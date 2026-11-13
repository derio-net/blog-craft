"""The elements-of-style standard (R23): only the needless-word list fails."""
import pytest

import validate_writing_standard as vws


@pytest.fixture(scope="module")
def eos():
    return vws.load_standard("elements-of-style")


def _hits(text, std):
    return vws.run_checks(text, std).hits


def _by(text, std, check):
    return [h for h in _hits(text, std) if h.check == check]


def test_a_60_word_sentence_passes(eos):
    text = " ".join(["Word"] + ["word"] * 59) + ".\n"
    assert _hits(text, eos) == []


def test_there_is_no_length_check(eos):
    assert not any(c.kind in ("sentence_length", "average_sentence_length")
                   for c in eos.checks.values())


@pytest.mark.parametrize("text, phrase", [
    ("We wait in order to see the result.", "in order to"),
    ("The fact that it works is enough.", "the fact that"),
])
def test_needless_phrases_fail(eos, text, phrase):
    hits = _hits(text + "\n", eos)
    assert [h.check for h in hits] == ["needless_words"]
    assert hits[0].severity == "fail" and phrase in hits[0].message.lower()


@pytest.mark.parametrize("text", [
    "The writer, who is careful, omits words.",
    "The draft, which was long, got shorter.",
])
def test_context_dependent_phrases_only_warn(eos, text):
    hits = _hits(text + "\n", eos)
    assert hits and {h.check for h in hits} == {"maybe_needless"}
    assert all(h.severity == "warn" for h in hits)


def test_passive_anywhere_warns(eos):
    hits = _by("The file was deleted by the tool.\n", eos, "active_voice")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_active_sentence_has_no_passive_warning(eos):
    assert _by("The tool deleted the file.\n", eos, "active_voice") == []


def test_negative_form_warns_naming_the_positive(eos):
    hits = _by("He did not remember the date.\n", eos, "positive_form")
    assert len(hits) == 1 and hits[0].severity == "warn" and "forgot" in hits[0].message


def test_positive_form_passes(eos):
    assert _by("He forgot the date.\n", eos, "positive_form") == []


def test_three_loose_sentences_warn(eos):
    text = ("We opened the file, and it was empty. We ran the build, but it failed. "
            "We read the log, so we found the cause.\n")
    hits = _by(text, eos, "loose_sentences")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_two_loose_sentences_pass(eos):
    text = "We opened the file, and it was empty. We ran the build, but it failed.\n"
    assert _by(text, eos, "loose_sentences") == []


def test_only_needless_words_fails_by_default(eos):
    assert {c for c, s in eos.checks.items() if s.severity == "fail"} == {"needless_words"}
