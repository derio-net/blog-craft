"""Phase 1 review findings p1-r1 .. p1-r13, each pinned by a failing input."""
import os

import pytest

import validate_writing_standard as vws


@pytest.fixture(scope="module")
def ste():
    return vws.load_standard("ste")


def _hits(text, std, check, **kw):
    return [h for h in vws.run_checks(text, std, **kw).hits if h.check == check]


def _split(text):
    return [s.text for u in vws.extract_prose(text) for s in vws.split_sentences(u)]


def _page(dirpath, name, body):
    path = os.path.join(str(dirpath), name)
    with open(path, "w") as f:
        f.write(body)
    return path


# p1-r1
def test_r1_and_then_joins_a_second_instruction(ste):
    assert len(_hits("1. Open the file, and then run the tests.\n", ste, "one_instruction")) == 1


# p1-r2
def test_r2_waiver_syntax_in_code_is_not_a_waiver(tmp_path, capsys):
    page = _page(tmp_path, "p.md",
                 "Write a waiver like `<!-- writing-standard: ignore contractions -->` here.\n\n"
                 "```html\n<!-- writing-standard: ignore contractions -->\n```\n")
    assert vws.main(["--default", "ste", page]) == 0
    assert "waiver_reason" not in capsys.readouterr().out


# p1-r3
def test_r3_stacked_waivers_both_cover_the_sentence(tmp_path, capsys):
    page = _page(tmp_path, "p.md",
                 "<!-- writing-standard: ignore contractions -- quoted -->\n"
                 "<!-- writing-standard: ignore vocabulary -- quoted -->\n"
                 "We don't ensure it.\n")
    assert vws.main(["--default", "ste", page]) == 0
    out = capsys.readouterr().out
    assert "contractions" not in out and "vocabulary" not in out


# p1-r4
@pytest.mark.parametrize("cfg_text", ["quality: [\n", "quality: 3\n",
                                      "quality:\n  writing_standard: 3\n", "- a list\n"])
def test_r4_bad_config_exits_2(tmp_path, capsys, cfg_text):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(cfg_text)
    page = _page(tmp_path, "p.md", "Fine.\n")
    assert vws.main(["--config", str(cfg), "--default", "ste", page]) == 2


def test_r4_glob_matching_a_directory_keeps_files_only(tmp_path, capsys):
    (tmp_path / "dir.md").mkdir()
    _page(tmp_path, "a.md", "Fine.\n")
    assert vws.main(["--default", "ste", str(tmp_path / "*.md")]) == 0
    assert "1 checked" in capsys.readouterr().out


def test_r4_non_utf8_page_exits_2(tmp_path, capsys):
    page = tmp_path / "p.md"
    page.write_bytes(b"Caf\xe9 is here.\n")
    assert vws.main(["--default", "ste", str(page)]) == 2
    assert "p.md" in capsys.readouterr().err


# p1-r5
def test_r5_bare_url_keeps_the_sentence_end():
    assert len(_split("See https://example.com/a. Then go.\n")) == 2


# p1-r6
def test_r6_step_continuation_paragraph_is_the_same_step(ste):
    assert len(_hits("1. Open it.\n\n   Run it.\n", ste, "one_instruction")) == 1


def test_r6_separate_steps_do_not_join(ste):
    assert _hits("1. Open it.\n2. Run it.\n", ste, "one_instruction") == []


# p1-r7
def test_r7_capitalised_word_mid_sentence_is_not_a_verb(ste):
    assert _hits("1. Install Python and Go.\n", ste, "one_instruction") == []


def test_r7_then_verb_sentence_is_a_second_instruction(ste):
    assert len(_hits("1. Run x. Then run y.\n", ste, "one_instruction")) == 1


# p1-r8
@pytest.mark.parametrize("text", ["1. The port is open.", "1. It is often fine.",
                                  "1. It is even.", "1. It is then.", "1. It was when.",
                                  "1. It is a token.", "1. It is token."])
def test_r8_passive_stop_list(ste, text):
    assert _hits(text + "\n", ste, "passive_in_steps") == []


def test_r8_one_adverb_before_the_participle(ste):
    hits = _hits("1. The file is often deleted.\n", ste, "passive_in_steps")
    assert len(hits) == 1 and "deleted" in hits[0].message


# p1-r9
def test_r9_i_am_contraction(ste):
    assert len(_hits("I'm here.\n", ste, "contractions")) == 1


# p1-r10
def test_r10_front_matter_waiver_naming_no_check_exits_2(tmp_path, capsys):
    page = _page(tmp_path, "p.md", "---\nwriting_standard_waive: {sentense_length: typo}\n---\nFine.\n")
    assert vws.main(["--default", "ste", page]) == 2
    assert "sentense_length" in capsys.readouterr().err


def test_r10_front_matter_waiver_of_a_sentence_level_check_fails(tmp_path, capsys):
    page = _page(tmp_path, "p.md",
                 "---\nwriting_standard_waive: {contractions: quotes}\n---\nWe don't.\n")
    assert vws.main(["--default", "ste", page]) == 1
    out = capsys.readouterr().out
    assert "waiver_reason" in out and "not a page-level check" in out
    assert "contractions: contraction" in out          # the hit itself is not waived


# p1-r11
def _std(tmp_path, check):
    (tmp_path / "s.md").write_text(f"# s\n\n```yaml\nname: s\ntitle: S\nchecks:\n  c: {check}\n```\n")
    return [str(tmp_path)]


@pytest.mark.parametrize("check", [
    '{kind: sentence_length, severity: fail, procedural_max: "20", descriptive_max: 25}',
    "{kind: sentence_length, severity: fail, procedural_max: true, descriptive_max: 25}",
    "{kind: passive, severity: warn, scope: everywhere}",
])
def test_r11_bad_parameter_values_are_refused(tmp_path, check):
    with pytest.raises(vws.StandardError) as e:
        vws.load_standard("s", dirs=_std(tmp_path, check))
    assert "'c'" in str(e.value)


# p1-r12
def test_r12_standards_load_once_per_run(tmp_path, capsys, monkeypatch):
    calls = []
    real = vws.load_standard
    monkeypatch.setattr(vws, "load_standard", lambda *a, **k: calls.append(a) or real(*a, **k))
    for n in range(3):
        _page(tmp_path, f"p{n}.md", "Fine.\n")
    assert vws.main(["--default", "ste", "--stats", str(tmp_path / "*.md")]) == 0
    assert len(calls) == len(vws.list_standards())


def test_r12_run_checks_returns_the_page():
    result = vws.run_checks("One. Two.\n", vws.load_standard("ste"))
    assert len(result.page.sentences) == 2 and result.hits == []


# p1-r13
@pytest.mark.parametrize("text,n", [("Use e.g. this", 3), ("Pi is 3.14 here", 4), ("It i.e. that", 3)])
def test_r13_dotted_tokens_are_one_word(text, n):
    assert vws.count_words(text) == n
