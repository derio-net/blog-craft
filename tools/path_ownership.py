#!/usr/bin/env python3
"""Path-ownership classifier — reads templates/manifest.yaml, classifies a
materialized path as framework | content | merged.

Consumed by the reproduction harness (P5, which paths to diff) and the updater
(P6, which paths to overwrite vs 3-way-merge vs leave).

Library:
  load_manifest(path) -> {class: [globs]}
  classify_all(relpath, manifest) -> [class, ...]   (all matching classes)
  classify(relpath, manifest) -> class | None       (the single class, else None)

CLI:
  path_ownership.py --manifest <m> --classify <relpath>
  path_ownership.py --manifest <m> --list <class>
"""
from __future__ import annotations

import re
import sys

CLASSES = ("framework", "merged", "content")


def load_manifest(path: str) -> dict:
    import yaml
    with open(path) as f:
        m = yaml.safe_load(f) or {}
    return {k: (m.get(k) or []) for k in CLASSES if k in m}


def _glob_to_regex(glob: str) -> re.Pattern:
    # `**` -> across segments (.*), `*` -> within a segment ([^/]*).
    out = []
    i = 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            if glob[i:i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def _matches(glob: str, path: str) -> bool:
    return _glob_to_regex(glob).match(path) is not None


def classify_all(relpath: str, manifest: dict) -> list[str]:
    hits = []
    for cls in CLASSES:
        for glob in manifest.get(cls, []):
            if _matches(glob, relpath):
                hits.append(cls)
                break
    return hits


def classify(relpath: str, manifest: dict):
    hits = set(classify_all(relpath, manifest))
    return hits.pop() if len(hits) == 1 else None


def _main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--classify")
    ap.add_argument("--list", dest="list_class")
    a = ap.parse_args(argv)
    m = load_manifest(a.manifest)
    if a.classify:
        cls = classify(a.classify, m)
        print(cls if cls else "UNCLASSIFIED")
        return 0 if cls else 1
    if a.list_class:
        for g in m.get(a.list_class, []):
            print(g)
        return 0
    ap.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
