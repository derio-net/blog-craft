"""The ste standard's checks: one passing and one failing fixture each, at default severity."""
import pytest

import validate_writing_standard as vws


@pytest.fixture(scope="module")
def ste():
    return vws.load_standard("ste")


def _hits(text, std, check, **kw):
    return [h for h in vws.run_checks(text, std, **kw) if h.check == check]


def _words(n, first="Word"):
    return " ".join([first] + ["word"] * (n - 1)) + "."


# ---- sentence_length (fail)

def test_step_sentence_over_20_words_fails(ste):
    hits = _hits("1. " + _words(21, "Open") + "\n", ste, "sentence_length")
    assert len(hits) == 1 and hits[0].severity == "fail" and hits[0].line == 1
    assert "21" in hits[0].message


def test_step_sentence_of_20_words_passes(ste):
    assert _hits("1. " + _words(20, "Open") + "\n", ste, "sentence_length") == []


def test_descriptive_sentence_over_25_fails_and_25_passes(ste):
    assert len(_hits(_words(26) + "\n", ste, "sentence_length")) == 1
    assert _hits(_words(25) + "\n", ste, "sentence_length") == []


def test_inline_code_counts_as_one_word(ste):
    text = "1. Run `a b c d e f g h i j k l m n o p q r s t u v w x y z` " + " ".join(["now"] * 18) + ".\n"
    assert _hits(text, ste, "sentence_length") == []   # 1 + 1 + 18 = 20 words


def test_hit_is_reported_on_the_line_where_the_sentence_starts(ste):
    text = "Short.\n\n" + " ".join(["word"] * 13) + "\n" + " ".join(["word"] * 13) + ".\n"
    hits = _hits(text, ste, "sentence_length")
    assert [h.line for h in hits] == [3]


# ---- contractions (fail)

@pytest.mark.parametrize("text", ["We don't stop.", "Look, it's here.", "Then you're done."])
def test_contractions_fail(ste, text):
    hits = _hits(text + "\n", ste, "contractions")
    assert len(hits) == 1 and hits[0].severity == "fail"


def test_possessive_is_not_a_contraction(ste):
    assert _hits("Open the user's file.\n", ste, "contractions") == []


def test_typographic_contraction_fails(ste):
    assert len(_hits("We don’t stop.\n", ste, "contractions")) == 1


# ---- one_instruction (fail)

def test_two_instruction_sentences_in_one_step_fail(ste):
    hits = _hits("1. Open the file. Run the tests.\n", ste, "one_instruction")
    assert len(hits) == 1 and hits[0].severity == "fail"


def test_and_joined_second_instruction_fails(ste):
    assert len(_hits("1. Open the file and run the tests.\n", ste, "one_instruction")) == 1
    assert len(_hits("1. Open the file, then run the tests.\n", ste, "one_instruction")) == 1


def test_descriptive_second_sentence_passes(ste):
    assert _hits("1. Run the tests. This lets you keep working.\n", ste, "one_instruction") == []


def test_two_instructions_outside_a_step_pass(ste):
    assert _hits("Open the file. Run the tests.\n", ste, "one_instruction") == []


# ---- passive_in_steps (warn)

def test_passive_in_a_step_warns(ste):
    hits = _hits("1. The file is deleted.\n", ste, "passive_in_steps")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_passive_outside_a_step_does_not_warn(ste):
    assert _hits("The file is deleted.\n", ste, "passive_in_steps") == []


# ---- ing_forms (warn)

def test_ing_form_warns(ste):
    hits = _hits("The job is running now.\n", ste, "ing_forms")
    assert len(hits) == 1 and hits[0].severity == "warn" and "running" in hits[0].message


def test_ing_stop_list_and_terms_pass(ste):
    text = "During the build, a string or a thing changes. Use the staging branch.\n"
    assert _hits(text, ste, "ing_forms", terms=["staging"]) == []


# ---- vocabulary (warn)

def test_vocabulary_word_warns_with_replacement(ste):
    hits = _hits("Ensure the cache is clean.\n", ste, "vocabulary")
    assert len(hits) == 1 and hits[0].severity == "warn"
    assert "make sure" in hits[0].message


def test_vocabulary_term_is_exempt(ste):
    assert _hits("Ensure the cache is clean.\n", ste, "vocabulary", terms=["ensure"]) == []


def test_vocabulary_never_matches_inside_code(ste):
    assert _hits("Run `ensure` now.\n", ste, "vocabulary") == []


# ---- paragraph_length (warn)

def test_paragraph_of_seven_sentences_warns(ste):
    hits = _hits(" ".join(["It is so."] * 7) + "\n", ste, "paragraph_length")
    assert len(hits) == 1 and hits[0].severity == "warn"


def test_paragraph_of_six_sentences_passes(ste):
    assert _hits(" ".join(["It is so."] * 6) + "\n", ste, "paragraph_length") == []


# ---- severities

def test_off_severity_drops_the_check(ste):
    assert _hits("We don't.\n", ste, "contractions", severities={"contractions": "off"}) == []


def test_severity_override_changes_the_hit(ste):
    hits = _hits("We don't.\n", ste, "contractions", severities={"contractions": "warn"})
    assert hits[0].severity == "warn"
