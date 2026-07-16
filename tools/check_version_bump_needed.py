#!/usr/bin/env python3
"""Fail a PR that changes shipped behavior without bumping the version.

A PR whose diff touches a version-required path (the shipped surface) must bump
`pyproject.toml`'s version, or CI fails. Docs / tests / specs alone never
require a bump. Mirrors super-fr's check-version-bump-needed.py.

Usage:
    tools/check_version_bump_needed.py <base-ref>
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import bump_version as bv

_REPO = pathlib.Path(__file__).resolve().parent.parent

# The shipped surface — changing any of these is user-observable and needs a bump.
_REQUIRED_PREFIXES = ("templates/", "tools/", "skills/", "agents/", ".claude-plugin/")


def requires_bump(path: str) -> bool:
    if not path.startswith(_REQUIRED_PREFIXES):
        return False
    # tests co-located under a required prefix don't themselves change behavior
    return "/tests/" not in f"/{path}" and not path.startswith("tools/tmp/")


def guard_fails(changed: list[str], base_version: str, head_version: str) -> bool:
    if base_version != head_version:
        return False
    return any(requires_bump(p) for p in changed)


def _git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=_REPO, check=True,
                          capture_output=True, text=True).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: tools/check_version_bump_needed.py <base-ref>", file=sys.stderr)
        return 2
    base = argv[0]
    changed = [p for p in _git(["diff", "--name-only", f"{base}...HEAD"]).splitlines() if p]
    head_version = bv.read_pyproject_version(_REPO)
    # pyproject.toml may not exist at base (the PR that introduces it) — treat a
    # missing/unparseable base version as "changed" so the guard passes.
    try:
        m = bv._TOML_VER.search(_git(["show", f"{base}:pyproject.toml"]))
        base_version = m.group(2) if m else ""
    except subprocess.CalledProcessError:
        base_version = ""

    if not guard_fails(changed, base_version, head_version):
        print(f"ok — version {base_version} -> {head_version}, "
              f"or no shipped-surface paths changed")
        return 0

    print("ERROR: shipped-surface changes require a version bump.", file=sys.stderr)
    print("Run `tools/bump_version.py patch` (or minor/major if warranted).", file=sys.stderr)
    for p in (p for p in changed if requires_bump(p)):
        print(f"  - {p}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
