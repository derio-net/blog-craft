#!/usr/bin/env python3
"""Mirror a paper's dossier frontmatter into the Hugo data dir.

The references-index shortcode reads `.Site.Data.papers.<slug>`; this writes
`<data_dir>/<slug>.yaml` from `<dossier_dir>/<slug>/dossier.md`. Config-driven:
dossier_dir + data_dir come from content_types.papers.

CLI:
  sync_dossier_to_data.py --config <.blog-craft.yaml> [--check]
    (default) sync all dossiers -> data_dir
    --check   exit 1 if any data file is missing/stale (no writes)
"""
from __future__ import annotations

import sys
from pathlib import Path

from validate_dossier import parse_dossier  # tools/ on sys.path


def _mirror(data: dict) -> dict:
    return {k: data.get(k) for k in
            ("vendors", "primary_sources", "artefacts", "gaps", "counter_arguments")
            if data.get(k) is not None}


def sync(root: Path, dossier_dir: str, data_dir: str, check: bool = False) -> list[str]:
    import yaml
    ddir = root / dossier_dir
    out_dir = root / data_dir
    problems: list[str] = []
    if not ddir.is_dir():
        return problems
    for d in sorted(ddir.iterdir()):
        dossier = d / "dossier.md"
        if not dossier.is_file():
            continue
        slug = d.name
        want = yaml.safe_dump(_mirror(parse_dossier(dossier.read_text())), sort_keys=True)
        target = out_dir / f"{slug}.yaml"
        if check:
            if not target.exists() or target.read_text() != want:
                problems.append(f"stale/missing data mirror: {target}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(want)
    return problems


def _main(argv):
    import argparse
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    cfg = yaml.safe_load(open(a.config))
    papers = ((cfg.get("content_types") or {}).get("papers") or {})
    root = Path(a.config).resolve().parent
    problems = sync(root, papers.get("dossier_dir", "docs/papers-dossiers"),
                    papers.get("data_dir", "blog/data/papers"), check=a.check)
    if problems:
        for p in problems:
            print(f"  x {p}", file=sys.stderr)
        return 1
    print("dossier->data " + ("in sync" if a.check else "synced"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
