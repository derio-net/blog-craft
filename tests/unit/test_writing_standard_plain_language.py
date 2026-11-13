"""The plain-language standard (R24): two exact failures, the rest warn."""
import pytest

import validate_writing_standard as vws


@pytest.fixture(scope="module")
def plain():
    return vws.load_standard("plain-language")


def _hits(text, std):
    return vws.run_checks(text, std).hits


def _by(text, std, check):
    return [h for h in _hits(text, std) if h.check == check]


def _sentence(n):
    return " ".join(["Word"] + ["word"] * (n - 1)) + "."


def test_average_over_20_fails(plain):
    hits = _hits(_sentence(21) + " " + _sentence(21) + "\n", plain)
    assert [(h.check, h.severity, h.line) for h in hits] == [("average_sentence_length", "fail", 1)]


def test_average_19_with_one_30_word_sentence_passes(plain):
    assert _hits(_sentence(30) + " " + _sentence(8) + "\n", plain) == []


def test_a_36_word_sentence_warns(plain):
    hits = _hits(_sentence(36) + " " + _sentence(4) + "\n", plain)      # mean 20
    assert [(h.check, h.severity) for h in hits] == [("long_sentence", "warn")]


def test_a_35_word_sentence_does_not_warn(plain):
    assert _by(_sentence(35) + " " + _sentence(5) + "\n", plain, "long_sentence") == []


def test_shall_fails_naming_must(plain):
    hits = _by("You shall sign the form.\n", plain, "must_not_shall")
    assert len(hits) == 1 and hits[0].severity == "fail" and "must" in hits[0].message


def test_must_passes(plain):
    assert _hits("You must sign the form.\n", plain) == []


def test_commence_warns_naming_start(plain):
    hits = _by("We commence the work today.\n", plain, "simple_words")
    assert len(hits) == 1 and hits[0].severity == "warn" and "start" in hits[0].message


def test_simple_words_list_has_at_least_25_entries(plain):
    assert len(plain.checks["simple_words"].params["words"]) >= 25


def test_nominalization_warns(plain):
    hits = _by("We make a decision today.\n", plain, "nominalizations")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_plain_verb_passes(plain):
    assert _hits("We decide today.\n", plain) == []


def test_unexplained_abbreviation_warns(plain):
    hits = _by("Open a PR for the change.\n", plain, "abbreviations")
    assert len(hits) == 1 and hits[0].severity == "warn" and "PR" in hits[0].message


def test_spelled_out_abbreviation_passes(plain):
    assert _hits("Open a pull request (PR) for the change. The PR runs the tests.\n", plain) == []


def test_seven_sentence_paragraph_warns(plain):
    hits = _by(" ".join(["We stop here."] * 7) + "\n", plain, "paragraph_length")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_six_sentence_paragraph_passes(plain):
    assert _by(" ".join(["We stop here."] * 6) + "\n", plain, "paragraph_length") == []


def test_passive_warns(plain):
    hits = _by("The form was signed by the clerk.\n", plain, "active_voice")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_only_two_checks_fail_by_default(plain):
    assert {c for c, s in plain.checks.items() if s.severity == "fail"} == {
        "average_sentence_length", "must_not_shall"}
