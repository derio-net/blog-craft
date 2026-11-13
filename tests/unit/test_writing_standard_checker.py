"""validate_writing_standard — prose extraction, splitting and the CLI."""
import pytest

import validate_writing_standard as vws


def test_main_runs():
    assert vws.main([]) == 0


# ------------------------------------------------------------------ extraction

def _texts(body):
    return [u.text for u in vws.extract_prose(body)]


def _all(body):
    return "\n".join(_texts(body))


def test_front_matter_is_excluded():
    body = "---\ntitle: Secret Title\nwriting_standard: ste\n---\n\nVisible prose here.\n"
    assert "Secret" not in _all(body)
    units = vws.extract_prose(body)
    assert units[0].text == "Visible prose here."
    assert units[0].line == 6


def test_fenced_code_is_excluded_including_a_four_backtick_fence():
    body = (
        "Before.\n\n"
        "````markdown\n```bash\nhidden command\n```\nstill hidden\n````\n\n"
        "After.\n"
    )
    text = _all(body)
    assert "hidden" not in text
    assert "Before." in text and "After." in text


def test_tables_and_html_comments_are_excluded():
    body = (
        "| col | other |\n|---|---|\n| tablecell | x |\n\n"
        "<!-- a comment\nspanning lines -->\n\n"
        "Real prose <!-- inline note --> stays.\n"
    )
    text = _all(body)
    assert "tablecell" not in text and "comment" not in text and "note" not in text
    assert "Real prose" in text and "stays." in text


def test_link_text_kept_url_dropped_heading_text_kept():
    body = "## The Heading\n\nRead [the guide](https://example.com/guide.html) now.\n"
    text = _all(body)
    assert "The Heading" in text and "#" not in text
    assert "the guide" in text and "example.com" not in text


def test_inline_code_becomes_one_placeholder_word():
    units = vws.extract_prose("Run `git commit --amend -m x` now.\n")
    assert units[0].text.count(vws.CODE_TOKEN) == 1
    assert "amend" not in units[0].text
    assert vws.count_words(units[0].text) == 3


def test_typographic_quotes_normalise():
    text = _all("It isn’t “quoted” here.\n")
    assert "isn't" in text and '"quoted"' in text


def test_ordered_list_items_are_steps():
    body = "Intro text.\n\n1. Open the file.\n2. Run the tests.\n\n- A bullet.\n"
    units = vws.extract_prose(body)
    steps = {u.text: u.in_step for u in units}
    assert steps == {"Intro text.": False, "Open the file.": True,
                     "Run the tests.": True, "A bullet.": False}


def test_continuation_lines_of_a_step_stay_in_the_step():
    body = "1. Open the file\n   in the editor.\n\n   Then save it.\n\nOutside.\n"
    units = vws.extract_prose(body)
    assert [(u.text, u.in_step) for u in units] == [
        ("Open the file\nin the editor.", True),
        ("Then save it.", True),
        ("Outside.", False),
    ]


# ------------------------------------------------------------------ splitting

def _split(text):
    out = []
    for u in vws.extract_prose(text):
        out.extend(s.text for s in vws.split_sentences(u))
    return out


def test_bold_question_and_its_answer_are_two_sentences():
    assert _split("**Why?** Because it works.\n") == ["**Why?**", "Because it works."]


def test_closing_quote_after_period_still_ends():
    assert len(_split("It ends here.” Next one starts.\n")) == 2


@pytest.mark.parametrize("abbr", ["e.g.", "i.e.", "etc.", "vs.", "cf.", "approx."])
def test_abbreviations_never_end_a_sentence(abbr):
    assert len(_split(f"Use {abbr} This form. Then go.\n")) == 2


def test_colon_before_a_fence_or_list_is_one_sentence():
    assert _split("Run this command:\n\n```\nls\n```\n") == ["Run this command:"]
    assert _split("Do these:\n- one\n") == ["Do these:", "one"]


def test_colon_inside_a_sentence_is_not_a_break():
    assert _split("The rule: keep it short.\n") == ["The rule: keep it short."]


def test_list_item_boundary_ends_a_sentence():
    assert _split("- first item without stop\n- second item\n") == [
        "first item without stop", "second item"]


def test_multi_line_sentence_reports_its_start_line():
    body = "Intro.\n\nOne sentence. A second sentence that\nruns over two lines.\n"
    sents = [s for u in vws.extract_prose(body) for s in vws.split_sentences(u)]
    assert [(s.text.split()[0], s.line) for s in sents] == [
        ("Intro.", 1), ("One", 3), ("A", 3)]
    body2 = "Intro.\n\nOne sentence\nthat wraps. Second\nstarts on line four.\n"
    sents = [s for u in vws.extract_prose(body2) for s in vws.split_sentences(u)]
    assert [s.line for s in sents] == [1, 3, 4]
