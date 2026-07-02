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

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_ownership import classify, load_manifest  # noqa: E402
from reproduce import apply, materialized_paths      # noqa: E402

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def render_staging(config: str, staging: str) -> Path:
    return apply(config, staging)


def three_way(base: Path, local: Path, incoming: Path) -> tuple[bytes, bool]:
    """git merge-file 3-way: returns (merged_bytes, conflict?)."""
    r = subprocess.run(["git", "merge-file", "-p", "--", str(local), str(base), str(incoming)],
                       capture_output=True)
    return r.stdout, r.returncode != 0


def plan_update(blog: str | Path, staging: str | Path, base: str | Path | None, manifest: dict) -> list[dict]:
    blog, staging = Path(blog), Path(staging)
    base = Path(base) if base else None
    plan: list[dict] = []
    for p in materialized_paths(staging):
        cls = classify(p, manifest)
        inc, loc = staging / p, blog / p
        if cls in (None, "content"):
            continue
        if not loc.exists():
            plan.append({"path": p, "action": "add", "class": cls})
            continue
        if loc.read_bytes() == inc.read_bytes():
            continue                                   # already up to date
        if cls == "framework":
            plan.append({"path": p, "action": "replace", "class": cls})
        else:  # merged -> 3-way
            b = base / p if base and (base / p).exists() else None
            if b is None:
                plan.append({"path": p, "action": "conflict", "class": cls,
                             "reason": "no base to merge from"})
            else:
                merged, conflict = three_way(b, loc, inc)
                plan.append({"path": p, "action": "conflict" if conflict else "merge",
                             "class": cls, "merged": merged})
    return plan


def dry_run_diff(plan: list[dict]) -> str:
    lines = [f"{e['action'].upper():8} {e['path']} [{e['class']}]"
             + (f"  ({e['reason']})" if e.get("reason") else "") for e in plan]
    if not lines:
        return "no changes"
    return "\n".join(lines)


def apply_plan(blog: str | Path, staging: str | Path, plan: list[dict]) -> list[str]:
    blog, staging = Path(blog), Path(staging)
    conflicts: list[str] = []
    for e in plan:
        dest = blog / e["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if e["action"] in ("replace", "add"):
            dest.write_bytes((staging / e["path"]).read_bytes())
        elif e["action"] == "merge":
            dest.write_bytes(e["merged"])
        elif e["action"] == "conflict":
            conflicts.append(e["path"])                # never auto-resolve
    return conflicts


def default_manifest() -> dict:
    return load_manifest(str(_PLUGIN_ROOT / "templates" / "manifest.yaml"))


def base_by_rerender(config: str, blog_craft_version: str, base_dir: str) -> Path:
    """Recover the 3-way base by re-rendering templates AT the recorded release.

    Extracts blog-craft's templates+tools at the git tag <blog_craft_version>
    into a temp checkout, then renders <config> through THAT. No per-repo
    baseline is stored (spec §8.2). Raises if the tag isn't reachable.
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


def _main(argv):
    import argparse
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--blog", required=True, help="existing blog dir to update in place")
    ap.add_argument("--base", help="explicit 3-way base (else re-render at blog_craft_version)")
    ap.add_argument("--apply", action="store_true", help="apply (default is dry-run)")
    a = ap.parse_args(argv)
    import yaml
    m = default_manifest()
    with tempfile.TemporaryDirectory() as td:
        staging = render_staging(a.config, str(Path(td) / "staging"))
        base = a.base
        if not base:
            ver = (yaml.safe_load(open(a.config)) or {}).get("blog_craft_version")
            if ver:
                base = str(base_by_rerender(a.config, ver, str(Path(td) / "base")))
        plan = plan_update(a.blog, staging, base, m)
        print(dry_run_diff(plan))
        if not a.apply:
            print("\n(dry-run — pass --apply to write)")
            return 0
        conflicts = apply_plan(a.blog, staging, plan)
        if conflicts:
            print("CONFLICTS (resolve manually):", *conflicts, sep="\n  ", file=sys.stderr)
            return 1
        print("update applied")
        return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
