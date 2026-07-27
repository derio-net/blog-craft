#!/usr/bin/env python3
"""Non-destructive updater — re-apply blog-craft to an existing blog (spec §8.2).

Renders to a STAGING tree, classifies each path via the manifest, and computes a
per-path action:
  framework -> replace (shipped, overwrite)
  content   -> leave   (operator-owned)
  merged    -> 3-way merge (base=re-render at recorded version, local=on-disk,
               incoming=staging) via `git merge-file`; conflicts are surfaced,
               never auto-resolved.
The base is recovered by re-rendering the templates AT the recorded
`blog_craft_version` (git tag) — no per-repo baseline is stored.

Library:
  render_staging(config, staging) -> Path
  plan_update(blog, staging, base, manifest) -> list[dict]   # actions
  dry_run_diff(plan) -> str
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

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


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
                plan.append({"path": p, "dest": dest,
                             "action": "conflict" if conflict else "merge",
                             "class": cls, "merged": merged})
    return plan


def dry_run_diff(plan: list[dict]) -> str:
    lines = [f"{e['action'].upper():8} {e.get('dest', e['path'])} [{e['class']}]"
             + (f"  ({e['reason']})" if e.get("reason") else "") for e in plan]
    if not lines:
        return "no changes"
    return "\n".join(lines)


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


@functools.lru_cache(maxsize=1)
def default_manifest() -> dict:
    # Cached: map_dest() falls back to it per path when a caller passes none.
    return load_manifest(str(_PLUGIN_ROOT / "templates" / "manifest.yaml"))


def base_by_rerender(config: str, blog_craft_version: str, base_dir: str) -> Path:
    """Recover the 3-way base by re-rendering templates AT the recorded release.

    Extracts blog-craft's templates+tools at the git tag <blog_craft_version>
    into a temp checkout, then renders <config> through THAT. No per-repo
    baseline is stored (spec §8.2). Raises if the tag isn't reachable.
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
        subprocess.run(["tar", "-xf", str(arch), "-C", str(old)], check=True)  # output already visible
        run_checked(["bash", str(old / "tools" / "bootstrap-render.sh"), str(config), str(base_dir)])
    return Path(base_dir)


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
    # Resolve every path argument up front (#59). --config is threaded into
    # bootstrap-render.sh, which resolves it AFTER an internal `cd` — the
    # documented `--config .blog-craft.yaml --blog .` invocation always failed
    # because of it. --blog/--base are only Path-joined, but resolving all three
    # keeps one file in view for both the plan and the render.
    config = Path(a.config).resolve()
    blog = Path(a.blog).resolve()
    m = default_manifest()
    cfg = yaml.safe_load(open(config)) or {}
    with tempfile.TemporaryDirectory() as td:
        staging = render_staging(str(config), str(Path(td) / "staging"))
        base = str(Path(a.base).resolve()) if a.base else None
        if not base:
            ver = cfg.get("blog_craft_version")
            if ver:
                base = str(base_by_rerender(str(config), ver, str(Path(td) / "base")))
        plan = plan_update(blog, staging, base, m, cfg=cfg, only=a.only)
        print(dry_run_diff(plan))
        if not a.apply:
            print("\n(dry-run — pass --apply to write)")
            return 0
        conflicts = apply_plan(blog, staging, plan)
        if conflicts:
            print("CONFLICTS (resolve manually):", *conflicts, sep="\n  ", file=sys.stderr)
            return 1
        print("update applied")
        return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
