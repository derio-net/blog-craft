"""Batch-rewrite changelog assembler — assemble_changelog.py (#28)."""
import os
import subprocess
import sys

import yaml

from assemble_changelog import hoist_conventions, render_changelog, split_items

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "assemble_changelog.py")


def test_split_items():
    assert split_items(["a; b", "c"]) == ["a", "b", "c"]
    assert split_items(["solo"]) == ["solo"]
    assert split_items(["x;  y"]) == ["x", "y"]   # tolerant of spacing


def test_hoist_common_to_conventions():
    posts = [
        {"slug": "01", "added": ["Missteps table", "D1"]},
        {"slug": "02", "added": ["Missteps table", "D2"]},
    ]
    conv, per = hoist_conventions(posts)
    assert conv["added"] == ["Missteps table"]
    by = {p["slug"]: p for p in per}
    assert by["01"]["added"] == ["D1"]
    assert by["02"]["added"] == ["D2"]


def test_non_common_not_hoisted():
    posts = [{"slug": "01", "added": ["X"]}, {"slug": "02", "added": ["Y"]}]
    conv, _ = hoist_conventions(posts)
    assert conv["added"] == []


def test_render_conventions_table_shape():
    conv = {"added": ["A1", "A2"], "removed": ["R1"], "modified": []}
    md = render_changelog("T", "intro", conv, [])
    assert "## Conventions Applied to Every Post" in md
    assert "| Added | A1 |" in md
    assert "|  | A2 |" in md          # subsequent items: blank category cell
    assert "| Removed | R1 |" in md
    assert "| Modified |" not in md    # empty category skipped


def test_no_batch_headers():
    conv = {"added": ["A"], "removed": [], "modified": []}
    per = [{"slug": "01", "added": ["Z"], "removed": [], "modified": []}]
    md = render_changelog("T", "i", conv, per)
    assert "Batch" not in md
    assert "### 01" in md


def test_post_with_no_residual_notes_it():
    conv = {"added": ["A"], "removed": [], "modified": []}
    per = [{"slug": "01", "added": [], "removed": [], "modified": []}]
    md = render_changelog("T", "i", conv, per)
    assert "### 01" in md
    assert "No post-specific changes" in md


def test_cli_roundtrip(tmp_path):
    entries = {
        "title": "Building — Changelog", "intro": "All rewritten.",
        "posts": [
            {"slug": "01", "added": ["Missteps table", "D1"]},
            {"slug": "02", "added": ["Missteps table", "D2"]},
        ],
    }
    f = tmp_path / "e.yaml"
    f.write_text(yaml.safe_dump(entries))
    r = subprocess.run([sys.executable, TOOL, str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "Conventions Applied to Every Post" in out
    assert "Missteps table" in out
    assert "### 01" in out and "### 02" in out
    assert "Batch" not in out
