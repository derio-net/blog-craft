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

import functools
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_ownership import _glob_to_regex, classify, load_manifest, root_of  # noqa: E402
from proc import run_checked                         # noqa: E402
from reproduce import apply, materialized_paths      # noqa: E402
from sync_state import SNAPSHOT_NAME, read_snapshot, write_snapshot  # noqa: E402

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Ordered for the dry-run tally: what lands, then what needs a human.
_ACTIONS = ("add", "replace", "merge", "relocate", "prune", "noop", "conflict")

_NO_SNAPSHOT_WARNING = (
    f"no {SNAPSHOT_NAME} — the 3-way base is rendered with the CURRENT config, so\n"
    "         changes you have made to .blog-craft.yaml since the last sync may be\n"
    "         dropped on `merged` paths (derio-net/blog-craft#60). A conflict-free\n"
    "         --apply records the snapshot; updates after that are exact."
)


def render_staging(config: str, staging: str) -> Path:
    # apply() resolves both — the renderer cds before reading them (#59).
    return apply(config, staging)


def site_prefix(cfg: dict | None) -> str:
    """`<site_dir>/`, or "" when the Hugo site IS the config root."""
    site_dir = ((cfg or {}).get("site_dir") or ".").rstrip("/")
    return "" if site_dir in ("", ".") else f"{site_dir}/"


def map_dest(path: str, cfg: dict | None, manifest: dict | None = None) -> str:
    """Map a STAGING-relative materialized path to its blog-relative destination.

    The manifest's `roots:` section decides, per path, WHO DEFINES ITS
    LOCATION (#61):

      repo  the location is fixed by a contract outside Hugo — GitHub Actions
            reads workflows from <repo>/.github/workflows/, hookify globs
            .claude/hookify.*.local.md from the project root. Never prefixed.
      site  Hugo's own layout defines it. Lands under `site_dir`.

    Two repo-rooted paths are additionally RENAMEABLE by the config, so their
    destination is read from it rather than from the manifest: the prompts file
    (`image.prompts_file`) and the reference pool (`image.reference_pool`).

    Identity when `site_dir` is absent and the defaults hold, so existing blogs'
    plans are byte-identical. An undeclared path falls back to `site`, which is
    the pre-#61 behaviour — see `path_ownership.root_of`.
    """
    cfg = cfg or {}
    image = cfg.get("image") or {}

    # Config-DECLARED destinations (repo-rooted and renameable).
    if path == "prompt_for_images.yaml":
        return image.get("prompts_file") or path
    if path == ".reference-pool" or path.startswith(".reference-pool/"):
        pool = image.get("reference_pool") or ".reference-pool"
        return pool + path[len(".reference-pool"):]

    if root_of(path, manifest if manifest is not None else default_manifest()) == "repo":
        return path
    return site_prefix(cfg) + path


def legacy_dests(path: str, cfg: dict | None, manifest: dict | None = None) -> list[str]:
    """Where earlier releases materialized `path`, per the manifest (#61).

    Fixing `map_dest` alone does not settle #61: `plan_update` classifies an
    absent managed path as `add`, so a blog carrying the file at the OLD
    location ends up with two copies and no indication which one the tool
    behind it honours — and the next `/update` re-adds the dead one.

    `{site}/` expands to `<site_dir>/`, or to nothing when the Hugo site IS the
    config root. Destinations that come out equal to the current one are dropped
    (they are not relocations), which is what keeps this inert for the blogs
    that never had the problem.
    """
    manifest = manifest if manifest is not None else default_manifest()
    table = (manifest.get("legacy_dests") or {}).get(path) or []
    if not table:
        return []
    prefix = site_prefix(cfg)
    here = map_dest(path, cfg, manifest)
    out = []
    for tmpl in table:
        # "{site}/x" -> "<site_dir>/x", or just "x" when the site IS the config
        # root (site_prefix is "" there, so one substitution covers both).
        dest = tmpl.replace("{site}/", prefix)
        if dest != here and dest not in out:
            out.append(dest)
    return out


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
        dest = map_dest(p, cfg, manifest)
        inc = staging / p
        if cls in (None, "content"):
            continue
        if only_res and not any(r.match(p) for r in only_res):
            continue

        # A path this release moved (root change and/or rename) may still be
        # sitting at its old destination. That file is the operator's — it is
        # the `local` side, not something to ignore and re-add blank (#61).
        legacy = next((d for d in legacy_dests(p, cfg, manifest) if (blog / d).exists()), None)
        entry = {"path": p, "dest": dest, "class": cls}
        if legacy:
            entry["legacy"] = legacy
            # Pruning the directories the old copy needed must stop at the site
            # directory — never retire the operator's site dir itself.
            site = site_prefix(cfg).rstrip("/")
            if site and (legacy == site or legacy.startswith(site + "/")):
                entry["legacy_floor"] = site

        loc = blog / dest
        if not loc.exists():
            if legacy is None:
                plan.append({**entry, "action": "add"})
                continue
            loc = blog / legacy                        # move the operator's copy
        elif legacy is not None and loc.read_bytes() == inc.read_bytes():
            # Half-migrated: a correct file already sits at the new destination
            # and the stale duplicate is still there. Only the duplicate goes.
            plan.append({**entry, "action": "prune"})
            continue

        if loc.read_bytes() == inc.read_bytes():
            if legacy is None:
                continue                               # already up to date
            plan.append({**entry, "action": "relocate"})   # identical -> pure move
            continue
        if cls == "framework":
            plan.append({**entry, "action": "replace"})
        else:  # merged -> 3-way
            b = base / p if base and (base / p).exists() else None
            if b is None:
                plan.append({**entry, "action": "conflict",
                             "reason": "no base to merge from"})
            else:
                merged, conflict = three_way(b, loc, inc)
                entry = {**entry, "merged": merged}
                if conflict:
                    entry["action"] = "conflict"
                elif merged == loc.read_bytes():
                    if legacy is not None:
                        # The merge kept the operator's copy wholesale — but that
                        # copy is at the OLD destination, so writing it is not a
                        # no-op, it IS the move (#61). Calling this NOOP would
                        # strand the file where nothing reads it.
                        entry["action"] = "relocate"
                    else:
                        # Applying would rewrite the file with the bytes already
                        # in it. Reported as `merge`, that is indistinguishable
                        # from a merge that shipped something — which is how #60
                        # stayed invisible. A NOOP on a path you expected to
                        # change means the base is wrong: a stale or absent sync
                        # snapshot.
                        entry["action"] = "noop"
                        entry["reason"] = "merge produced no change"
                else:
                    entry["action"] = "merge"
                plan.append(entry)
    return plan


def dry_run_diff(plan: list[dict]) -> str:
    """Render the plan. For a relocation the dry-run IS the migration notice —
    it names both sides, so the operator sees where the file is coming from."""
    lines = []
    for e in plan:
        dest, legacy = e.get("dest", e["path"]), e.get("legacy")
        if e["action"] == "prune":
            what = f"{legacy}  (stale — now at {dest})"
        elif legacy:
            what = f"{legacy} -> {dest}"
        else:
            what = dest
        line = f"{e['action'].upper():8} {what} [{e['class']}]"
        if e.get("reason"):
            line += f"  ({e['reason']})"
        lines.append(line)
    return "\n".join(lines) if lines else "no changes"


def _prune_empty_parents(floor: Path, path: Path) -> None:
    """Remove directories left empty by a relocation, never at or above `floor`.

    `floor` is the blog root, or the site directory when the stale copy lived
    under it: a relocation retires the directories the OLD destination needed,
    never the operator's site directory — even in the degenerate case where the
    moved file was the only thing in it.
    """
    d = path.parent
    while d != floor and floor in d.parents:
        try:
            d.rmdir()          # only succeeds while the directory is empty
        except OSError:
            return             # still holds operator files — stop here
        d = d.parent


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
        legacy = blog / e["legacy"] if e.get("legacy") else None

        if e["action"] == "conflict":
            # Never auto-resolve — and on a relocation, never destroy the
            # evidence either: BOTH copies stay, both are named, because the
            # operator has to know there are two (#61).
            conflicts.append(e.get("dest", e["path"]))
            if legacy is not None:
                conflicts.append(e["legacy"])
            continue

        # `prune` removes the stale duplicate only; `noop` is a merge that kept
        # local wholesale, so writing it back would be a no-op by definition.
        if e["action"] not in ("prune", "noop"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            if e["action"] == "merge":
                dest.write_bytes(e["merged"])
            elif e["action"] == "relocate":
                # A relocation writes the operator's file at its NEW home: the
                # 3-way result when there was one, else the staged bytes — which
                # in the pure-move case are byte-identical to their copy.
                dest.write_bytes(e["merged"] if "merged" in e
                                 else (staging / e["path"]).read_bytes())
            elif e["action"] in ("replace", "add"):
                dest.write_bytes((staging / e["path"]).read_bytes())

        # The new copy is on disk (or was already correct) — retire the old one.
        if legacy is not None and legacy.exists() and legacy != dest:
            legacy.unlink()
            floor = blog / e["legacy_floor"] if e.get("legacy_floor") else blog
            _prune_empty_parents(floor, legacy)
    return conflicts


@functools.lru_cache(maxsize=1)
def default_manifest() -> dict:
    # Cached: map_dest() falls back to it per path when a caller passes none.
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
    config = Path(config).resolve()          # the renderer cds before reading it (#59)
    base_dir = Path(base_dir).resolve()
    with tempfile.TemporaryDirectory() as td:
        arch = Path(td) / "old.tar"
        # run_checked, not bare check=True: an unreachable tag is exactly the
        # failure /update's own guardrail ("keep blog_craft_version accurate")
        # warns about, and git says which ref it could not find (#59).
        run_checked(["git", "-C", str(_PLUGIN_ROOT), "archive", "--output", str(arch),
                     blog_craft_version])
        old = Path(td) / "old"; old.mkdir()
        subprocess.run(["tar", "-xf", str(arch), "-C", str(old)], check=True)  # output visible
        run_checked(["bash", str(old / "tools" / "bootstrap-render.sh"),
                     str(config), str(base_dir)])
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
    import yaml
    # Resolve every path argument up front (#59), BEFORE anything reads them.
    # --config is threaded into bootstrap-render.sh, which resolves it AFTER an
    # internal `cd` — the documented `--config .blog-craft.yaml --blog .`
    # invocation always failed because of it. --blog/--base are only Path-joined,
    # but resolving all three keeps one file in view for the plan, the render and
    # the sync snapshot.
    config = Path(a.config).resolve()
    blog = Path(a.blog).resolve()
    # A typo'd path is the most likely way to get this wrong, so it must not
    # arrive as a stdlib traceback — that is the same illegibility #59 is about,
    # one step earlier than the renderer. Name the resolved path AND the
    # directory it was resolved from, since the whole point of #59 is that a
    # relative argument is not resolved where the operator assumed.
    for label, p, kind in (("--config", config, "file"), ("--blog", blog, "directory")):
        if not (p.is_file() if kind == "file" else p.is_dir()):
            print(f"ERROR: {label} {kind} not found: {p}", file=sys.stderr)
            print(f"       (resolved from {Path.cwd()})", file=sys.stderr)
            return 2
    # Is THIS run's base the #60 fallback? Read before anything can write a
    # snapshot — a conflict-free apply records one, after which the answer would
    # always be "no" and the one chance to flag pre-existing drift would be gone.
    fallback_base = not a.base and read_snapshot(blog) is None
    m = default_manifest()
    cfg = yaml.safe_load(open(config)) or {}
    with tempfile.TemporaryDirectory() as td:
        staging = render_staging(str(config), str(Path(td) / "staging"))
        base = str(Path(a.base).resolve()) if a.base else None
        if not base:
            ver = cfg.get("blog_craft_version")
            if ver:
                base = render_base(config, blog, ver, str(Path(td) / "base"))
        plan = plan_update(blog, staging, base, m, cfg=cfg, only=a.only)
        print(dry_run_diff(plan))
        if plan:
            print(f"\n{plan_summary(plan)}")     # dry_run_diff already says "no changes"
        if not a.apply:
            print("\n(dry-run — pass --apply to write)")
            return 0
        conflicts = apply_plan(blog, staging, plan)
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
                print(f"recorded sync snapshot: {write_snapshot(config, blog)}")
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
