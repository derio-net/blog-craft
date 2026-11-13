"""The writing-standard registry: reference files with one check-instance yaml block."""
import os
import re

import pytest

import validate_writing_standard as vws

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STANDARDS = os.path.join(ROOT, "skills", "apply-writing-standard", "standards")


def _write_standard(dirpath, name, block, prose="A fixture standard.\n"):
    path = os.path.join(str(dirpath), f"{name}.md")
    with open(path, "w") as f:
        f.write(f"# {name}\n\n{prose}\n```yaml\n{block}```\n")
    return path


def test_load_ste_has_name_title_checks_terms():
    std = vws.load_standard("ste")
    assert std.name == "ste"
    assert std.title.startswith("STE writing rules")
    assert isinstance(std.terms, list)
    assert set(std.checks) >= {
        "sentence_length", "contractions", "one_instruction", "passive_in_steps",
        "ing_forms", "vocabulary", "paragraph_length",
    }
    spec = std.checks["sentence_length"]
    assert isinstance(spec, vws.CheckSpec)
    assert spec.kind == "sentence_length"
    assert spec.severity == "fail"
    assert spec.params == {"procedural_max": 20, "descriptive_max": 25}


def test_ste_severities_match_spec():
    std = vws.load_standard("ste")
    sev = {cid: c.severity for cid, c in std.checks.items()}
    assert sev == {
        "sentence_length": "fail", "contractions": "fail", "one_instruction": "fail",
        "passive_in_steps": "warn", "ing_forms": "warn", "vocabulary": "warn",
        "paragraph_length": "warn",
    }


def test_ste_vocabulary_has_at_least_25_words():
    words = vws.load_standard("ste").checks["vocabulary"].params["words"]
    assert len(words) >= 25
    for w in ("ensure", "utilize", "commence", "terminate", "assist"):
        assert w in words


def test_first_yaml_block_is_the_data(tmp_path):
    block = "name: two\ntitle: Two\nchecks:\n  c: {kind: contractions, severity: warn}\nterms: [x]\n"
    path = os.path.join(str(tmp_path), "two.md")
    with open(path, "w") as f:
        f.write(f"# two\n\n```yaml\n{block}```\n\nLater example:\n\n```yaml\nname: other\n```\n")
    std = vws.load_standard("two", dirs=[str(tmp_path)])
    assert std.name == "two"
    assert std.terms == ["x"]


def test_unknown_kind_names_check_and_kind(tmp_path):
    _write_standard(tmp_path, "bad", "name: bad\ntitle: Bad\nchecks:\n  mine: {kind: telepathy, severity: warn}\n")
    with pytest.raises(vws.StandardError) as e:
        vws.load_standard("bad", dirs=[str(tmp_path)])
    assert "mine" in str(e.value) and "telepathy" in str(e.value)


def test_unexpected_parameter_is_an_error(tmp_path):
    _write_standard(tmp_path, "bad", "name: bad\ntitle: Bad\nchecks:\n  c: {kind: contractions, severity: warn, limit: 3}\n")
    with pytest.raises(vws.StandardError) as e:
        vws.load_standard("bad", dirs=[str(tmp_path)])
    assert "limit" in str(e.value) and "c" in str(e.value)


def test_missing_required_parameter_is_an_error(tmp_path):
    _write_standard(tmp_path, "bad", "name: bad\ntitle: Bad\nchecks:\n  len: {kind: sentence_length, severity: fail, procedural_max: 20}\n")
    with pytest.raises(vws.StandardError) as e:
        vws.load_standard("bad", dirs=[str(tmp_path)])
    assert "descriptive_max" in str(e.value)


def test_bad_severity_is_an_error(tmp_path):
    _write_standard(tmp_path, "bad", "name: bad\ntitle: Bad\nchecks:\n  c: {kind: contractions, severity: loud}\n")
    with pytest.raises(vws.StandardError) as e:
        vws.load_standard("bad", dirs=[str(tmp_path)])
    assert "loud" in str(e.value)


def test_unknown_standard_lists_available(tmp_path):
    _write_standard(tmp_path, "alpha", "name: alpha\ntitle: A\nchecks: {}\n")
    with pytest.raises(vws.StandardError) as e:
        vws.load_standard("nope", dirs=[str(tmp_path)])
    assert "nope" in str(e.value) and "alpha" in str(e.value)


def test_list_standards_ignores_readme(tmp_path):
    _write_standard(tmp_path, "alpha", "name: alpha\ntitle: A\nchecks: {}\n")
    _write_standard(tmp_path, "README", "name: example\ntitle: E\nchecks: {}\n")
    assert vws.list_standards(dirs=[str(tmp_path)]) == ["alpha"]


def test_two_instances_of_one_kind_are_both_kept(tmp_path):
    block = (
        "name: twice\ntitle: Twice\nchecks:\n"
        "  must_not_shall: {kind: replacements, severity: fail, words: {shall: must}}\n"
        "  simple_words: {kind: replacements, severity: warn, words: {utilize: use}}\n"
    )
    _write_standard(tmp_path, "twice", block)
    std = vws.load_standard("twice", dirs=[str(tmp_path)])
    assert std.checks["must_not_shall"].kind == "replacements"
    assert std.checks["simple_words"].kind == "replacements"
    assert std.checks["must_not_shall"].params["words"] == {"shall": "must"}


def test_all_twelve_kinds_are_declared():
    assert set(vws.KINDS) == {
        "sentence_length", "average_sentence_length", "contractions", "one_instruction",
        "replacements", "phrases", "passive", "ing_forms", "paragraph_length",
        "loose_sentences", "nominalizations", "abbreviations",
    }


def test_ste_names_its_source_and_never_claims_conformance():
    with open(os.path.join(STANDARDS, "ste.md")) as f:
        text = f.read()
    assert "based on ASD-STE100" in text
    assert not re.search(r"conformant|compliant", text, re.IGNORECASE)


# ------------------------------------------------------------------ phase 2: three standards

def _read(name):
    with open(os.path.join(STANDARDS, f"{name}.md")) as f:
        return f.read()


def test_three_standards_ship():
    assert vws.list_standards() == ["elements-of-style", "plain-language", "ste"]


def test_elements_of_style_names_strunk_1918():
    text = _read("elements-of-style")
    assert "Strunk" in text and "1918" in text
    assert vws.load_standard("elements-of-style").title.startswith("Elements of Style rules")


def test_plain_language_names_the_guidelines():
    text = _read("plain-language")
    assert "Plain Language Guidelines" in text
    assert vws.load_standard("plain-language").title.startswith("Plain language rules")


@pytest.mark.parametrize("name", ["elements-of-style", "plain-language", "ste", "README"])
def test_no_standard_claims_conformance(name):
    assert not re.search(r"conformant|compliant", _read(name), re.IGNORECASE)


def _readme_kind_table():
    """kind -> the parameter names its README table row lists (the
    backticked names outside parentheses in the Parameters column)."""
    table = {}
    for line in _read("README").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"`\w+`", cells[0]) and cells[1] in ("exact", "heuristic"):
            params = re.sub(r"\([^)]*\)", "", cells[2])
            table[cells[0].strip("`")] = set(re.findall(r"`(\w+)`", params))
    return table


def test_readme_kind_table_matches_kinds():
    expected = {kind: set(req) | set(opt) for kind, (req, opt) in vws.KINDS.items()}
    assert _readme_kind_table() == expected


def test_readme_and_plain_language_say_all_capitals():
    for name in ("README", "plain-language"):
        assert "capitalized" not in _read(name)
    assert "all-capitals" in _read("README") and "all-capitals" in _read("plain-language")


def test_readme_names_long_sentence_as_an_exception():
    assert "long_sentence" in _read("README")


def test_a_fourth_standard_of_existing_kinds_needs_no_code(tmp_path):
    block = (
        "name: house\ntitle: House rules\nchecks:\n"
        "  avg: {kind: average_sentence_length, severity: fail, max: 15}\n"
        "  filler: {kind: phrases, severity: warn, phrases: {basically: (omit)}}\n"
        "  abbr: {kind: abbreviations, severity: warn}\n"
        "  loose: {kind: loose_sentences, severity: warn, run: 2}\n"
        "  nominal: {kind: nominalizations, severity: warn}\n"
        "terms: []\n"
    )
    _write_standard(tmp_path, "house", block)
    dirs = [STANDARDS, str(tmp_path)]
    assert vws.list_standards(dirs=dirs) == ["elements-of-style", "house", "plain-language", "ste"]
    hits = vws.run_checks("It is basically fine.\n", vws.load_standard("house", dirs=dirs)).hits
    assert [h.check for h in hits] == ["filler"]


def _after_examples(name):
    """The text of every `- After:` example in a standard's prose, as a page."""
    examples, current = [], None
    for line in _read(name).split("```yaml", 1)[0].splitlines():
        if line.startswith("- After:"):
            current = [line[len("- After:"):].strip()]
            examples.append(current)
        elif current is not None and line.startswith("  ") and line.strip():
            current.append(line.strip())
        else:
            current = None
    return "\n\n".join("\n".join(x for x in e if x) for e in examples) + "\n"


@pytest.mark.parametrize("name", ["elements-of-style", "plain-language", "ste"])
def test_each_standards_after_examples_pass_its_own_checker(name):
    page = _after_examples(name)
    assert page.strip()
    hits = vws.run_checks(page, vws.load_standard(name)).hits
    assert hits == []
