"""P1.T3 -- validate_explainers.py (config-driven, no dossier)."""
from validate_explainers import validate_post


def _fm(**over):
    fm = {"title": "T", "date": "2026-01-01", "draft": False, "weight": 2,
          "series": ["explainers"], "post_number": 1, "archetype": "feature-deep-dive",
          "tldr": "short"}
    fm.update(over)
    return fm


def test_explainer_passes():
    assert validate_post(_fm(), weight_offset=1) == []


def test_explainer_weight_invariant_violation():
    assert any("weight invariant" in f for f in validate_post(_fm(weight=1), weight_offset=1))


def test_explainer_weight_offset_is_config_driven():
    # offset 0: weight must equal post_number
    assert validate_post(_fm(weight=1, post_number=1), weight_offset=0) == []
    assert any("weight invariant" in f for f in validate_post(_fm(weight=1, post_number=1), weight_offset=1))


def test_explainer_missing_field():
    fm = _fm()
    del fm["tldr"]
    assert any("tldr" in f for f in validate_post(fm))


def test_explainer_series_mismatch():
    assert any("series" in f for f in validate_post(_fm(series=["posts"])))


def test_explainer_bad_post_number():
    assert any("post_number" in f for f in validate_post(_fm(post_number=-1)))
    assert any("post_number" in f for f in validate_post(_fm(post_number="abc")))
