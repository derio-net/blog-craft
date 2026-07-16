#!/usr/bin/env python3
"""Assemble a per-post changelog for a batch educational rewrite (#28).

Given per-post change entries (YAML), hoist the items common to EVERY post into
a "Conventions Applied to Every Post" table and render the campaign changelog in
the frank format (see skills/educational-writing/references/changelog.md). The
per-post tables then carry only each post's residual, post-specific changes.

Usage:
    assemble_changelog.py <entries.yaml> [-o <out.md>]
"""
from __future__ import annotations

import sys

# (yaml key, display label) — render order.
_CATEGORIES = [("added", "Added"), ("removed", "Removed"), ("modified", "Modified")]


def split_items(items) -> list[str]:
    """Flatten a list, splitting any `; `-joined item into its own entries."""
    out: list[str] = []
    for it in items or []:
        for part in str(it).split(";"):
            p = part.strip()
            if p:
                out.append(p)
    return out


def hoist_conventions(posts: list[dict]) -> tuple[dict, list[dict]]:
    """Return (conventions, per_post_residuals).

    conventions[cat] = items present in EVERY post for that category (order from
    the first post). Each per-post entry keeps only the items NOT hoisted.
    """
    norm = [{"slug": p["slug"], **{k: split_items(p.get(k)) for k, _ in _CATEGORIES}}
            for p in posts]

    conventions: dict[str, list[str]] = {}
    for key, _ in _CATEGORIES:
        if not norm:
            conventions[key] = []
            continue
        conventions[key] = [it for it in norm[0][key]
                            if all(it in p[key] for p in norm)]

    per_post = []
    for p in norm:
        residual = {"slug": p["slug"]}
        for key, _ in _CATEGORIES:
            common = set(conventions[key])
            residual[key] = [it for it in p[key] if it not in common]
        per_post.append(residual)
    return conventions, per_post


def _table(groups: list[tuple[str, list[str]]]) -> str:
    """Markdown table; the category label sits in the first row of its group,
    blank on subsequent rows. Returns "" when there are no rows."""
    lines = ["| Category | Items |", "|----------|-------|"]
    any_row = False
    for label, items in groups:
        for i, it in enumerate(items):
            lines.append(f"| {label if i == 0 else ''} | {it} |")
            any_row = True
    return "\n".join(lines) if any_row else ""


def render_changelog(title: str, intro: str, conventions: dict, per_post: list[dict]) -> str:
    parts = [f"# {title}", "", intro, "", "## Conventions Applied to Every Post", ""]
    conv = _table([(label, conventions.get(key, [])) for key, label in _CATEGORIES])
    parts.append(conv if conv else "_None._")
    for p in per_post:
        parts += ["", f"### {p['slug']}", ""]
        t = _table([(label, p.get(key, [])) for key, label in _CATEGORIES])
        parts.append(t if t else
                     "No post-specific changes — all changes are in the "
                     "Conventions table above.")
    return "\n".join(parts) + "\n"


def _main(argv):
    import argparse
    import yaml
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("entries", help="YAML of per-post change entries")
    ap.add_argument("-o", "--output", default=None, help="write markdown here (default: stdout)")
    a = ap.parse_args(argv)

    data = yaml.safe_load(open(a.entries)) or {}
    posts = data.get("posts") or []
    if not posts:
        print("error: no `posts` in entries file", file=sys.stderr)
        return 1
    conventions, per_post = hoist_conventions(posts)
    md = render_changelog(data.get("title", "Per-Post Changelog"),
                          data.get("intro", ""), conventions, per_post)
    if a.output:
        with open(a.output, "w") as f:
            f.write(md)
        print(f"wrote {a.output}", file=sys.stderr)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
