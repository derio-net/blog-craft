#!/usr/bin/env python3
"""Lint ```mermaid fences for common syntax errors before render (#27).

A regex linter (no node/mmdc toolchain) that catches high-confidence, dead-on-
render mistakes with file:line:

  - bare <br>                 Hextra's bundled Mermaid wants <br/> (self-closed)
  - unbalanced brackets       [] () {} outside quotes must balance per block

(An edge whose endpoint is a subgraph id is NOT on this list: mermaid
flowcharts accept it and render it — #74 dropped a rule that claimed otherwise.
A rule earns its place here only for a form that demonstrably fails to render.)

Opt-out with `quality.mermaid_syntax: false` (absent => on). Blocking when on.

Library:
  find_mermaid_blocks(md) -> list[(start_line, src)]
  lint_mermaid_block(src) -> list[(offset, message)]
  validate_file(path, md) -> list[str]   ("path:line: message")
CLI:
  validate_mermaid.py --config <.blog-craft.yaml> <index.md> [<index.md> ...]
"""
from __future__ import annotations

import re
import sys

_BARE_BR = re.compile(r"<br\s*>")   # <br> / <br > — NOT <br/> or <br />


def find_mermaid_blocks(md: str) -> list[tuple[int, str]]:
    """Return (start_line, block_src) per ```mermaid fence.

    start_line is the 1-based line of the first content line inside the fence."""
    blocks: list[tuple[int, str]] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^\s*(`{3,}|~{3,})\s*mermaid\s*$", lines[i])
        if m:
            fence = m.group(1)[0]
            buf, j = [], i + 1
            while j < len(lines) and not re.match(rf"^\s*{re.escape(fence)}{{3,}}\s*$", lines[j]):
                buf.append(lines[j])
                j += 1
            blocks.append((i + 2, "\n".join(buf)))
            i = j + 1
        else:
            i += 1
    return blocks


def _strip_quoted(s: str) -> str:
    return re.sub(r'"[^"]*"', "", s)


def lint_mermaid_block(src: str) -> list[tuple[int, str]]:
    issues: list[tuple[int, str]] = []
    for idx, line in enumerate(src.splitlines()):
        # R2 — bare <br>
        if _BARE_BR.search(line):
            issues.append((idx, "bare <br> — use <br/> (self-closed) for the bundled Mermaid"))

    # R3 — unbalanced brackets across the block (quoted spans removed)
    stripped = _strip_quoted(src)
    for open_c, close_c, name in (("[", "]", "square"), ("(", ")", "round"), ("{", "}", "curly")):
        if stripped.count(open_c) != stripped.count(close_c):
            issues.append((0, f"unbalanced {name} brackets '{open_c}{close_c}' — an "
                              f"unquoted bracket in a label breaks the parse"))

    issues.sort()
    return issues


def validate_file(path: str, md: str) -> list[str]:
    out: list[str] = []
    for start, src in find_mermaid_blocks(md):
        for offset, msg in lint_mermaid_block(src):
            out.append(f"{path}:{start + offset}: {msg}")
    return out


# --------------------------------------------------------------------------- CLI

def _main(argv):
    import argparse
    import yaml
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load(open(a.config)) or {}
    gate_enabled = (cfg.get("quality") or {}).get("mermaid_syntax", True) is not False

    failed: dict[str, list[str]] = {}
    checked = 0
    for p in a.paths:
        try:
            md = open(p).read()
        except OSError as e:  # noqa: BLE001
            failed[p] = [f"{p}: could not read: {e}"]
            continue
        checked += 1
        fails = validate_file(p, md)
        if fails:
            failed[p] = fails

    if not gate_enabled:
        # A disabled gate must still SCAN and still be LOUD about it. The
        # principle, from frank 77e68e37: "a gate nobody runs reports nothing,
        # including how far behind you are" — that is the FAILURE being fixed,
        # not the goal. Always exits 0: visible, never build-breaking.
        total = sum(len(fs) for fs in failed.values())
        plural = "" if total == 1 else "s"
        print(f"GATE DISABLED (quality.mermaid_syntax: false) — would report "
              f"{total} finding{plural} across {checked} file(s) checked",
              file=sys.stderr)
        if failed:
            for fs in failed.values():
                for x in fs:
                    print(f"  {x}", file=sys.stderr)
        return 0

    if failed:
        print("MERMAID SYNTAX CHECK FAILED", file=sys.stderr)
        for fs in failed.values():
            for x in fs:
                print(f"  {x}", file=sys.stderr)
        print("\n  Fix the diagram(s), or set `quality.mermaid_syntax: false` to "
              "opt out.", file=sys.stderr)
        return 1
    print(f"MERMAID SYNTAX OK: {checked} file(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
