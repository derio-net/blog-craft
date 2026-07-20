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
from path_ownership import _glob_to_regex, classify, load_manifest  # noqa: E402
from reproduce import apply, materialized_paths      # noqa: E402

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


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
    ap.add_argument("--only", action="append",
                    help="staging-relative glob to scope the plan (repeatable, ORed) — "
                         "e.g. --only 'scripts/**' migrates the image machinery only")
    ap.add_argument("--apply", action="store_true", help="apply (default is dry-run)")
    a = ap.parse_args(argv)
    import yaml
    m = default_manifest()
    cfg = yaml.safe_load(open(a.config)) or {}
    with tempfile.TemporaryDirectory() as td:
        staging = render_staging(a.config, str(Path(td) / "staging"))
        base = a.base
        if not base:
            ver = cfg.get("blog_craft_version")
            if ver:
                base = str(base_by_rerender(a.config, ver, str(Path(td) / "base")))
        plan = plan_update(a.blog, staging, base, m, cfg=cfg, only=a.only)
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
