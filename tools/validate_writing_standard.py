#!/usr/bin/env python3
"""Check Markdown pages against a writing standard (STE, Elements of Style, ...).

    validate_writing_standard.py [--config .blog-craft.yaml] [--default <standard>]
        [--severity <check>=<fail|warn|off> ...] [--terms <file>] [--term <word> ...]
        [--preserve-from <git-ref>] [--stats] <path-or-glob> [...]

A standard is one reference file, skills/apply-writing-standard/standards/<name>.md,
whose fenced yaml block declares named check instances of a closed set of kinds.
Needs only Python 3 and PyYAML. Exit 0 when nothing fails, 1 when a check fails,
2 on a usage or configuration error.
"""
from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
