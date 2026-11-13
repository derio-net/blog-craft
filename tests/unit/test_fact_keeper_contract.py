"""P3 — fact-keeper agent contract (R18).

Grep-style, like test_cold_reader_contract.py: read-only tools, exactly two
inputs, over-share reporting, and the kept / changed / lost / added table.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FACT_KEEPER = os.path.join(ROOT, "agents", "fact-keeper.md")


def _read(path):
    assert os.path.exists(path), f"missing file: {path}"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "no yaml frontmatter block"
    return m.group(1)


def test_the_agent_is_named_fact_keeper():
    fm = _frontmatter(_read(FACT_KEEPER))
    assert re.search(r"^name:\s*fact-keeper\s*$", fm, re.MULTILINE)
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE)


def test_its_tools_are_exactly_read_grep_glob():
    fm = _frontmatter(_read(FACT_KEEPER))
    m = re.search(r"^tools:\s*(.+)$", fm, re.MULTILINE)
    assert m, "no tools line in frontmatter"
    assert {t.strip() for t in m.group(1).split(",")} == {"Read", "Grep", "Glob"}


def test_it_takes_exactly_two_paths():
    text = _read(FACT_KEEPER)
    assert "exactly two paths" in text
    assert "original" in text and "rewrite" in text


def test_it_reports_an_over_share_instead_of_reading_it():
    text = _read(FACT_KEEPER)
    assert "over-share" in text
    assert "do not open it" in text


def test_it_returns_kept_changed_lost_and_added():
    text = _read(FACT_KEEPER)
    for status in ("kept", "changed", "lost", "added"):
        assert f"`{status}`" in text, f"missing status {status}"
    assert "both wordings" in text


def test_it_defines_a_fact():
    text = _read(FACT_KEEPER)
    assert "A fact is" in text
    for part in ("behavior", "condition", "default", "limit", "order of steps", "name"):
        assert part in text, f"fact definition misses {part!r}"


def test_it_never_calls_a_page_conformant_or_compliant():
    text = _read(FACT_KEEPER).lower()
    assert "conformant" not in text and "compliant" not in text
