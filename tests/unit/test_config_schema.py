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


def test_version_must_be_2():
    cfg = _valid()
    cfg["version"] = 1
    assert validate_config(cfg)


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
