"""R19 — /blog-post and /post-rewrite apply a post's resolved writing standard.

While drafting they load the resolved standard's reference file, and their gate
step runs the checker beside the educational gate.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _section(skill, heading):
    text = open(os.path.join(ROOT, "skills", skill, "SKILL.md")).read()
    m = re.search(r"^### " + re.escape(heading) + r".*?(?=^### |^## |\Z)", text, re.M | re.S)
    assert m, f"{skill}: no section starting {heading!r}"
    return m.group(0)


def _loads_the_standard(section):
    assert "apply-writing-standard/standards/<standard>.md" in section
    assert "writing_standard" in section   # front matter / series default resolution
    assert "none" in section               # an opted-out post loads nothing


def _gates_with_the_checker(section):
    assert "validate_writing_standard.py" in section
    assert "--config <blog" in section.split("validate_writing_standard.py", 1)[1][:200]


def test_blog_post_loads_the_resolved_standard_while_drafting():
    _loads_the_standard(_section("blog-post", "Step 4:"))


def test_blog_post_gate_runs_the_checker():
    _gates_with_the_checker(_section("blog-post", "Step 11:"))


def test_post_rewrite_loads_the_resolved_standard_while_drafting():
    _loads_the_standard(_section("post-rewrite", "Step 6:"))


def test_post_rewrite_gate_runs_the_checker():
    _gates_with_the_checker(_section("post-rewrite", "Step 9:"))


def test_post_rewrite_batch_gate_names_the_writing_standard():
    assert "writing standard" in _section("post-rewrite", "The loop")
