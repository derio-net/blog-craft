#!/usr/bin/env python3
"""Ensure a config key exists in .blog-craft.yaml, seeding it if missing.

If the key is absent, it is appended with its default value and a comment
showing the allowed values. The file is modified in-place (a .bak is saved).

Usage:
    python3 tools/seed_config.py --config .blog-craft.yaml \\
        --key voice_level --default balanced \\
        --values "dry,balanced,rich" \\
        --comment "How thick the persona frame is."
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml


def seed_key(
    config_path: Path,
    key: str,
    default: str,
    comment: str = "",
    values: str = "",
) -> bool:
    """Ensure *key* exists in the YAML config. Return True if seeded.

    *key* may be dotted (``quality.lint.enabled``): the segments are a nested
    mapping path, seeded as a real YAML block (extending any existing
    ancestors in place), never as a flat literal ``a.b.c`` key. *default* is
    parsed as a YAML scalar, so ``true`` seeds a boolean, not a string.
    """
    config_path = config_path.resolve()
    if not config_path.is_file():
        print(f"ERROR: config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    # Walk the dotted path; depth = how many leading segments already exist.
    parts = key.split(".")
    node = data
    depth = 0
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
            depth += 1
        else:
            break

    if depth == len(parts):
        print(f"  {key}: already set to {node!r}")
        return False

    comment_line = comment
    if values:
        allowed = f"options: {values}"
        comment_line = f"{comment} ({allowed})" if comment else allowed

    with open(config_path) as f:
        raw_lines = f.readlines()

    if depth == 0:
        indent = ""
        # Insert before the first top-level key that sorts after ours, or at end
        insert_pos = len(raw_lines)
        for i, line in enumerate(raw_lines):
            stripped = line.rstrip()
            if stripped.startswith("#") or stripped == "":
                continue
            # Top-level YAML key
            if not stripped[0].isspace() and ":" in stripped and not stripped.startswith("-"):
                candidate = stripped.split(":")[0].strip()
                if candidate > parts[0]:
                    insert_pos = i
                    break
    else:
        # Insert right after the deepest existing ancestor's mapping line,
        # located by walking the path segments at their block indentation.
        insert_pos = None
        ancestor_line = ""
        ancestor_indent = 0
        want = 0
        for i, line in enumerate(raw_lines):
            stripped = line.rstrip("\n")
            if not stripped.strip() or stripped.lstrip().startswith("#"):
                continue
            cur_indent = len(stripped) - len(stripped.lstrip(" "))
            if cur_indent == 2 * want and stripped.lstrip().startswith(parts[want] + ":"):
                want += 1
                if want == depth:
                    insert_pos = i + 1
                    ancestor_line = stripped
                    ancestor_indent = cur_indent
                    break
        # The ancestor line must be a bare block-mapping line (`quality:`,
        # nothing after the colon but an optional comment). A flow-style
        # mapping (`quality: {gate: {...}}`) or a scalar (`quality: true`)
        # cannot take an inserted child block — inserting would corrupt the
        # YAML, so bail out loudly instead.
        if insert_pos is None or not re.fullmatch(
            r"\s*[\w.-]+:\s*(#.*)?", ancestor_line
        ):
            print(
                f"ERROR: could not locate existing block for "
                f"{'.'.join(parts[:depth])!r} in {config_path} "
                "(non-block YAML style?); seed it manually",
                file=sys.stderr,
            )
            sys.exit(1)
        # Match the ancestor's existing children's indentation when it has
        # any (a 4-space-indented config must get 4-space siblings, or the
        # existing children silently nest under the new key); fall back to
        # ancestor_indent + 2 for a childless ancestor.
        child_indent = None
        for line in raw_lines[insert_pos:]:
            stripped = line.rstrip("\n")
            if not stripped.strip() or stripped.lstrip().startswith("#"):
                continue
            cur_indent = len(stripped) - len(stripped.lstrip(" "))
            if cur_indent > ancestor_indent:
                child_indent = cur_indent
            break
        if child_indent is None:
            child_indent = ancestor_indent + 2
        indent = " " * child_indent

    # Build the missing subtree (a scalar for a flat key), indented to sit
    # under the deepest existing ancestor.
    subtree = yaml.safe_load(default)
    for part in reversed(parts[depth:]):
        subtree = {part: subtree}
    block = yaml.dump(subtree, default_flow_style=False, sort_keys=False).rstrip("\n")

    lines_to_add = []
    if comment_line:
        for line in comment_line.split("\n"):
            lines_to_add.append(f"{indent}# {line}")
    for line in block.split("\n"):
        lines_to_add.append(f"{indent}{line}")

    for line in lines_to_add:
        raw_lines.insert(insert_pos, line + "\n")
        insert_pos += 1

    with open(config_path, "w") as f:
        f.writelines(raw_lines)

    print(f"  {key}: seeded with {default!r}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to .blog-craft.yaml")
    parser.add_argument("--key", required=True, help="Config key to ensure exists")
    parser.add_argument("--default", required=True, help="Default value if missing")
    parser.add_argument("--comment", default="", help="Comment to place above the key")
    parser.add_argument("--values", default="", help="Comma-separated allowed values")
    args = parser.parse_args()

    config_path = Path(args.config)
    bak_path = config_path.with_suffix(config_path.suffix + ".bak")
    shutil.copy2(config_path, bak_path)

    seeded = seed_key(config_path, args.key, args.default, args.comment, args.values)
    if seeded:
        print(f"  Backup saved to {bak_path}")
    else:
        bak_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
