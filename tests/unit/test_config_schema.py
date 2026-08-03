"""P1.T1 — .blog-craft.yaml v2 schema validator.

Invariants under test (spec §4 / §4.1):
- version == 2 and the required top-level blocks are present;
- image.composition_order is a list and image.layers a map;
- every composition_order name (except the reserved `scene`) resolves in image.layers;
- `scene` is reserved: it must appear in composition_order and must NOT be a layers key.
"""
import copy
import os

import yaml

from validate_config import validate_config  # tools/ on sys.path via conftest

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


def _valid():
    with open(os.path.join(FIXTURES, "valid-v2.blog-craft.yaml")) as f:
        return yaml.safe_load(f)


def test_a_valid_config_passes():
    assert validate_config(_valid()) == []


def test_b_missing_required_key_named():
    cfg = _valid()
    del cfg["image"]["composition_order"]
    errs = validate_config(cfg)
    assert errs, "expected an error for missing image.composition_order"
    assert any("composition_order" in e for e in errs)


def test_quality_mermaid_syntax_must_be_bool():
    cfg = _valid()
    cfg["quality"] = {"mermaid_syntax": "yes"}
    assert any("mermaid_syntax" in e for e in validate_config(cfg))


def test_quality_mermaid_syntax_bool_ok():
    cfg = _valid()
    cfg["quality"] = {"mermaid_syntax": False}
    assert validate_config(cfg) == []


def test_c_composition_order_names_unknown_layer():
    cfg = _valid()
    cfg["image"]["composition_order"] = ["base_style", "nope_layer", "scene"]
    errs = validate_config(cfg)
    assert any("nope_layer" in e for e in errs)


def test_d_scene_is_reserved_not_a_layer():
    cfg = _valid()
    cfg["image"]["layers"]["scene"] = "should not be here"
    errs = validate_config(cfg)
    assert any("scene" in e.lower() for e in errs)


def test_versions_2_through_5_accepted():
    for v in (2, 3, 4, 5):
        cfg = _valid()
        cfg["version"] = v
        assert validate_config(cfg) == [], f"version {v} should be valid"


def test_out_of_range_versions_rejected():
    # 7 became a LADDER RUNG in the stickers plan (006_to_007), so the first
    # out-of-range version above the head is now 8.
    for v in (1, 8, "2"):
        cfg = _valid()
        cfg["version"] = v
        assert validate_config(cfg), f"version {v!r} should be invalid"


# --- v4: site_dir, _select, image.character_sheet (spec D1/D3/D8) ---

def test_site_dir_relative_ok():
    cfg = _valid()
    cfg["site_dir"] = "blog"
    assert validate_config(cfg) == []


def test_site_dir_absolute_or_nonstring_rejected():
    for bad in ("/abs/path", 3, ["blog"]):
        cfg = _valid()
        cfg["site_dir"] = bad
        assert any("site_dir" in e for e in validate_config(cfg)), bad


def test_scalar_layer_named_torso_is_valid_in_v4():
    # the engine hardcodes no layer names; a scalar torso is fine now
    cfg = _valid()
    cfg["image"]["composition_order"] = ["torso", "scene"]
    cfg["image"]["layers"] = {"torso": "always this torso"}
    assert validate_config(cfg) == []


def test_select_shape_ok():
    cfg = _valid()
    cfg["image"]["composition_order"] = ["torso", "scene"]
    cfg["image"]["layers"] = {"torso": {"_select": [["torso", "series"], "torso_variant"],
                                        "building": ["t0"]}}
    assert validate_config(cfg) == []


def test_select_bad_shapes_rejected():
    for bad in ("torso_variant", [3], [{"f": 1}], [["a", 2]]):
        cfg = _valid()
        cfg["image"]["composition_order"] = ["torso", "scene"]
        cfg["image"]["layers"] = {"torso": {"_select": bad, "building": ["t0"]}}
        assert any("_select" in e for e in validate_config(cfg)), bad


def test_character_sheet_layers_shape():
    cfg = _valid()
    cfg["image"]["character_sheet"] = {"layers": ["persona", "visual_constants"]}
    assert validate_config(cfg) == []
    cfg["image"]["character_sheet"] = {"layers": "persona"}
    assert any("character_sheet" in e for e in validate_config(cfg))
    cfg["image"]["character_sheet"] = {"layers": [1]}
    assert any("character_sheet" in e for e in validate_config(cfg))


# --- series_index block (optional; style cards|table|none, optional layers registry) ---

def test_series_index_absent_is_valid():
    cfg = _valid()
    cfg.pop("series_index", None)
    assert validate_config(cfg) == []


def test_series_index_valid_styles_pass():
    for style in ("cards", "table", "none"):
        cfg = _valid()
        cfg["series_index"] = {"style": style}
        assert validate_config(cfg) == [], f"style {style!r} should be valid"


def test_series_index_invalid_style_rejected():
    cfg = _valid()
    cfg["series_index"] = {"style": "carousel"}
    errs = validate_config(cfg)
    assert any("series_index" in e and "style" in e for e in errs), errs


def test_series_index_layers_shape():
    cfg = _valid()
    cfg["series_index"] = {"style": "cards",
                           "layers": [{"code": "hw", "name": "Hardware"},
                                      {"code": "net", "name": "Networking"}]}
    assert validate_config(cfg) == []
    # malformed: an entry missing code/name
    cfg["series_index"]["layers"] = [{"code": "hw"}]
    assert any("layers" in e for e in validate_config(cfg))
    # malformed: not a list
    cfg["series_index"]["layers"] = {"hw": "Hardware"}
    assert any("layers" in e for e in validate_config(cfg))


# --- image.optimize block (optional; webp pipeline knob) ---

def test_image_optimize_absent_is_valid():
    cfg = _valid()
    cfg["image"].pop("optimize", None)
    assert validate_config(cfg) == []


def test_image_optimize_valid_passes():
    cfg = _valid()
    cfg["image"]["optimize"] = {"enabled": True, "format": "webp", "quality": 82,
                                "max_width": 1600, "banner_max_width": 2560}
    assert validate_config(cfg) == []


def test_image_optimize_not_a_mapping_rejected():
    cfg = _valid()
    cfg["image"]["optimize"] = ["webp"]
    assert any("optimize" in e for e in validate_config(cfg))


def test_image_optimize_bad_format_rejected():
    cfg = _valid()
    cfg["image"]["optimize"] = {"enabled": True, "format": "avif"}
    assert any("optimize" in e and "format" in e for e in validate_config(cfg))


def test_image_optimize_bad_enabled_rejected():
    cfg = _valid()
    cfg["image"]["optimize"] = {"enabled": "yes"}
    assert any("optimize" in e and "enabled" in e for e in validate_config(cfg))


def test_image_optimize_quality_out_of_range_rejected():
    cfg = _valid()
    # bool is guarded before the int check (isinstance(True, int) is True)
    for bad in (0, 101, "hi", 82.5, True, False):
        cfg["image"]["optimize"] = {"quality": bad}
        assert any("optimize" in e and "quality" in e for e in validate_config(cfg)), bad


def test_image_optimize_widths_must_be_positive_ints():
    cfg = _valid()
    for key in ("max_width", "banner_max_width"):
        for bad in (0, "wide", True, False):
            cfg["image"]["optimize"] = {key: bad}
            assert any("optimize" in e and key in e for e in validate_config(cfg)), (key, bad)


# ── v5: composition_orders (named), bracket tokens ────────────────────────────

def _v5(cfg):
    cfg["version"] = 5
    img = cfg["image"]
    img["composition_orders"] = {"hero": img.pop("composition_order")}
    return cfg


def test_v5_named_orders_accepted():
    assert validate_config(_v5(_valid())) == []


def test_v5_orders_must_be_map_of_lists():
    cfg = _v5(_valid())
    cfg["image"]["composition_orders"] = {"hero": "not-a-list"}
    assert any("composition_orders" in e for e in validate_config(cfg))
    cfg["image"]["composition_orders"] = ["hero"]
    assert any("composition_orders" in e for e in validate_config(cfg))


def test_v5_every_order_needs_scene():
    cfg = _v5(_valid())
    cfg["image"]["composition_orders"]["scenery"] = ["base_style"]
    errs = validate_config(cfg)
    assert any("scenery" in e and "scene" in e for e in errs)


def test_v5_bracket_token_resolves_against_layers():
    cfg = _v5(_valid())
    cfg["image"]["layers"]["reference_guidance"] = {"anchor": "A"}
    cfg["image"]["composition_orders"]["hero"] = [
        "base_style", "reference_guidance[anchor]", "scene"]
    assert validate_config(cfg) == []
    cfg["image"]["composition_orders"]["hero"] = ["nope_layer[anchor]", "scene"]
    assert any("nope_layer" in e for e in validate_config(cfg))


def test_v4_single_order_still_accepted_at_v5():
    cfg = _valid()
    cfg["version"] = 5
    assert validate_config(cfg) == []


def test_missing_both_order_forms_flagged():
    cfg = _valid()
    del cfg["image"]["composition_order"]
    assert any("composition_order" in e for e in validate_config(cfg))


# --- features.glossary (abbreviation glossary, docs/CONFIG.md §9) -------------
# The `features` block was unvalidated until now; these are the first assertions
# over it. Only the glossary sub-block is checked — a typo'd `enable: true` would
# otherwise silently disable the whole feature with no signal.

def test_features_glossary_valid_block_passes():
    cfg = _valid()
    cfg["features"] = {"glossary": {"enabled": True, "first_occurrence_only": True}}
    assert validate_config(cfg) == []


def test_features_glossary_must_be_a_mapping():
    cfg = _valid()
    cfg["features"] = {"glossary": True}
    assert any("features.glossary must be a mapping" in e for e in validate_config(cfg))


def test_features_glossary_enabled_must_be_bool():
    cfg = _valid()
    cfg["features"] = {"glossary": {"enabled": "yes"}}
    assert any("features.glossary.enabled must be a boolean" in e
               for e in validate_config(cfg))


def test_features_glossary_first_occurrence_only_must_be_bool():
    cfg = _valid()
    cfg["features"] = {"glossary": {"first_occurrence_only": 1}}
    assert any("features.glossary.first_occurrence_only must be a boolean" in e
               for e in validate_config(cfg))


def test_no_features_block_is_never_an_error():
    cfg = _valid()
    cfg.pop("features", None)
    assert validate_config(cfg) == []


def test_other_feature_keys_stay_unvalidated():
    cfg = _valid()
    cfg["features"] = {"read_tracker": "not-a-bool"}
    assert validate_config(cfg) == []


# --- quality.lint (humanize lint layer; severities fail|warn|off, numeric ----
# thresholds). Unknown severity/threshold KEYS stay unvalidated — forward-
# compatible with new checks; only the SHAPE is enforced.

def test_quality_lint_valid_block_passes():
    cfg = _valid()
    cfg["quality"] = {"lint": {"enabled": True}}
    assert validate_config(cfg) == []


def test_quality_lint_must_be_a_mapping():
    cfg = _valid()
    cfg["quality"] = {"lint": True}
    assert any("quality.lint must be a mapping" in e for e in validate_config(cfg))


def test_quality_lint_enabled_must_be_bool():
    cfg = _valid()
    cfg["quality"] = {"lint": {"enabled": "yes"}}
    assert any("quality.lint.enabled must be a boolean" in e
               for e in validate_config(cfg))


def test_quality_lint_bad_severity_value_rejected():
    cfg = _valid()
    cfg["quality"] = {"lint": {"severities": {"vocabulary": "hard"}}}
    assert any("fail | warn | off" in e for e in validate_config(cfg))


def test_quality_lint_valid_severities_pass():
    cfg = _valid()
    cfg["quality"] = {"lint": {"severities": {"vocabulary": "warn", "em_dash": "off"}}}
    assert validate_config(cfg) == []


def test_quality_lint_threshold_must_be_a_number():
    cfg = _valid()
    cfg["quality"] = {"lint": {"thresholds": {"em_dash_per_1000": "many"}}}
    assert any("must be a number" in e for e in validate_config(cfg))


def test_no_quality_lint_block_is_never_an_error():
    cfg = _valid()
    cfg.pop("quality", None)
    assert validate_config(cfg) == []


def test_quality_lint_unknown_keys_allowed():
    cfg = _valid()
    cfg["quality"] = {"lint": {"severities": {"future_check": "warn"},
                               "thresholds": {"future_per_1000": 4.5}}}
    assert validate_config(cfg) == []


# --- v6: features.mermaid_view + quality.mermaid_max_width (mermaid readability) ---

def test_version_6_accepted():
    cfg = _valid()
    cfg["version"] = 6
    assert validate_config(cfg) == []


def test_version_5_still_valid_at_v6_ladder():
    cfg = _valid()
    cfg["version"] = 5
    assert validate_config(cfg) == []


def test_features_mermaid_view_must_be_bool():
    cfg = _valid()
    cfg["features"] = {"mermaid_view": "yes"}
    assert any("features.mermaid_view must be a boolean" in e for e in validate_config(cfg))


def test_features_mermaid_view_bool_or_absent_ok():
    cfg = _valid()
    cfg["features"] = {"mermaid_view": True}
    assert validate_config(cfg) == []
    cfg["features"] = {"mermaid_view": False}
    assert validate_config(cfg) == []
    cfg.pop("features", None)
    assert validate_config(cfg) == []


def test_quality_mermaid_max_width_valid_values():
    cfg = _valid()
    cfg["quality"] = {"mermaid_max_width": 1400}
    assert validate_config(cfg) == []
    cfg["quality"] = {"mermaid_max_width": 0}
    assert validate_config(cfg) == []


def test_quality_mermaid_max_width_rejects_string():
    cfg = _valid()
    cfg["quality"] = {"mermaid_max_width": "1400"}
    errs = validate_config(cfg)
    assert any("mermaid_max_width" in e and "non-negative number" in e for e in errs)


def test_quality_mermaid_max_width_rejects_negative():
    cfg = _valid()
    cfg["quality"] = {"mermaid_max_width": -5}
    errs = validate_config(cfg)
    assert any("mermaid_max_width" in e and "non-negative number" in e for e in errs)


def test_quality_mermaid_max_width_rejects_bool():
    cfg = _valid()
    cfg["quality"] = {"mermaid_max_width": True}
    errs = validate_config(cfg)
    assert any("mermaid_max_width" in e and "non-negative number" in e for e in errs)


# --- stickers: image.layers.<name>._template (the `str.format` frame) ---------
# Two reasons a frame is rejected, deliberately NOT the same reason:
#   1. it would misbehave mid-run — no `{}` drops the value, two `{}` raise
#      IndexError, an unmatched brace raises ValueError — invisible until
#      IMAGE-GENERATION time with a paid API call in flight, so the validator is
#      the only place that failure is cheap;
#   2. it is legal `str.format` forbidden by POLICY: `{0}`, `{:>10}` and the
#      escapes `{{`/`}}` format fine with one positional arg, but the rule is "no
#      literal brace anywhere", so a frame has one obvious spelling.
# `test_legal_but_policy_rejected_braces` pins that difference explicitly, so
# nobody "fixes" the strict half believing it is a bug.

def _tpl_cfg(tmpl):
    cfg = _valid()
    cfg["image"]["composition_order"] = ["mood", "scene"]
    cfg["image"]["layers"] = {"mood": {"_template": tmpl, "focused": "FOC"}}
    return cfg


def test_template_must_be_a_string():
    for bad in (7, True, ["Frank's expression: {}."], {"f": "{}"}, None):
        errs = validate_config(_tpl_cfg(bad))
        assert any("mood._template" in e for e in errs), bad


def test_template_without_placeholder_rejected():
    # it would silently drop the resolved value from the prompt
    errs = validate_config(_tpl_cfg("Frank's expression."))
    assert any("mood._template" in e and "{}" in e for e in errs)


def test_template_with_two_placeholders_rejected():
    # str.format would raise IndexError mid-run (one positional arg supplied)
    errs = validate_config(_tpl_cfg("Frank's {} expression: {}."))
    assert any("mood._template" in e and "{}" in e for e in errs)


def test_template_with_stray_braces_rejected():
    # an UNMATCHED brace: str.format would raise ValueError mid-run
    for bad in ("Frank's {expression: {}.", "Frank's expression: {}.}"):
        errs = validate_config(_tpl_cfg(bad))
        assert any("mood._template" in e for e in errs), bad


def test_legal_but_policy_rejected_braces():
    """These three format PERFECTLY WELL with one positional arg — they are
    rejected by policy (no literal brace anywhere), not because they would
    raise. Asserted both ways round so the reason cannot be misread later."""
    for legal in ("{{}} literal {}", "Frank's expression: {0}.", "|{:>10}|"):
        legal.format("VALUE")                                    # no exception
        errs = validate_config(_tpl_cfg(legal))
        assert any("mood._template" in e for e in errs), legal


def test_template_error_shows_the_offending_value():
    errs = validate_config(_tpl_cfg("no placeholder here"))
    assert any("no placeholder here" in e for e in errs)


def test_template_with_exactly_one_placeholder_accepted():
    assert validate_config(_tpl_cfg("Frank's expression: {}.")) == []
    assert validate_config(_tpl_cfg("{}")) == []


def test_template_on_a_select_walk_layer_also_validated():
    cfg = _valid()
    cfg["image"]["composition_order"] = ["mood", "scene"]
    cfg["image"]["layers"] = {
        "mood": {"_select": ["mood"], "_template": "no placeholder", "focused": "FOC"}
    }
    assert any("mood._template" in e for e in validate_config(cfg))


# --- a BRACKET token never gets the frame, so the combination is rejected -----
# `_template` is applied on the two resolution paths (`_resolve_modifier`,
# `_resolve_selector_walk`) but deliberately NOT on `resolve_token`'s `name[sub]`
# branch (journal p1-template-two-paths-only). `X` and `X[y]` look identical in
# config and behave differently, and the failure mode is a prose section quietly
# losing its frame — no exception, a prompt that still reads perfectly well. So
# the validator refuses the combination rather than let it compose.

TPL = "Frank's expression: {}."


def test_bracket_token_naming_a_template_layer_rejected():
    cfg = _valid()
    cfg["image"]["composition_order"] = ["mood[focused]", "scene"]
    cfg["image"]["layers"] = {"mood": {"_template": TPL, "focused": "FOC"}}
    errs = validate_config(cfg)
    assert any("mood[focused]" in e and "_template" in e for e in errs), errs


def test_bracket_token_on_a_template_layer_rejected_in_a_named_order():
    cfg = _valid()
    del cfg["image"]["composition_order"]
    cfg["image"]["composition_orders"] = {"hero": ["mood[focused]", "scene"],
                                          "sticker": ["mood", "scene"]}
    cfg["image"]["layers"] = {"mood": {"_template": TPL, "focused": "FOC"}}
    errs = validate_config(cfg)
    assert any("composition_orders.hero" in e and "_template" in e for e in errs), errs
    # the sticker order names `mood` PLAIN — the frame applies, nothing to flag
    assert not any("composition_orders.sticker" in e for e in errs), errs


def test_a_plain_token_on_a_template_layer_is_fine():
    cfg = _valid()
    cfg["image"]["composition_order"] = ["mood", "scene"]
    cfg["image"]["layers"] = {"mood": {"_template": TPL, "focused": "FOC"}}
    assert validate_config(cfg) == []


def test_a_bracket_token_on_a_frameless_layer_is_still_fine():
    """The pre-existing bracket idiom (reference_guidance[anchor]) must be
    untouched — only the _template combination is new and only it is rejected."""
    cfg = _valid()
    cfg["image"]["composition_order"] = ["mood[focused]", "scene"]
    cfg["image"]["layers"] = {"mood": {"focused": "FOC"}}
    assert validate_config(cfg) == []


def test_layer_without_template_is_unaffected():
    cfg = _valid()
    cfg["image"]["composition_order"] = ["mood", "scene"]
    cfg["image"]["layers"] = {"mood": {"focused": "FOC"}}
    assert validate_config(cfg) == []


# --- v7: features.stickers + image.fallback_model / image.timeout_ms ----------
# The capability is OPTIONAL: 88 existing blog configs have no `features.stickers`
# at all, and `006_to_007` seeds it disabled. So absence must be valid at every
# accepted version, and the path keys are only required once someone opts in.

def test_version_7_accepted():
    cfg = _valid()
    cfg["version"] = 7
    assert validate_config(cfg) == []


def test_features_stickers_absent_is_valid_at_every_version():
    for v in (2, 3, 4, 5, 6, 7):
        cfg = _valid()
        cfg["version"] = v
        cfg.pop("features", None)
        assert validate_config(cfg) == [], f"v{v} without features should be valid"
        cfg["features"] = {"mermaid_view": True}          # features present, stickers not
        assert validate_config(cfg) == [], f"v{v} without features.stickers should be valid"


def test_the_v7_migration_seed_validates():
    # exactly what migrations/006_to_007.py writes — it must not produce a config
    # its own validator rejects
    cfg = _valid()
    cfg["version"] = 7
    cfg["features"] = {"stickers": {"enabled": False}}
    assert validate_config(cfg) == []


def _stk(block, version=7):
    cfg = _valid()
    cfg["version"] = version
    cfg["features"] = {"stickers": block}
    return cfg


_ENABLED = {"enabled": True,
            "prompts_file": "blog/_private/stickers/stickers.yaml",
            "images_dir": "blog/_private/stickers/images",
            "sheets_dir": "blog/_private/stickers/sheets"}


def test_features_stickers_fully_enabled_block_passes():
    block = dict(_ENABLED, sheet={"size": "a4", "dpi": 300, "grid": [3, 3], "gutter": 60})
    assert validate_config(_stk(block)) == []


def test_features_stickers_must_be_a_mapping():
    for bad in (True, "on", ["enabled"]):
        errs = validate_config(_stk(bad))
        assert any("features.stickers must be a mapping" in e for e in errs), bad


def test_features_stickers_enabled_must_be_bool():
    for bad in ("yes", 1, None):
        errs = validate_config(_stk({"enabled": bad}))
        assert any("features.stickers.enabled must be a boolean" in e for e in errs), bad


def test_features_stickers_disabled_needs_no_paths():
    assert validate_config(_stk({"enabled": False})) == []
    assert validate_config(_stk({})) == []          # absent `enabled` means off


def test_features_stickers_enabled_requires_the_three_paths():
    for missing in ("prompts_file", "images_dir", "sheets_dir"):
        block = dict(_ENABLED)
        del block[missing]
        errs = validate_config(_stk(block))
        assert any(f"features.stickers.{missing}" in e for e in errs), missing


def test_features_stickers_paths_must_be_non_empty_strings_when_enabled():
    for key in ("prompts_file", "images_dir", "sheets_dir"):
        for bad in ("", "   ", 3, ["a"], None, True):
            block = dict(_ENABLED, **{key: bad})
            errs = validate_config(_stk(block))
            assert any(f"features.stickers.{key}" in e for e in errs), (key, bad)


def test_features_stickers_paths_unvalidated_when_disabled():
    # nothing to generate, so a half-written block is not an error yet
    assert validate_config(_stk({"enabled": False, "prompts_file": ""})) == []


def test_features_stickers_sheet_must_be_a_mapping():
    errs = validate_config(_stk(dict(_ENABLED, sheet=[3, 3])))
    assert any("features.stickers.sheet must be a mapping" in e for e in errs)


def test_features_stickers_sheet_dpi_and_gutter_must_be_positive_ints():
    for key in ("dpi", "gutter"):
        for bad in (0, -1, "300", 300.5, True, False, None):
            errs = validate_config(_stk(dict(_ENABLED, sheet={key: bad})))
            assert any(f"features.stickers.sheet.{key}" in e for e in errs), (key, bad)


def test_features_stickers_sheet_grid_must_be_two_positive_ints():
    for bad in ([3], [3, 3, 3], "3x3", [3, 0], [0, 3], ["3", "3"], [3, True], 9, [3, 3.0]):
        errs = validate_config(_stk(dict(_ENABLED, sheet={"grid": bad})))
        assert any("features.stickers.sheet.grid" in e for e in errs), bad
    assert validate_config(_stk(dict(_ENABLED, sheet={"grid": [3, 3]}))) == []
    assert validate_config(_stk(dict(_ENABLED, sheet={"grid": [2, 5]}))) == []


def test_features_stickers_sheet_validated_even_when_disabled():
    # the geometry is nonsense regardless of whether generation is on
    errs = validate_config(_stk({"enabled": False, "sheet": {"dpi": "300"}}))
    assert any("features.stickers.sheet.dpi" in e for e in errs)


def test_features_stickers_sheet_absent_is_valid():
    assert validate_config(_stk(dict(_ENABLED))) == []


def test_image_fallback_model_must_be_a_non_empty_string():
    for bad in ("", "  ", 3, True, None, ["m"]):
        cfg = _valid()
        cfg["image"]["fallback_model"] = bad
        errs = validate_config(cfg)
        assert any("image.fallback_model" in e for e in errs), bad


def test_image_fallback_model_valid_or_absent_ok():
    cfg = _valid()
    cfg["image"]["fallback_model"] = "gemini-2.5-flash-image"
    assert validate_config(cfg) == []
    cfg["image"].pop("fallback_model")
    assert validate_config(cfg) == []


def test_image_timeout_ms_must_be_a_positive_int():
    for bad in (0, -1, "120000", 120000.5, True, False, None):
        cfg = _valid()
        cfg["image"]["timeout_ms"] = bad
        errs = validate_config(cfg)
        assert any("image.timeout_ms" in e for e in errs), bad


def test_image_timeout_ms_valid_or_absent_ok():
    cfg = _valid()
    cfg["image"]["timeout_ms"] = 120000
    assert validate_config(cfg) == []
    cfg["image"].pop("timeout_ms")
    assert validate_config(cfg) == []
