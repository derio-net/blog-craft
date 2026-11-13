"""The five kinds phase 2 adds (phrases, average_sentence_length, loose_sentences,
nominalizations, abbreviations): one passing and one failing case each, run
through fixture standards in tmp_path so no shipped standard is needed."""
import os

import pytest

import validate_writing_standard as vws


def _standard(tmp_path, checks, terms="[]"):
    """A fixture standard named `fix` holding *checks* (yaml lines under checks:)."""
    block = "name: fix\ntitle: Fixture\nchecks:\n" + "".join(f"  {c}\n" for c in checks)
    block += f"terms: {terms}\n"
    with open(os.path.join(str(tmp_path), "fix.md"), "w") as f:
        f.write(f"# fix\n\nA fixture standard.\n\n```yaml\n{block}```\n")
    return vws.load_standard("fix", dirs=[str(tmp_path)])


def _hits(text, std, **kw):
    return vws.run_checks(text, std, **kw).hits


def _sentence(n, first="Word"):
    return " ".join([first] + ["word"] * (n - 1)) + "."


# ------------------------------------------------------------------ phrases

PHRASES = "needless: {kind: phrases, severity: fail, phrases: {in order to: to, the fact that: '(omit)'}}"


def test_phrase_hits_with_its_hint_in_the_message(tmp_path):
    hits = _hits("We wait in order to see the result.\n", _standard(tmp_path, [PHRASES]))
    assert len(hits) == 1 and hits[0].check == "needless" and hits[0].severity == "fail"
    assert "in order to" in hits[0].message and "to" in hits[0].message.split(":", 1)[1]


def test_phrase_is_case_insensitive(tmp_path):
    std = _standard(tmp_path, [PHRASES])
    assert len(_hits("In Order To see it, wait.\n", std)) == 1
    hits = _hits("The fact that it works is enough.\n", std)
    assert len(hits) == 1 and "(omit)" in hits[0].message


def test_phrase_needs_word_boundaries(tmp_path):
    std = _standard(tmp_path, [PHRASES])
    assert _hits("We sat in orderly rows.\n", std) == []
    assert _hits("We wait in order tomorrow.\n", std) == []


def test_phrase_across_a_line_break_hits(tmp_path):
    assert len(_hits("We wait in order\nto see it.\n", _standard(tmp_path, [PHRASES]))) == 1


def test_phrase_in_inline_code_does_not_hit(tmp_path):
    assert _hits("Run `in order to` now.\n", _standard(tmp_path, [PHRASES])) == []


# ------------------------------------------------------------------ average_sentence_length

AVERAGE = "average_sentence_length: {kind: average_sentence_length, severity: fail, max: 20}"


def test_page_averaging_21_words_hits_once_on_line_1(tmp_path):
    text = "\n\n" + _sentence(21) + " " + _sentence(21) + "\n"     # prose starts on line 3
    hits = _hits(text, _standard(tmp_path, [AVERAGE]))
    assert len(hits) == 1 and hits[0].line == 1 and hits[0].severity == "fail"
    assert "21" in hits[0].message and "20" in hits[0].message


def test_page_averaging_19_words_passes(tmp_path):
    text = _sentence(19) + " " + _sentence(19) + "\n"
    assert _hits(text, _standard(tmp_path, [AVERAGE])) == []


def test_average_mixes_long_and_short_sentences(tmp_path):
    text = _sentence(30) + " " + _sentence(8) + "\n"      # mean 19
    assert _hits(text, _standard(tmp_path, [AVERAGE])) == []


def test_empty_page_has_no_average_hit(tmp_path):
    assert _hits("---\ntitle: x\n---\n", _standard(tmp_path, [AVERAGE])) == []


def test_front_matter_waiver_suppresses_the_average(tmp_path, monkeypatch, capsys):
    (tmp_path / "std").mkdir()
    _standard(tmp_path / "std", [AVERAGE])
    monkeypatch.setattr(vws, "standards_dirs", lambda: [str(tmp_path / "std")])
    body = _sentence(21) + " " + _sentence(21) + "\n"
    waived = tmp_path / "waived.md"
    waived.write_text("---\nwriting_standard_waive: {average_sentence_length: quoted law}\n---\n" + body)
    plain = tmp_path / "plain.md"
    plain.write_text(body)
    assert vws.main(["--default", "fix", str(waived)]) == 0
    assert vws.main(["--default", "fix", str(plain)]) == 1
    assert f"FAIL: {plain}:1: average_sentence_length: " in capsys.readouterr().out


def test_front_matter_waiver_needs_a_reason(tmp_path, monkeypatch, capsys):
    (tmp_path / "std").mkdir()
    _standard(tmp_path / "std", [AVERAGE])
    monkeypatch.setattr(vws, "standards_dirs", lambda: [str(tmp_path / "std")])
    page = tmp_path / "p.md"
    page.write_text("---\nwriting_standard_waive: {average_sentence_length: ''}\n---\n"
                    + _sentence(21) + "\n")
    assert vws.main(["--default", "fix", str(page)]) == 1
    assert "waiver_reason" in capsys.readouterr().out


# ------------------------------------------------------------------ loose_sentences

LOOSE = "loose: {kind: loose_sentences, severity: warn, run: 3}"


def test_three_loose_sentences_in_a_row_hit_once(tmp_path):
    text = ("We opened the file, and it was empty. We ran the build, but it failed. "
            "We read the log, so we found the cause.\n")
    hits = _hits(text, _standard(tmp_path, [LOOSE]))
    assert len(hits) == 1 and hits[0].severity == "warn" and hits[0].line == 1
    assert "3" in hits[0].message


def test_two_loose_sentences_pass(tmp_path):
    text = "We opened the file, and it was empty. We ran the build, but it failed.\n"
    assert _hits(text, _standard(tmp_path, [LOOSE])) == []


def test_a_tight_sentence_breaks_the_run(tmp_path):
    text = ("We opened the file, and it was empty. We ran the build, but it failed. "
            "The log named the cause. We fixed it, which took a minute.\n")
    assert _hits(text, _standard(tmp_path, [LOOSE])) == []


def test_relative_pronouns_join_loose_clauses(tmp_path):
    text = ("The tool reads the page, which holds the prose. It writes a report, who reads it. "
            "The report lists each hit, and the hit names its line.\n")
    assert len(_hits(text, _standard(tmp_path, [LOOSE]))) == 1


def test_and_without_a_comma_is_not_a_loose_clause(tmp_path):
    text = "We like salt and pepper. We like bread and butter. We like tea and milk.\n"
    assert _hits(text, _standard(tmp_path, [LOOSE])) == []


# ------------------------------------------------------------------ nominalizations

NOMINAL = "nominal: {kind: nominalizations, severity: warn}"


@pytest.mark.parametrize("text", [
    "We make a decision today.",
    "They conduct an analysis of the logs.",
    "You carry out an assessment first.",
    "She gave a performance review.",
    "They performed the installation twice.",
    "We have a discussion about it.",
])
def test_weak_verb_plus_nominalization_hits(tmp_path, text):
    hits = _hits(text + "\n", _standard(tmp_path, [NOMINAL]))
    assert len(hits) == 1 and hits[0].severity == "warn"


@pytest.mark.parametrize("text", [
    "We make a list today.",
    "Take a moment to read it.",
    "We have a question.",
    "The decision is yours.",
])
def test_no_nominalization_passes(tmp_path, text):
    assert _hits(text + "\n", _standard(tmp_path, [NOMINAL])) == []


# ------------------------------------------------------------------ abbreviations

ABBR = "abbr: {kind: abbreviations, severity: warn}"


def test_unexplained_abbreviation_hits_once(tmp_path):
    hits = _hits("The CI runs on each push. The CI is fast.\n", _standard(tmp_path, [ABBR]))
    assert len(hits) == 1 and hits[0].severity == "warn" and "CI" in hits[0].message


@pytest.mark.parametrize("text", [
    "The continuous integration (CI) runs on each push. The CI is fast.",
    "The CI (continuous integration) runs on each push. The CI is fast.",
])
def test_spelled_out_at_first_use_passes(tmp_path, text):
    assert _hits(text + "\n", _standard(tmp_path, [ABBR])) == []


def test_spelled_out_only_later_still_hits(tmp_path):
    text = "The CI runs. Later, continuous integration (CI) is defined.\n"
    assert len(_hits(text, _standard(tmp_path, [ABBR]))) == 1


def test_a_term_is_not_an_abbreviation(tmp_path):
    std = _standard(tmp_path, [ABBR], terms="[CI]")
    assert _hits("The CI runs on each push.\n", std) == []
    assert _hits("The API runs.\n", std, terms=["api"]) == []


def test_abbreviation_lengths_and_code(tmp_path):
    std = _standard(tmp_path, [ABBR])
    assert _hits("I am here. A cat sat.\n", std) == []            # one letter
    assert _hits("The ABCDEFG word is long.\n", std) == []        # seven letters
    assert _hits("Run `GIT` now.\n", std) == []                   # inline code
    assert len(_hits("Open two PRs today.\n", std)) == 1          # plural form


def test_every_declared_kind_has_a_matcher():
    assert set(vws.MATCHERS) == set(vws.KINDS)


def test_a_phrase_inside_a_longer_listed_phrase_is_reported_once(tmp_path):
    std = _standard(tmp_path, [
        "needless: {kind: phrases, severity: fail, "
        "phrases: {the fact that: '(omit)', owing to the fact that: since}}"])
    hits = _hits("We stopped owing to the fact that it rained.\n", std)
    assert len(hits) == 1 and "since" in hits[0].message
    assert len(_hits("The fact that it rained stopped us.\n", std)) == 1
