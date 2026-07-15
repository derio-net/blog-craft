#!/usr/bin/env python3
"""Sync blog-craft skills into OpenCode-discoverable mirrors.

OpenCode discovers skills as SKILL.md files under .opencode/skills/<name>/ and
project-level instructions from the opencode.json instructions array. Its slash
commands (/name) live in commands/<name>.md — separate from skills. This script
generates all three mirrors from canonical sources.

skills/<name>/SKILL.md stays the canonical source — never hand-edit
.opencode/skills/<name>/SKILL.md, .opencode/commands/<name>.md, or
.opencode/instructions/<rule>.md directly; all three are overwritten on sync.

Usage:
    uv run scripts/sync-opencode.py          # write/update all mirrors
    uv run scripts/sync-opencode.py --check  # exit non-zero on drift, no writes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

SKILLS_CANONICAL_DIR = REPO_ROOT / "skills"
SKILLS_MIRROR_DIR = REPO_ROOT / ".opencode" / "skills"

INSTRUCTIONS_CANONICAL_DIR = REPO_ROOT / ".opencode" / "instructions"
INSTRUCTIONS_MIRROR_DIR = REPO_ROOT / ".opencode" / "instructions"

COMMANDS_MIRROR_DIR = REPO_ROOT / ".opencode" / "commands"


def canonical_skills() -> dict[str, Path]:
    return {p.parent.name: p for p in sorted(SKILLS_CANONICAL_DIR.glob("*/SKILL.md"))}


def mirror_skills() -> dict[str, Path]:
    if not SKILLS_MIRROR_DIR.is_dir():
        return {}
    return {p.parent.name: p for p in sorted(SKILLS_MIRROR_DIR.glob("*/SKILL.md"))}


def find_skills_drift() -> list[str]:
    canonical = canonical_skills()
    mirror = mirror_skills()
    problems = []

    missing = sorted(set(canonical) - set(mirror))
    extra = sorted(set(mirror) - set(canonical))
    for name in missing:
        problems.append(f"{name}: missing from .opencode/skills/")
    for name in extra:
        problems.append(f"{name}: present in .opencode/skills/ with no canonical source")

    for name in sorted(set(canonical) & set(mirror)):
        if canonical[name].read_text() != mirror[name].read_text():
            problems.append(f"{name}: .opencode/skills/ content differs from canonical")

    return problems


def sync_skills() -> None:
    canonical = canonical_skills()

    for name, path in mirror_skills().items():
        if name not in canonical:
            skill_dir = path.parent
            for child in skill_dir.iterdir():
                child.unlink()
            skill_dir.rmdir()

    for name, src in canonical.items():
        dest_dir = SKILLS_MIRROR_DIR / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "SKILL.md"
        dest.write_text(src.read_text())
        source_note = dest_dir / ".source"
        source_note.write_text(
            f"Generated from {src.relative_to(REPO_ROOT)} by "
            f"scripts/sync-opencode.py. Do not edit SKILL.md here directly.\n"
        )


def _skill_frontmatter(skill_md: Path) -> dict[str, object]:
    """Parse SKILL.md frontmatter for name and description.

    Uses line-by-line parsing on unindented keys only because canonical
    descriptions contain unquoted colons (e.g. ``<!-- MEDIA: ... -->``)
    that YAML interprets as mapping keys, and sub-sections like ``arguments``
    contain their own ``description:`` fields that would shadow the top-level
    one in a naive scan.
    """
    text = skill_md.read_text()
    parts = text.split("---", 2)
    result: dict[str, object] = {}
    for line in parts[1].strip().splitlines():
        if not line.strip():
            continue
        # Only read top-level keys (no leading whitespace, not a list item)
        if line[0] in (" ", "\t", "-"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in ("name", "description"):
                result[key] = val
    return result


def _render_command(name: str, description: str) -> str:
    frontmatter = yaml.safe_dump({"description": description}, sort_keys=False, allow_unicode=True)
    return f"---\n{frontmatter}---\nUse the `{name}` skill to handle this request.\n\n$ARGUMENTS\n"


def canonical_commands() -> dict[str, str]:
    result = {}
    for name, skill_md in canonical_skills().items():
        frontmatter = _skill_frontmatter(skill_md)
        description = str(frontmatter.get("description", "")).strip()
        result[name] = _render_command(name, description)
    return result


def mirror_commands() -> dict[str, Path]:
    if not COMMANDS_MIRROR_DIR.is_dir():
        return {}
    return {p.stem: p for p in sorted(COMMANDS_MIRROR_DIR.glob("*.md"))}


def find_commands_drift() -> list[str]:
    canonical = canonical_commands()
    mirror = mirror_commands()
    problems = []

    missing = sorted(set(canonical) - set(mirror))
    extra = sorted(set(mirror) - set(canonical))
    for name in missing:
        problems.append(f"{name}: missing from .opencode/commands/")
    for name in extra:
        problems.append(f"{name}: present in .opencode/commands/ with no matching skill")

    for name in sorted(set(canonical) & set(mirror)):
        if mirror[name].read_text() != canonical[name]:
            problems.append(f"{name}: .opencode/commands/ content differs from generated canonical")

    return problems


def sync_commands() -> None:
    canonical = canonical_commands()

    for name, path in mirror_commands().items():
        if name not in canonical:
            path.unlink()

    COMMANDS_MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in canonical.items():
        dest = COMMANDS_MIRROR_DIR / f"{name}.md"
        dest.write_text(content)


def canonical_instructions() -> dict[str, Path]:
    if not INSTRUCTIONS_CANONICAL_DIR.is_dir():
        return {}
    return {p.stem: p for p in sorted(INSTRUCTIONS_CANONICAL_DIR.glob("*.md")) if p.name != ".gitkeep"}


def mirror_instructions() -> dict[str, Path]:
    if not INSTRUCTIONS_MIRROR_DIR.is_dir():
        return {}
    return {p.stem: p for p in sorted(INSTRUCTIONS_MIRROR_DIR.glob("*.md")) if p.name != ".gitkeep"}


def find_instructions_drift() -> list[str]:
    canonical = canonical_instructions()
    mirror = mirror_instructions()
    problems = []

    missing = sorted(set(canonical) - set(mirror))
    extra = sorted(set(mirror) - set(canonical))
    for name in missing:
        problems.append(f"{name}: missing from .opencode/instructions/")
    for name in extra:
        problems.append(f"{name}: present in .opencode/instructions/ with no canonical source")

    for name in sorted(set(canonical) & set(mirror)):
        if canonical[name].read_text() != mirror[name].read_text():
            problems.append(f"{name}: .opencode/instructions/ content differs from canonical")

    return problems


def sync_instructions() -> None:
    canonical = canonical_instructions()

    for name, path in mirror_instructions().items():
        if name not in canonical:
            path.unlink()

    INSTRUCTIONS_MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    for name, src in canonical.items():
        dest = INSTRUCTIONS_MIRROR_DIR / f"{name}.md"
        dest.write_text(src.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any mirror is out of sync; make no writes.",
    )
    args = parser.parse_args()

    if args.check:
        drift = find_skills_drift() + find_instructions_drift() + find_commands_drift()
        if drift:
            print("scripts/sync-opencode.py --check: drift detected:", file=sys.stderr)
            for line in drift:
                print(f"  - {line}", file=sys.stderr)
            print("Run scripts/sync-opencode.py (no --check) to fix.", file=sys.stderr)
            return 1
        print("scripts/sync-opencode.py --check: .opencode/ mirrors are in sync.")
        return 0

    sync_skills()
    sync_instructions()
    sync_commands()
    print(
        f"Synced {len(canonical_skills())} skill(s) into "
        f"{SKILLS_MIRROR_DIR.relative_to(REPO_ROOT)}/, "
        f"{len(canonical_instructions())} instruction file(s) into "
        f"{INSTRUCTIONS_MIRROR_DIR.relative_to(REPO_ROOT)}/, and "
        f"{len(canonical_commands())} command file(s) into "
        f"{COMMANDS_MIRROR_DIR.relative_to(REPO_ROOT)}/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
