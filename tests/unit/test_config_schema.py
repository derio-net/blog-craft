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


def test_versions_2_through_4_accepted():
    for v in (2, 3, 4):
        cfg = _valid()
        cfg["version"] = v
        assert validate_config(cfg) == [], f"version {v} should be valid"


def test_out_of_range_versions_rejected():
    for v in (1, 5, "2"):
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
