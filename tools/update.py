#!/usr/bin/env python3
"""Non-destructive updater — re-apply blog-craft to an existing blog (spec §8.2).

Renders to a STAGING tree, classifies each path via the manifest, and computes a
per-path action:
  framework -> replace (shipped, overwrite)
  content   -> leave   (operator-owned)
  merged    -> 3-way merge (base=re-render at recorded version, local=on-disk,
               incoming=staging) via `git merge-file`; conflicts are surfaced,
               never auto-resolved. A merge that keeps local wholesale writes
               nothing and is reported as `noop`, not `merge`.

The base answers "what did blog-craft last give this blog?" — that is
`render(config_at_last_sync, templates_at_recorded_version)`. The templates come
from a `git archive` of the recorded `blog_craft_version`; the config comes from
`.blog-craft.sync.yaml`, the snapshot this tool writes on every clean `--apply`
(see tools/sync_state.py). No rendered baseline TREE is stored — one small YAML
file is (spec §8.2).

A blog with no snapshot — every blog synced before blog-craft#60 — falls back to
the current config and is told so: that fallback is exactly the defect #60
describes, and the first `--apply` records the snapshot that ends it.

Library:
  render_staging(config, staging) -> Path
  base_config(config, blog) -> (Path, str | None)            # which config, why
  render_base(config, blog, version, base_dir) -> str        # the 3-way base
  plan_update(blog, staging, base, manifest) -> list[dict]   # actions
  dry_run_diff(plan) -> str
  plan_summary(plan) -> str                                  # per-action tally
  baselined_by_fallback(plan) -> list[str]                   # NOOPs a fallback base hid
  apply_plan(blog, plan) -> list[str]                        # conflicted paths
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_ownership import _glob_to_regex, classify, load_manifest  # noqa: E402
from reproduce import apply, materialized_paths      # noqa: E402
from sync_state import SNAPSHOT_NAME, read_snapshot, write_snapshot  # noqa: E402

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Ordered for the dry-run tally: what lands, then what needs a human.
_ACTIONS = ("add", "replace", "merge", "noop", "conflict")

_NO_SNAPSHOT_WARNING = (
    f"no {SNAPSHOT_NAME} — the 3-way base is rendered with the CURRENT config, so\n"
    "         changes you have made to .blog-craft.yaml since the last sync may be\n"
    "         dropped on `merged` paths (derio-net/blog-craft#60). A conflict-free\n"
    "         --apply records the snapshot; updates after that are exact."
)


def render_staging(config: str, staging: str) -> Path:
    return apply(config, staging)


def map_dest(path: str, cfg: dict | None) -> str:
    """Map a STAGING-relative materialized path to its blog-relative destination.

    Config-rooted paths (the config itself, the reference pool, the prompts
    file) stay at / relocate to their config-declared locations; everything
    else — the Hugo site — lands under `site_dir` (spec D6). Identity when
    site_dir is absent and the defaults hold, so existing blogs' plans are
    byte-identical.
    """
    cfg = cfg or {}
    image = cfg.get("image") or {}
    if path == ".blog-craft.yaml":
        return path
    if path == "prompt_for_images.yaml":
        return image.get("prompts_file") or path
    pool = image.get("reference_pool") or ".reference-pool"
    if path == ".reference-pool" or path.startswith(".reference-pool/"):
        return pool + path[len(".reference-pool"):]
    site_dir = (cfg.get("site_dir") or ".").rstrip("/")
    if site_dir in ("", "."):
        return path
    return f"{site_dir}/{path}"


def three_way(base: Path, local: Path, incoming: Path) -> tuple[bytes, bool]:
    """git merge-file 3-way: returns (merged_bytes, conflict?)."""
    r = subprocess.run(["git", "merge-file", "-p", "--", str(local), str(base), str(incoming)],
                       capture_output=True)
    return r.stdout, r.returncode != 0


def plan_update(blog: str | Path, staging: str | Path, base: str | Path | None, manifest: dict,
                cfg: dict | None = None, only: list[str] | None = None) -> list[dict]:
    blog, staging = Path(blog), Path(staging)
    base = Path(base) if base else None
    only_res = [_glob_to_regex(g) for g in (only or [])]
    plan: list[dict] = []
    for p in materialized_paths(staging):
        # classification runs on the STAGING-relative path (manifest is
        # site-shaped); comparison + application use the mapped destination
        cls = classify(p, manifest)
        dest = map_dest(p, cfg)
        inc, loc = staging / p, blog / dest
        if cls in (None, "content"):
            continue
        if only_res and not any(r.match(p) for r in only_res):
            continue
        if not loc.exists():
            plan.append({"path": p, "dest": dest, "action": "add", "class": cls})
            continue
        if loc.read_bytes() == inc.read_bytes():
            continue                                   # already up to date
        if cls == "framework":
            plan.append({"path": p, "dest": dest, "action": "replace", "class": cls})
        else:  # merged -> 3-way
            b = base / p if base and (base / p).exists() else None
            if b is None:
                plan.append({"path": p, "dest": dest, "action": "conflict", "class": cls,
                             "reason": "no base to merge from"})
            else:
                merged, conflict = three_way(b, loc, inc)
                entry = {"path": p, "dest": dest, "class": cls, "merged": merged}
                if conflict:
                    entry["action"] = "conflict"
                elif merged == loc.read_bytes():
                    # The merge resolved entirely in local's favour, so applying
                    # it would rewrite the file with the bytes already in it.
                    # Reported as `merge`, that is indistinguishable from a merge
                    # that shipped something — which is how #60 stayed invisible.
                    # A NOOP on a path you expected to change means the base is
                    # wrong: a stale or absent sync snapshot.
                    entry["action"] = "noop"
                    entry["reason"] = "merge produced no change"
                else:
                    entry["action"] = "merge"
                plan.append(entry)
    return plan


def dry_run_diff(plan: list[dict]) -> str:
    lines = [f"{e['action'].upper():8} {e.get('dest', e['path'])} [{e['class']}]"
             + (f"  ({e['reason']})" if e.get("reason") else "") for e in plan]
    if not lines:
        return "no changes"
    return "\n".join(lines)


def plan_summary(plan: list[dict]) -> str:
    """One-line tally — `2 replace, 1 merge, 1 noop` — so a long plan is readable."""
    if not plan:
        return "no changes"
    counts: dict[str, int] = {}
    for e in plan:
        counts[e["action"]] = counts.get(e["action"], 0) + 1
    # _ACTIONS first, for a stable reading order; anything unknown still appears,
    # because a tally that silently drops entries is the bug this fix is about.
    order = list(_ACTIONS) + sorted(k for k in counts if k not in _ACTIONS)
    return ", ".join(f"{counts[a]} {a}" for a in order if counts.get(a))


def baselined_by_fallback(plan: list[dict]) -> list[str]:
    """`merged` paths that resolved to NOOP — where a pre-#60 drop would be hiding.

    A NOOP means the merge kept local wholesale. Against an HONEST base that is
    simply "nothing to do". Against the FALLBACK base — rendered from the current
    config because the blog has no snapshot yet — it also covers the case this
    fix exists to end: blog-craft shipped a change, an earlier run dropped it, and
    a base built from today's config now agrees the absence was deliberate.

    The two are indistinguishable from inside a single run, so the caller names
    them instead of guessing. Cheap to ignore when they are the harmless kind;
    the only way to notice when they are not.
    """
    return [e.get("dest", e["path"]) for e in plan if e["action"] == "noop"]


def _baselined_warning(paths: list[str]) -> str:
    listed = "\n".join(f"           {p}" for p in paths)
    return (
        f"a snapshot was recorded, but THIS run's base still came from the current\n"
        f"         config — there was no {SNAPSHOT_NAME} when it started. These\n"
        f"         `merged` paths resolved to NOOP against that base:\n{listed}\n"
        "         If blog-craft shipped a change to one of them BEFORE this run, an\n"
        "         earlier update dropped it (#60) — and the snapshot just written now\n"
        "         makes every future update agree with that drift instead of\n"
        "         reporting it. This is the one run that can still tell you.\n"
        "         Check each against a fresh render before trusting it:\n"
        "           bash <blog-craft>/tools/bootstrap-render.sh <config> /tmp/bc-fresh\n"
        "         then diff /tmp/bc-fresh/<staging-relative path> against your copy."
    )


def apply_plan(blog: str | Path, staging: str | Path, plan: list[dict]) -> list[str]:
    blog, staging = Path(blog), Path(staging)
    conflicts: list[str] = []
    for e in plan:
        dest = blog / e.get("dest", e["path"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        if e["action"] in ("replace", "add"):
            dest.write_bytes((staging / e["path"]).read_bytes())
        elif e["action"] == "merge":
            dest.write_bytes(e["merged"])
        elif e["action"] == "conflict":
            # report the on-disk destination (mapped) — that's the file the
            # operator must resolve; never auto-resolve
            conflicts.append(e.get("dest", e["path"]))
    return conflicts


def default_manifest() -> dict:
    return load_manifest(str(_PLUGIN_ROOT / "templates" / "manifest.yaml"))


def base_by_rerender(config: str, blog_craft_version: str, base_dir: str) -> Path:
    """Render <config> through blog-craft's templates AT the recorded release.

    Extracts templates+tools at the git tag <blog_craft_version> into a temp
    checkout and renders <config> through THAT. No baseline TREE is stored (spec
    §8.2). Raises if the tag isn't reachable.

    Deliberately single-purpose: *this config, that tag*. Choosing WHICH config
    is the base's — the sync snapshot, not whatever the operator last edited —
    belongs to `render_base`, and conflating the two is what #60 was.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        arch = Path(td) / "old.tar"
        subprocess.run(["git", "-C", str(_PLUGIN_ROOT), "archive", "--output", str(arch),
                        blog_craft_version], check=True, capture_output=True)
        old = Path(td) / "old"; old.mkdir()
        subprocess.run(["tar", "-xf", str(arch), "-C", str(old)], check=True)
        subprocess.run(["bash", str(old / "tools" / "bootstrap-render.sh"), str(config), str(base_dir)],
                       check=True, capture_output=True, text=True)
    return Path(base_dir)


def base_config(config: str | Path, blog: str | Path) -> tuple[Path, str | None]:
    """Which config the 3-way base must be rendered from, and what to warn about.

    The snapshot when the blog has one — that is the whole point of #60. The
    live config otherwise, with the warning that makes the approximation
    visible; silence was the defect's accomplice.
    """
    snap = read_snapshot(blog)
    if snap is not None:
        return snap, None
    return Path(config), _NO_SNAPSHOT_WARNING


def _warn(msg: str) -> None:
    print(f"[update] {msg}", file=sys.stderr)


def render_base(config: str | Path, blog: str | Path, blog_craft_version: str,
                base_dir: str, *, render=None, warn=_warn) -> str:
    """Render the 3-way base, preferring the sync snapshot over the live config.

    `render` is injected so the selection logic is testable without a git tag or
    a Hugo toolchain; it defaults to `base_by_rerender`.

    A snapshot that will not render — one whose schema the recorded release
    predates, say — degrades to the live config rather than killing the run:
    that is the pre-#60 behaviour, which is imperfect but not fatal. If the live
    config will not render either, the failure propagates; there is nothing left
    to fall back to.
    """
    render = render or base_by_rerender
    chosen, warning = base_config(config, blog)
    if warning:
        warn(warning)
    try:
        return render(str(chosen), blog_craft_version, base_dir)
    except Exception as e:                                    # noqa: BLE001
        if warning:                                           # already the live config
            raise
        warn(f"{SNAPSHOT_NAME} would not render at {blog_craft_version} ({e}); falling back\n"
             "         to the current config — merged paths may lose changes (#60).")
        return render(str(config), blog_craft_version, base_dir)


def _main(argv):
    import argparse
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--blog", required=True, help="existing blog dir to update in place")
    ap.add_argument("--base", help="explicit 3-way base (else re-render at blog_craft_version)")
    ap.add_argument("--only", action="append",
                    help="staging-relative glob to scope the plan (repeatable, ORed) — "
                         "e.g. --only 'scripts/**' migrates the image machinery only")
    ap.add_argument("--apply", action="store_true", help="apply (default is dry-run)")
    a = ap.parse_args(argv)
    # Is THIS run's base the #60 fallback? Read before anything can write a
    # snapshot — a conflict-free apply records one, after which the answer would
    # always be "no" and the one chance to flag pre-existing drift would be gone.
    fallback_base = not a.base and read_snapshot(a.blog) is None
    import yaml
    m = default_manifest()
    cfg = yaml.safe_load(open(a.config)) or {}
    with tempfile.TemporaryDirectory() as td:
        staging = render_staging(a.config, str(Path(td) / "staging"))
        base = a.base
        if not base:
            ver = cfg.get("blog_craft_version")
            if ver:
                base = render_base(a.config, a.blog, ver, str(Path(td) / "base"))
        plan = plan_update(a.blog, staging, base, m, cfg=cfg, only=a.only)
        print(dry_run_diff(plan))
        if plan:
            print(f"\n{plan_summary(plan)}")     # dry_run_diff already says "no changes"
        if not a.apply:
            print("\n(dry-run — pass --apply to write)")
            return 0
        conflicts = apply_plan(a.blog, staging, plan)
        if conflicts:
            # Leave the previous snapshot in place: half the plan is unresolved,
            # so "this blog is synced to config X" would be a lie, and a stale
            # but honest base beats a fresh but false one.
            print("CONFLICTS (resolve manually):", *conflicts, sep="\n  ", file=sys.stderr)
            return 1
        if a.only:
            # A scoped run syncs SOME paths. Recording the config as this blog's
            # sync state would then overstate what landed, and every path outside
            # the scope would be diffed against a base built from a config it was
            # never rendered with — #60 again, by another door.
            _warn(f"--only was scoped, so {SNAPSHOT_NAME} is left as it was: a partial\n"
                  "         apply is not a sync. Run an unscoped --apply to record one.")
        else:
            try:
                print(f"recorded sync snapshot: {write_snapshot(a.config, a.blog)}")
            except OSError as e:
                # The files landed; only the bookkeeping failed. Don't fail the
                # run over it — but the operator has to know the next update
                # will fall back to the current config.
                _warn(f"applied, but could not write {SNAPSHOT_NAME} ({e}) — the next\n"
                      "         update will render its base from the current config (#60).")
            else:
                # A snapshot now exists, so this blog's base is honest from here
                # on. What it cannot do is undo a drop that happened before it:
                # the snapshot asserts "synced to this config" over a tree that
                # may not match, and from the next run those paths are ordinary
                # NOOPs with no warning attached. Name them while it still means
                # something.
                if fallback_base:
                    suspect = baselined_by_fallback(plan)
                    if suspect:
                        _warn(_baselined_warning(suspect))
        print("update applied")
        return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
