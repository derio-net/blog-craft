#!/usr/bin/env python3
"""Insert {{< abbr >}} markers into a post's prose (docs/CONFIG.md §9).

Deliberately boring and deliberately paranoid. It marks only terms the registry
already defines, only in prose, and only once per post by default — then refuses
to do anything on a second run.

It imports `excluded_spans` from glossary_scan rather than re-deriving "is this
token in prose?". Two implementations of that question would eventually
disagree, and the failure mode of disagreement is a marker written into a code
sample.

Library:
  apply_file(path, registry, first_occurrence_only=True) -> [{file, line, term}]

CLI:
  glossary_apply.py --config <.blog-craft.yaml> [--all] <path…>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glossary_scan import MARKER_RE, candidates, load_registry  # noqa: E402


def _marker(term: str, display: str) -> str:
    if display == term:
        return f'{{{{< abbr "{term}" >}}}}'
    return f'{{{{< abbr "{term}" "{display}" >}}}}'


def apply_file(path: str, registry: dict,
               first_occurrence_only: bool = True) -> list[dict]:
    """Mark defined terms in one file. Returns the edits made (empty == untouched).

    The file is written only when something actually changed, so a no-op run
    leaves mtime alone and produces no git noise across a series-wide sweep.
    """
    with open(path) as f:
        text = f.read()

    hits = [c for c in candidates(text) if c["term"] in registry]
    if first_occurrence_only:
        # Seed from the markers already in the file. candidates() skips tokens
        # INSIDE a marker (it sits in an excluded span), but a later bare
        # occurrence is still a candidate — so without this seed a second run
        # would keep marking further occurrences and never converge.
        seen: set[str] = set(MARKER_RE.findall(text))
        first = []
        for c in hits:
            if c["term"] not in seen:
                seen.add(c["term"])
                first.append(c)
        hits = first
    if not hits:
        return []

    edits = [{"file": path, "line": text.count("\n", 0, c["start"]) + 1,
              "term": c["term"]} for c in hits]

    # Rewrite right-to-left so earlier offsets stay valid.
    for c in sorted(hits, key=lambda c: c["start"], reverse=True):
        text = (text[:c["start"]] + _marker(c["term"], c["display"])
                + text[c["end"]:])
    with open(path, "w") as f:
        f.write(text)
    return edits


def _main(argv: list[str]) -> int:
    import argparse
    import yaml
    ap = argparse.ArgumentParser(description="Insert {{< abbr >}} markers.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--all", action="store_true",
                    help="mark every occurrence, not just the first per post")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)

    with open(a.config) as f:
        cfg = yaml.safe_load(f) or {}
    gl = ((cfg.get("features") or {}).get("glossary") or {})
    first_only = False if a.all else gl.get("first_occurrence_only", True)

    registry = load_registry(a.config)
    if not registry:
        print("no data/glossary.yaml entries — nothing to mark", file=sys.stderr)
        return 0

    total = 0
    for p in a.paths:
        for e in apply_file(p, registry, first_occurrence_only=first_only):
            print(f"{e['file']}:{e['line']}  {e['term']}")
            total += 1
    print(f"{total} marker(s) inserted")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
