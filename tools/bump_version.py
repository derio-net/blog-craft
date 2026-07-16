#!/usr/bin/env python3
"""Bump or verify blog-craft's canonical version.

`pyproject.toml` `[project].version` is the single source of truth.
`.claude-plugin/plugin.json` `version` and `.claude-plugin/marketplace.json`
`plugins[].version` must match it byte-for-byte; this script keeps them in
lockstep (minimal-diff: only the version strings are rewritten).

Usage:
    tools/bump_version.py patch          # 0.5.0 -> 0.5.1
    tools/bump_version.py minor          # 0.5.0 -> 0.6.0
    tools/bump_version.py major          # 0.5.9 -> 1.0.0
    tools/bump_version.py 0.7.2          # set explicitly
    tools/bump_version.py --check        # verify agreement; exit 1 on drift

On merge, .github/workflows/auto-tag.yml cuts the matching `vX.Y.Z` tag.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parent.parent
_TOML_VER = re.compile(r'^(version\s*=\s*")([^"]+)(")', re.M)
_JSON_VER = re.compile(r'("version"\s*:\s*")[^"]*(")')
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _pyproject(root): return root / "pyproject.toml"
def _plugin(root): return root / ".claude-plugin" / "plugin.json"
def _marketplace(root): return root / ".claude-plugin" / "marketplace.json"


def read_pyproject_version(root: pathlib.Path) -> str:
    m = _TOML_VER.search(_pyproject(root).read_text())
    if not m:
        raise SystemExit(f"error: no `version = \"...\"` line in {_pyproject(root)}")
    return m.group(2)


def versions(root: pathlib.Path) -> dict[str, str]:
    out = {"pyproject.toml": read_pyproject_version(root)}
    out[".claude-plugin/plugin.json"] = json.loads(_plugin(root).read_text())["version"]
    mk = json.loads(_marketplace(root).read_text())
    for i, p in enumerate(mk.get("plugins", [])):
        out[f"marketplace.json[plugins][{i}]"] = p["version"]
    return out


def compute_new(old: str, arg: str) -> str:
    if _SEMVER.match(arg):
        return arg
    maj, mi, pa = (int(x) for x in old.split("."))
    if arg == "major":
        return f"{maj + 1}.0.0"
    if arg == "minor":
        return f"{maj}.{mi + 1}.0"
    if arg == "patch":
        return f"{maj}.{mi}.{pa + 1}"
    raise SystemExit(f"error: expected patch|minor|major|X.Y.Z, got {arg!r}")


def write_all(root: pathlib.Path, new: str) -> None:
    pp = _pyproject(root)
    pp.write_text(_TOML_VER.sub(rf"\g<1>{new}\g<3>", pp.read_text(), count=1))
    for path in (_plugin(root), _marketplace(root)):
        path.write_text(_JSON_VER.sub(rf"\g<1>{new}\g<2>", path.read_text()))


def check(root: pathlib.Path) -> int:
    vs = versions(root)
    w = max(len(k) for k in vs)
    for k, v in vs.items():
        print(f"{k:<{w}}  {v}")
    if len(set(vs.values())) == 1:
        print("ok — versions agree")
        return 0
    print("DRIFT — run `tools/bump_version.py <patch|minor|major|X.Y.Z>` to resync",
          file=sys.stderr)
    return 1


def bump(root: pathlib.Path, arg: str) -> int:
    old = read_pyproject_version(root)
    new = compute_new(old, arg)
    if new == old:
        print(f"already at {new}, nothing to do")
        return 0
    write_all(root, new)
    print(f"bumped {old} -> {new} (pyproject.toml + plugin.json + marketplace.json)")
    return 0


def main(argv: list[str], root: pathlib.Path = _REPO) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    arg = argv[0]
    return check(root) if arg == "--check" else bump(root, arg)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
