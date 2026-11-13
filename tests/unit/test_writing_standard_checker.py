"""validate_writing_standard — prose extraction, splitting and the CLI."""
import pytest

import validate_writing_standard as vws


def test_main_is_the_entry_point():
    assert callable(vws.main)


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


# ------------------------------------------------------------------ CLI

import os
import subprocess


def _page(dirpath, name, body, fm=None):
    path = os.path.join(str(dirpath), name)
    head = ""
    if fm is not None:
        head = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n"
    with open(path, "w") as f:
        f.write(head + body)
    return path


def _git_init(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_output_line_format_and_exit_1_on_fail(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "Intro.\n\nWe don't stop.\n")
    assert vws.main(["--default", "ste", page]) == 1
    out = capsys.readouterr().out
    assert f"FAIL: {page}:3: contractions: " in out
    assert "WRITING STANDARD FAILED" in out


def test_exit_0_with_only_warnings(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "Ensure the cache is clean.\n")
    assert vws.main(["--default", "ste", page]) == 0
    out = capsys.readouterr().out
    assert f"WARN: {page}:1: vocabulary: " in out
    assert "WRITING STANDARD OK: 1 checked, 0 skipped" in out


def test_exit_2_on_usage_errors(tmp_path, capsys):
    assert vws.main([]) == 2
    assert vws.main(["--default", "ste", str(tmp_path / "missing.md")]) == 2
    page = _page(tmp_path, "p.md", "Fine.\n")
    assert vws.main(["--default", "ste", "--severity", "nonsense", page]) == 2
    assert vws.main(["--default", "ste", "--preserve-from", "HEAD", page]) == 2


def test_globs_expand(tmp_path, capsys):
    _page(tmp_path, "a.md", "Fine.\n")
    _page(tmp_path, "b.md", "Fine too.\n")
    assert vws.main(["--default", "ste", str(tmp_path / "*.md")]) == 0
    assert "2 checked" in capsys.readouterr().out


# ---- severities

def test_cli_severity_qualified_and_bare(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "We don't stop.\n")
    assert vws.main(["--default", "ste", "--severity", "ste.contractions=warn", page]) == 0
    assert vws.main(["--default", "ste", "--severity", "contractions=off", page]) == 0
    assert "contractions" not in capsys.readouterr().out.split("WRITING")[-2]


def test_qualified_beats_bare(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "We don't stop.\n")
    args = ["--default", "ste", "--severity", "ste.contractions=fail",
            "--severity", "contractions=off", page]
    assert vws.main(args) == 1


def test_config_severities_and_cli_layering(tmp_path, capsys):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text("quality:\n  writing_standard:\n    severities:\n      contractions: warn\n")
    page = _page(tmp_path, "p.md", "We don't stop.\n")
    assert vws.main(["--config", str(cfg), "--default", "ste", page]) == 0
    assert vws.main(["--config", str(cfg), "--default", "ste",
                     "--severity", "contractions=fail", page]) == 1


def test_unknown_standard_or_check_in_an_override_exits_2(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "Fine.\n")
    assert vws.main(["--default", "ste", "--severity", "klingon.contractions=warn", page]) == 2
    assert vws.main(["--default", "ste", "--severity", "ste.telepathy=warn", page]) == 2
    assert vws.main(["--default", "ste", "--severity", "telepathy=warn", page]) == 2
    assert vws.main(["--default", "ste", "--severity", "contractions=loud", page]) == 2
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text("quality:\n  writing_standard:\n    severities:\n      ste.telepathy: warn\n")
    assert vws.main(["--config", str(cfg), "--default", "ste", page]) == 2


# ---- waivers

def test_waiver_with_reason_suppresses_the_next_hit(tmp_path, capsys):
    for delim in ("--", "—"):
        page = _page(tmp_path, "p.md",
                     f"<!-- writing-standard: ignore contractions {delim} quoted speech -->\n"
                     "We don't stop.\n")
        assert vws.main(["--default", "ste", page]) == 0
        assert "contractions" not in capsys.readouterr().out


def test_waiver_suppresses_only_one_hit(tmp_path, capsys):
    page = _page(tmp_path, "p.md",
                 "<!-- writing-standard: ignore contractions -- quoted -->\n"
                 "We don't stop.\n\nWe can't stop.\n")
    assert vws.main(["--default", "ste", page]) == 1
    out = capsys.readouterr().out
    assert f"{page}:4: contractions" in out and f"{page}:2:" not in out


def test_waiver_without_reason_fails(tmp_path, capsys):
    page = _page(tmp_path, "p.md",
                 "<!-- writing-standard: ignore contractions -->\nWe don't stop.\n")
    assert vws.main(["--default", "ste", page]) == 1
    assert f"FAIL: {page}:1: waiver_reason: " in capsys.readouterr().out


def test_front_matter_waiver_is_accepted(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "Fine.\n",
                 fm={"writing_standard_waive": "{average_sentence_length: long quotes}"})
    assert vws.main(["--default", "ste", page]) == 0
    bad = _page(tmp_path, "q.md", "Fine.\n",
                fm={"writing_standard_waive": "{average_sentence_length: ''}"})
    assert vws.main(["--default", "ste", bad]) == 1
    assert "waiver_reason" in capsys.readouterr().out


# ---- terms

def test_terms_from_every_source(tmp_path, capsys, monkeypatch):
    _git_init(tmp_path)
    (tmp_path / ".writing-standard-terms").write_text("# product terms\nstaging\n")
    sub = tmp_path / "docs"
    sub.mkdir()
    page = _page(sub, "p.md", "Use staging. Ensure it. Create it. Allow it. Provide it.\n")
    tf = tmp_path / "extra-terms.txt"
    tf.write_text("create\n")
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text("quality:\n  writing_standard:\n    terms: [ensure]\n")
    elsewhere = tmp_path.parent / (tmp_path.name + "-cwd")
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert vws.main(["--config", str(cfg), "--default", "ste", "--terms", str(tf),
                     "--term", "allow", page]) == 0
    out = capsys.readouterr().out
    assert "staging" not in out and "'Ensure'" not in out
    assert "'Create'" not in out and "'Allow'" not in out
    assert "'Provide'" in out


# ---- stats and portability

def test_stats_line(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "One two three. " + " ".join(["W"] * 30) + ".\n")
    vws.main(["--default", "ste", "--stats", page])
    out = capsys.readouterr().out
    assert f"STATS: {page}: ste: sentences=2 avg=16.5 max=30 over_limit=1" in out


def test_runs_with_no_config_against_a_page_in_another_repo(tmp_path, capsys, monkeypatch):
    other = tmp_path / "other-repo"
    other.mkdir()
    _git_init(other)
    page = _page(other, "p.md", "Fine.\n")
    monkeypatch.chdir(tmp_path)
    assert vws.main(["--default", "ste", page]) == 0


def test_script_runs_as_a_subprocess(tmp_path):
    import sys
    page = _page(tmp_path, "p.md", "We don't stop.\n")
    script = os.path.join(os.path.dirname(vws.__file__), "validate_writing_standard.py")
    r = subprocess.run([sys.executable, script, "--default", "ste", page],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 1 and "FAIL:" in r.stdout
