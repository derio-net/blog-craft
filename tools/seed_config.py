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
    """Ensure *key* exists in the YAML config. Return True if seeded."""
    config_path = config_path.resolve()
    if not config_path.is_file():
        print(f"ERROR: config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    if key in data:
        print(f"  {key}: already set to {data[key]!r}")
        return False

    comment_line = comment
    if values:
        allowed = f"options: {values}"
        comment_line = f"{comment} ({allowed})" if comment else allowed

    # Build the comment + key line(s)
    key_value = yaml.dump({key: default}, default_flow_style=False, sort_keys=False).strip()
    lines_to_add = []
    if comment_line:
        for line in comment_line.split("\n"):
            lines_to_add.append(f"# {line}")
    lines_to_add.append(key_value)

    # Read raw lines, insert key before the last non-empty meaningful section
    with open(config_path) as f:
        raw_lines = f.readlines()

    # Insert before the first top-level key that sorts after ours, or at end
    insert_pos = len(raw_lines)
    for i, line in enumerate(raw_lines):
        stripped = line.rstrip()
        if stripped.startswith("#") or stripped.startswith("\n") or stripped == "":
            continue
        # Top-level YAML key
        if not stripped[0].isspace() and ":" in stripped and not stripped.startswith("-"):
            candidate = stripped.split(":")[0].strip()
            if candidate > key:
                insert_pos = i
                break

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
