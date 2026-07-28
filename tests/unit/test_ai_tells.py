"""ai-tells catalog — load_lint_data() parses the fenced yaml block."""
import re

from validate_educational import load_lint_data


def test_returns_dict_with_expected_keys():
    data = load_lint_data()
    assert isinstance(data, dict)
    for key in (
        "vocabulary",
        "conclusion_openers",
        "patterns",
        "thresholds",
        "transfer_headings",
    ):
        assert key in data, f"missing key: {key}"


def test_vocabulary_list_lowercase():
    vocab = load_lint_data()["vocabulary"]
    assert isinstance(vocab, list)
    assert len(vocab) >= 12
    for word in vocab:
        assert isinstance(word, str)
        assert word == word.lower(), f"not lowercase: {word!r}"


def test_conclusion_openers_list_lowercase():
    openers = load_lint_data()["conclusion_openers"]
    assert isinstance(openers, list)
    assert len(openers) >= 4
    for opener in openers:
        assert isinstance(opener, str)
        assert opener == opener.lower(), f"not lowercase: {opener!r}"


def test_vocabulary_covers_common_inflections():
    """rev-minors (9): delve carries all conjugations; the other verbs must
    not slip through by inflecting ('embarked on a journey', 'boasting')."""
    vocab = set(load_lint_data()["vocabulary"])
    for word in (
        "embarks", "embarked", "embarking",
        "supercharges", "supercharged", "supercharging",
        "revolutionizes", "revolutionized", "revolutionizing",
        "boasting", "boasted",
    ):
        assert word in vocab, f"missing inflection: {word}"


def test_patterns_compile():
    patterns = load_lint_data()["patterns"]
    assert "negative_parallelism" in patterns
    assert "triad" in patterns
    for name, pattern in patterns.items():
        re.compile(pattern)  # raises re.error if invalid


def test_thresholds_numeric():
    thresholds = load_lint_data()["thresholds"]
    for key in (
        "em_dash_per_1000",
        "negative_parallelisms_per_1000",
        "triads_per_1000",
    ):
        assert key in thresholds, f"missing threshold: {key}"
        assert isinstance(thresholds[key], (int, float))


def test_transfer_headings_list():
    headings = load_lint_data()["transfer_headings"]
    assert isinstance(headings, list)
    assert len(headings) >= 2
    for heading in headings:
        assert isinstance(heading, str)
