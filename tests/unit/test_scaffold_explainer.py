"""P1.T2 -- scaffold-explainer.sh produces a valid bundle (no dossier)."""
import os
import subprocess
import sys

import pytest

from validate_explainers import ARCHETYPE_SECTIONS, parse_frontmatter, split_body, validate_post

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "scaffold-explainer.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
ENV = dict(os.environ, PYTHON=sys.executable)

SIX_SECTIONS = [
    "## Overview",
    "## Why it exists",
    "## How it works",
    "## Code walkthrough",
    "## Tradeoffs & alternatives",
    "## Try it yourself",
]


def test_scaffold_explainer(tmp_path):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(open(os.path.join(FIX, "answers-explainers-v2.yaml")).read())
    r = subprocess.run(
        ["bash", TOOL, "--config", str(cfg), "7", "my-feature"],
        capture_output=True, text=True, env=ENV,
    )
    assert r.returncode == 0, r.stderr

    idx = tmp_path / "content" / "docs" / "explainers" / "07-my-feature" / "index.md"
    assert idx.exists(), f"expected bundle at {idx}"

    content = idx.read_text()
    fm = parse_frontmatter(content)
    assert fm["post_number"] == 7
    assert fm["weight"] == 8  # 7 + weight_offset(1)
    assert fm["series"] == ["explainers"]
    assert fm["archetype"] == "feature-deep-dive"

    for heading in SIX_SECTIONS:
        assert heading in content, f"missing section heading: {heading}"


def test_scaffold_refuses_duplicate(tmp_path):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(open(os.path.join(FIX, "answers-explainers-v2.yaml")).read())
    subprocess.run(
        ["bash", TOOL, "--config", str(cfg), "7", "x"],
        capture_output=True, text=True, env=ENV, check=True,
    )
    r2 = subprocess.run(
        ["bash", TOOL, "--config", str(cfg), "7", "x"],
        capture_output=True, text=True, env=ENV,
    )
    assert r2.returncode != 0


# ---- archetype modes (P2) ----

def _scaffold_standalone(tmp_path, slug, *extra):
    """Run the scaffold in standalone mode; return the created .md text."""
    out = tmp_path / "out"
    r = subprocess.run(
        ["bash", TOOL, "--standalone", "--output", str(out), *extra, "3", slug],
        capture_output=True, text=True, env=ENV,
    )
    return r, out / f"03-{slug}.md"


@pytest.mark.parametrize("archetype", sorted(ARCHETYPE_SECTIONS))
def test_scaffold_each_archetype(tmp_path, archetype):
    r, md = _scaffold_standalone(tmp_path, archetype, "--archetype", archetype)
    assert r.returncode == 0, r.stderr
    content = md.read_text()
    fm = parse_frontmatter(content)
    assert fm["archetype"] == archetype

    # Exactly this archetype's headings appear...
    for section in ARCHETYPE_SECTIONS[archetype]:
        assert f"## {section}" in content, f"{archetype}: missing '## {section}'"
    # ...and no foreign heading from a *different* archetype leaks in.
    own = set(ARCHETYPE_SECTIONS[archetype])
    foreign = {s for a, secs in ARCHETYPE_SECTIONS.items() if a != archetype
               for s in secs} - own
    for section in foreign:
        assert f"## {section}\n" not in content, f"{archetype}: leaked '## {section}'"


@pytest.mark.parametrize("archetype", sorted(ARCHETYPE_SECTIONS))
def test_scaffold_roundtrips_through_validator(tmp_path, archetype):
    r, md = _scaffold_standalone(tmp_path, archetype, "--archetype", archetype)
    assert r.returncode == 0, r.stderr
    content = md.read_text()
    fm = parse_frontmatter(content)
    # A freshly scaffolded post must satisfy the archetype structural check.
    assert validate_post(fm, weight_offset=1, body=split_body(content)) == []


def test_scaffold_default_archetype_is_feature_deep_dive(tmp_path):
    r, md = _scaffold_standalone(tmp_path, "no-flag")
    assert r.returncode == 0, r.stderr
    fm = parse_frontmatter(md.read_text())
    assert fm["archetype"] == "feature-deep-dive"


def test_scaffold_unknown_archetype_fails(tmp_path):
    r, _ = _scaffold_standalone(tmp_path, "bad", "--archetype", "bogus")
    assert r.returncode != 0
