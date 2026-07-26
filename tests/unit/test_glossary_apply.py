"""P3 — glossary_apply.py: safe, idempotent marker insertion.

Everything here is about NOT corrupting a post. The applier shares
glossary_scan's exclusion scanner, so a region the scanner refuses to propose
from is a region the applier refuses to write into — by construction, not by a
parallel implementation that could drift.
"""
import os
import subprocess
import sys

import yaml

import glossary_apply as ga  # tools/ on sys.path via conftest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APPLY = os.path.join(ROOT, "tools", "glossary_apply.py")

REG = {
    "NUT": {"name": "Network UPS Tools", "description": "d"},
    "SLO": {"name": "Service Level Objective", "description": "d"},
}


def _post(tmp_path, body, name="index.md"):
    p = tmp_path / name
    p.write_text(body)
    return p


# --- T1: first-occurrence insertion -----------------------------------------

def test_only_the_first_occurrence_is_marked(tmp_path):
    p = _post(tmp_path, "We ran NUT twice; NUT again.\n")
    edits = ga.apply_file(str(p), REG)
    assert len(edits) == 1
    assert p.read_text() == 'We ran {{< abbr "NUT" >}} twice; NUT again.\n'


def test_inflected_display_uses_the_positional_override(tmp_path):
    p = _post(tmp_path, "our SLOs slipped\n")
    ga.apply_file(str(p), REG)
    assert p.read_text() == 'our {{< abbr "SLO" "SLOs" >}} slipped\n'


def test_unregistered_terms_are_never_inserted(tmp_path):
    p = _post(tmp_path, "we used CDP heavily\n")
    assert ga.apply_file(str(p), REG) == []
    assert p.read_text() == "we used CDP heavily\n"


def test_edits_carry_file_and_one_based_line(tmp_path):
    p = _post(tmp_path, "line one\n\nwe ran NUT here\n")
    edits = ga.apply_file(str(p), REG)
    assert edits[0]["file"] == str(p)
    assert edits[0]["line"] == 3
    assert edits[0]["term"] == "NUT"


def test_multiple_terms_in_one_line_all_marked_once(tmp_path):
    p = _post(tmp_path, "NUT feeds the SLO dashboard\n")
    ga.apply_file(str(p), REG)
    assert p.read_text() == (
        '{{< abbr "NUT" >}} feeds the {{< abbr "SLO" >}} dashboard\n')


# --- T2: idempotence, all-occurrences mode, write discipline ----------------

def test_applying_twice_is_a_no_op(tmp_path):
    p = _post(tmp_path, "We ran NUT twice; NUT again.\n")
    ga.apply_file(str(p), REG)
    first = p.read_bytes()
    assert ga.apply_file(str(p), REG) == []
    assert p.read_bytes() == first


def test_an_already_marked_post_gains_nothing(tmp_path):
    body = 'we ran {{< abbr "NUT" >}} then NUT again\n'
    p = _post(tmp_path, body)
    assert ga.apply_file(str(p), REG) == []
    assert p.read_text() == body


def test_all_occurrences_mode_marks_every_one(tmp_path):
    p = _post(tmp_path, "We ran NUT twice; NUT again.\n")
    edits = ga.apply_file(str(p), REG, first_occurrence_only=False)
    assert len(edits) == 2
    assert p.read_text() == (
        'We ran {{< abbr "NUT" >}} twice; {{< abbr "NUT" >}} again.\n')


def test_excluded_regions_are_never_rewritten(tmp_path):
    body = (
        "---\ntitle: NUT setup\n---\n\n"
        "## NUT in the heading\n\n"
        "See [NUT](https://x.example/NUT).\n\n"
        "```\nNUT in a fence\n```\n\n"
        "Finally we wired NUT into the rack.\n"
    )
    p = _post(tmp_path, body)
    edits = ga.apply_file(str(p), REG)
    out = p.read_text()
    assert len(edits) == 1
    assert out.count("{{< abbr") == 1
    assert 'wired {{< abbr "NUT" >}} into the rack' in out
    # every excluded region byte-identical
    assert "title: NUT setup" in out
    assert "## NUT in the heading" in out
    assert "See [NUT](https://x.example/NUT)." in out
    assert "```\nNUT in a fence\n```" in out


def test_an_unchanged_file_is_not_rewritten(tmp_path):
    p = _post(tmp_path, "nothing to mark here\n")
    before = p.stat().st_mtime_ns
    assert ga.apply_file(str(p), REG) == []
    assert p.stat().st_mtime_ns == before


# --- CLI --------------------------------------------------------------------

def _blog(tmp_path, features=None):
    blog = tmp_path / "blog"
    (blog / "data").mkdir(parents=True)
    cfg = {"version": 5}
    if features is not None:
        cfg["features"] = features
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (blog / "data" / "glossary.yaml").write_text(yaml.safe_dump(REG))
    return blog


def test_cli_marks_and_reports(tmp_path):
    blog = _blog(tmp_path)
    p = _post(blog, "We ran NUT twice; NUT again.\n")
    r = subprocess.run([sys.executable, APPLY, "--config",
                        str(blog / ".blog-craft.yaml"), str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "NUT" in r.stdout
    assert p.read_text().count("{{< abbr") == 1


def test_cli_all_flag_overrides_config(tmp_path):
    blog = _blog(tmp_path, features={"glossary": {"first_occurrence_only": True}})
    p = _post(blog, "We ran NUT twice; NUT again.\n")
    r = subprocess.run([sys.executable, APPLY, "--config",
                        str(blog / ".blog-craft.yaml"), "--all", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert p.read_text().count("{{< abbr") == 2


def test_cli_honours_first_occurrence_only_false_from_config(tmp_path):
    blog = _blog(tmp_path, features={"glossary": {"first_occurrence_only": False}})
    p = _post(blog, "We ran NUT twice; NUT again.\n")
    r = subprocess.run([sys.executable, APPLY, "--config",
                        str(blog / ".blog-craft.yaml"), str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert p.read_text().count("{{< abbr") == 2
