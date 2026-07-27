#!/usr/bin/env python3
"""Path-ownership classifier — reads templates/manifest.yaml, classifies a
materialized path as framework | content | merged.

Consumed by the reproduction harness (P5, which paths to diff) and the updater
(P6, which paths to overwrite vs 3-way-merge vs leave).

It also carries the manifest's path-ROOT model (#61) — a different question from
ownership: not "who owns this file?" but "who DEFINES its location — the Hugo
site, or a tool that reads it from the repository root?". `/update` needs the
answer to place a path in a blog whose site is not the repo root.

Library:
  load_manifest(path) -> {class: [globs], "roots": {root: [globs]}}
  classify_all(relpath, manifest) -> [class, ...]   (all matching classes)
  classify(relpath, manifest) -> class | None       (the single class, else None)
  root_of(relpath, manifest) -> "repo" | "site"     (undeclared -> "site")

CLI:
  path_ownership.py --manifest <m> --classify <relpath>
  path_ownership.py --manifest <m> --list <class>
"""
from __future__ import annotations

import re
import sys

CLASSES = ("framework", "merged", "content")
ROOTS = ("repo", "site")
DEFAULT_ROOT = "site"


def load_manifest(path: str) -> dict:
    import yaml
    with open(path) as f:
        m = yaml.safe_load(f) or {}
    out = {k: (m.get(k) or []) for k in CLASSES if k in m}
    # `roots` is namespaced under its own key so it never collides with a class
    # name — classify_all() only ever iterates CLASSES.
    roots = m.get("roots") or {}
    if roots:
        out["roots"] = {r: (roots.get(r) or []) for r in ROOTS if r in roots}
    return out


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


def root_of(relpath: str, manifest: dict) -> str:
    """Which root defines this path's location — "repo" or "site" (#61).

    An UNDECLARED path resolves to "site", which is byte-identical to the
    pre-#61 behaviour: a template file someone forgets to declare can never
    break a blog at runtime. The enforcement that every materialized path IS
    declared lives in tests/unit/test_path_roots.py.
    """
    for root in ROOTS:
        for glob in (manifest.get("roots") or {}).get(root, []):
            if _matches(glob, relpath):
                return root
    return DEFAULT_ROOT


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
