#!/usr/bin/env python3
"""Reproduction harness — apply blog-craft + a config into a scratch dir and
structurally diff it against a reference tree (spec §7).

Only `framework` + `merged` paths (per templates/manifest.yaml) are compared;
`content` paths are operator-owned and ignored. An unclassified materialized
path is itself drift (spec §11 "no unclassified materialized path").

Library:
  apply(config_path, scratch_dir) -> Path                 # materialize a blog
  structural_diff(generated, reference, manifest) -> [str] # [] == zero drift
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_ownership import classify, load_manifest  # noqa: E402

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# Build artifacts + VCS — never part of the materialized template surface.
_IGNORE_DIRS = {"public", "resources", ".git", ".hugo_build.lock", "node_modules"}
_IGNORE_FILES = {".hugo_build.lock", "hugo_stats.json"}


def apply(config_path: str, scratch_dir: str) -> Path:
    """Materialize a blog from a .blog-craft.yaml (== v2 answers) into scratch_dir."""
    target = Path(scratch_dir)
    subprocess.run(
        ["bash", str(_PLUGIN_ROOT / "tools" / "bootstrap-render.sh"), str(config_path), str(target)],
        check=True, capture_output=True, text=True,
    )
    return target


def materialized_paths(root: str | Path) -> list[str]:
    root = Path(root)
    out = []
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for f in files:
            if f in _IGNORE_FILES:
                continue
            out.append(os.path.relpath(os.path.join(dp, f), root))
    return sorted(out)


def structural_diff(generated: str | Path, reference: str | Path, manifest: dict) -> list[str]:
    generated, reference = Path(generated), Path(reference)
    drift: list[str] = []
    gen = materialized_paths(generated)
    for p in gen:
        cls = classify(p, manifest)
        if cls is None:
            drift.append(f"unclassified materialized path: {p}")
            continue
        if cls == "content":
            continue
        rp = reference / p
        if not rp.exists():
            drift.append(f"missing in reference: {p} [{cls}]")
        elif (generated / p).read_bytes() != rp.read_bytes():
            drift.append(f"content differs: {p} [{cls}]")
    ref_set = set(gen)
    for p in materialized_paths(reference):
        if p in ref_set:
            continue
        cls = classify(p, manifest)
        if cls in ("framework", "merged"):
            drift.append(f"missing in generated: {p} [{cls}]")
    return drift


def render_and_diff(root_a: str | Path, root_b: str | Path) -> list[str]:
    """Hugo-build two blog trees and diff their rendered HTML — the
    render-identity check (spec: prove zero VISUAL change).

    Used to prove a generalization renders identically to the original: build
    the blog before vs after the change (same content), diff public/**/*.html.
    Any diff is a real appearance change. Returns [] == pixel-identical markup.
    """
    a, b = Path(root_a), Path(root_b)
    for r in (a, b):
        subprocess.run(["hugo", "--buildDrafts", "--quiet"], cwd=str(r), check=True, capture_output=True, text=True)
    diffs: list[str] = []
    pa, pb = a / "public", b / "public"

    def _html(root):
        return {os.path.relpath(os.path.join(dp, f), root)
                for dp, _, fs in os.walk(root) for f in fs if f.endswith(".html")}

    ha, hb = _html(pa), _html(pb)
    for f in sorted(ha | hb):
        fa, fb = pa / f, pb / f
        if not fa.exists():
            diffs.append(f"only in B: {f}")
        elif not fb.exists():
            diffs.append(f"only in A: {f}")
        elif fa.read_bytes() != fb.read_bytes():
            diffs.append(f"render differs: {f}")
    return diffs


def default_manifest() -> dict:
    return load_manifest(str(_PLUGIN_ROOT / "templates" / "manifest.yaml"))


def _main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--reference", required=True, help="existing blog tree to diff against")
    ap.add_argument("--scratch", required=True)
    a = ap.parse_args(argv)
    apply(a.config, a.scratch)
    drift = structural_diff(a.scratch, a.reference, default_manifest())
    if drift:
        print(f"STRUCTURAL DRIFT ({len(drift)}):", file=sys.stderr)
        for d in drift:
            print(f"  - {d}", file=sys.stderr)
        return 1
    print("ZERO STRUCTURAL DRIFT")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
