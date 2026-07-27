"""The shipped version must have a CHANGELOG section.

Two gates already guard the version itself — `bump_version.py --check` (lockstep
across pyproject/both manifests/uv.lock) and `check_version_bump_needed.py` (a PR
touching the shipped surface must bump). Nothing guarded the CHANGELOG, so 0.14.1
shipped a user-facing fix with no entry and the file read 0.15.0 -> 0.14.0 with a
hole in it (fixed retroactively in #57).

The header claims "All notable changes to blog-craft are recorded here". This is
what makes that true.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
PYPROJECT = os.path.join(ROOT, "pyproject.toml")

_SECTION = re.compile(r"^## \[([^\]]+)\]", re.M)
_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _current_version():
    with open(PYPROJECT) as f:
        m = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M)
    assert m, "no version in pyproject.toml"
    return m.group(1)


def _sections():
    with open(CHANGELOG) as f:
        return _SECTION.findall(f.read())


def test_current_version_has_a_changelog_section():
    version = _current_version()
    sections = _sections()
    assert version in sections, (
        "pyproject.toml is at %s but CHANGELOG.md has no `## [%s]` section. "
        "A version bump without an entry leaves the shipped surface undocumented "
        "— add the section before merging.\nSections found: %s"
        % (version, version, ", ".join(sections[:6])))


def test_released_sections_are_ordered_newest_first():
    """A hole or an out-of-order section is the visible symptom of a skipped
    entry, which is how 0.14.1's omission surfaced."""
    released = []
    for s in _sections():
        m = _SEMVER.match(s)
        if m:
            released.append((tuple(int(g) for g in m.groups()), s))
    assert released, "no released sections parsed"
    ordered = sorted(released, key=lambda t: t[0], reverse=True)
    assert released == ordered, (
        "CHANGELOG sections are not newest-first:\n  got:      %s\n  expected: %s"
        % ([s for _, s in released], [s for _, s in ordered]))


@pytest.mark.parametrize("heading", ["Unreleased"])
def test_unreleased_section_is_present(heading):
    """Keep-a-Changelog's staging area — its absence means someone edited the
    top of the file by hand and dropped it."""
    assert heading in _sections(), "`## [%s]` section missing" % heading
