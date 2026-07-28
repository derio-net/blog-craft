"""P3.T1 — reader-arc methodology reference + SKILL.md/checklist amendments.

Grep-style contract tests, same style as the other skill-contract tests: they
pin the load-bearing strings of the prose (the organizing rule, the three arc
sections, the mode-conditional carve-out, the failure signature, the checklist
items) without trying to judge the prose itself.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL_DIR = os.path.join(ROOT, "skills", "educational-writing")
READER_ARC = os.path.join(SKILL_DIR, "references", "reader-arc.md")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
CHECKLIST = os.path.join(SKILL_DIR, "references", "checklist.md")


def _read(path):
    assert os.path.exists(path), f"missing file: {path}"
    with open(path) as f:
        return f.read()


# ---- references/reader-arc.md ----

def test_reader_arc_states_the_organizing_rule():
    text = _read(READER_ARC)
    assert "reader's arc" in text
    assert "session's chronology" in text
    assert "raw material" in text


def test_reader_arc_beginning_is_the_lay_of_the_land():
    assert "lay of the land" in _read(READER_ARC)


def test_reader_arc_end_is_what_transfers():
    assert "What transfers" in _read(READER_ARC)


def test_reader_arc_is_mode_conditional():
    """One statement must name both sides of the split: the landscape applies
    to tutorial/explanation posts; how-to/reference posts keep the tight
    three-beat orientation."""
    text = _read(READER_ARC)
    assert re.search(r"tutorial", text, re.IGNORECASE)
    assert re.search(r"explanation", text, re.IGNORECASE)
    assert re.search(r"how-to", text, re.IGNORECASE)
    assert re.search(r"reference", text, re.IGNORECASE)


def test_reader_arc_sizes_the_beginning_proportionally():
    text = _read(READER_ARC)
    assert "sized" in text
    assert "idiosyncratic" in text


# ---- SKILL.md amendments ----

def test_skill_references_reader_arc():
    assert "reader-arc.md" in _read(SKILL_MD)


def test_skill_failure_signatures_include_session_skeleton():
    text = _read(SKILL_MD)
    # scope to §4 so the signature lives in the failure list, not elsewhere
    section4 = text.split("## 4.")[1].split("\n## ")[0]
    assert "Session-skeleton" in section4


# ---- references/checklist.md amendments ----

def test_checklist_has_landscape_item():
    assert re.search(r"lay[- ]of[- ]the[- ]land", _read(CHECKLIST))


def test_checklist_has_what_transfers_item():
    text = _read(CHECKLIST)
    assert "keeps beyond this repo" in text
    assert "not a recap" in text
