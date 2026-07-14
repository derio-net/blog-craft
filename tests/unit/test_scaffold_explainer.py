"""P1.T2 -- scaffold-explainer.sh produces a valid bundle (no dossier)."""
import os
import subprocess
import sys

from validate_explainers import parse_frontmatter

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
