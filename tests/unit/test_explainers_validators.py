"""P1.T3 -- validate_explainers.py (config-driven, no dossier)."""
from validate_explainers import ARCHETYPE_SECTIONS, extract_h2, validate_post


def _fm(**over):
    fm = {"title": "T", "date": "2026-01-01", "draft": False, "weight": 2,
          "series": ["explainers"], "post_number": 1, "archetype": "feature-deep-dive",
          "tldr": "short"}
    fm.update(over)
    return fm


def _body(headings):
    """Build a minimal markdown body from an ordered list of level-2 headings."""
    return "\n\n".join(f"## {h}\n\n*filler.*" for h in headings)


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
    # YAML boolean True is a subclass of int — must be explicitly rejected
    assert any("post_number" in f for f in validate_post(_fm(post_number=True)))


# ---- archetype structural check (P1) ----

def test_all_six_archetypes_registered():
    assert set(ARCHETYPE_SECTIONS) == {
        "feature-deep-dive", "skill-presentation", "skill-comparison",
        "testing-pyramid", "deployment-strategy", "security-posture",
    }


def test_unknown_archetype_fails_without_body():
    # Frontmatter-only: a typo'd archetype is caught even with no body.
    fails = validate_post(_fm(archetype="feature-deepdive"))
    assert any("archetype" in f for f in fails)


def test_unknown_archetype_fails_with_body():
    fails = validate_post(_fm(archetype="bogus"), body=_body(["Overview"]))
    assert any("archetype" in f for f in fails)


def test_each_archetype_canonical_body_passes():
    for arch, sections in ARCHETYPE_SECTIONS.items():
        fails = validate_post(_fm(archetype=arch), body=_body(sections))
        assert fails == [], f"{arch}: {fails}"


def test_missing_required_section_fails():
    sections = ARCHETYPE_SECTIONS["deployment-strategy"]
    partial = [s for s in sections if s != "Rollback path"]
    fails = validate_post(_fm(archetype="deployment-strategy"), body=_body(partial))
    assert any("missing section" in f.lower() and "Rollback path" in f for f in fails)


def test_reordered_sections_fail():
    sections = list(ARCHETYPE_SECTIONS["testing-pyramid"])
    swapped = sections[:]
    swapped[1], swapped[2] = swapped[2], swapped[1]  # swap two middle sections
    fails = validate_post(_fm(archetype="testing-pyramid"), body=_body(swapped))
    assert any("order" in f.lower() for f in fails)


def test_extra_section_allowed():
    sections = list(ARCHETYPE_SECTIONS["skill-presentation"]) + ["Further reading"]
    fails = validate_post(_fm(archetype="skill-presentation"), body=_body(sections))
    assert fails == [], fails


def test_heading_inside_fenced_code_not_counted():
    sections = ARCHETYPE_SECTIONS["security-posture"]
    body = _body(sections) + "\n\n```bash\n## Fake heading in a shell comment\necho hi\n```\n"
    fails = validate_post(_fm(archetype="security-posture"), body=body)
    assert fails == [], fails


def test_heading_inside_tilde_fence_not_counted():
    # A duplicate of a REQUIRED heading inside a ~~~ fence must not trip the
    # order check (regression for the tilde-fence hardening).
    sections = ARCHETYPE_SECTIONS["skill-presentation"]
    body = _body(sections) + "\n\n~~~markdown\n## Overview\nnot a real section\n~~~\n"
    fails = validate_post(_fm(archetype="skill-presentation"), body=body)
    assert fails == [], fails
    assert extract_h2("## A\n\n~~~\n## B\n~~~\n\n## C") == ["A", "C"]


def test_no_body_skips_structural_check():
    # A known archetype with no body: structural check skipped, still passes.
    assert validate_post(_fm(archetype="skill-comparison")) == []


def test_extract_h2_ignores_h3_and_fences():
    body = (
        "## Overview\n\n### a subheading\n\ntext\n\n"
        "```python\n## not a heading\n```\n\n## Try it yourself\n"
    )
    assert extract_h2(body) == ["Overview", "Try it yourself"]
