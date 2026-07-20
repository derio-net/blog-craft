"""Schema migration v3 -> v4 (spec D7): the dead vocabularies become config data.

003_to_004 does three things, all output-preserving:
  1. `metaphor.*` (the old bootstrap-blog vocabulary) -> `image.layers` +
     `image.reference_image`, with `composition_order` defaulting to the exact
     order the old blog-post skill hand-concatenated — so composed prompts are
     byte-identical before and after.
  2. `image_gen.*` (the old settings vocabulary) merges into `image.*`
     (existing `image.*` keys win).
  3. A dict layer named `torso` without `_select` gains the previously
     hardcoded engine rule as explicit data:
     `_select: [[torso, series], torso_variant]`.
"""
import importlib.util
import os

import pytest

from compose import compose  # tools/ on sys.path
from migrate_config import latest_version, upgrade

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_004():
    p = os.path.join(_ROOT, "migrations", "003_to_004.py")
    spec = importlib.util.spec_from_file_location("m004", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OLD_SKILL_ORDER = ["base_style", "persona", "visual_constants", "scene", "reference_guidance"]

METAPHOR_CFG = {
    "version": 3,
    "project": {"name": "x"},
    "metaphor": {
        "base_style": "STYLE",
        "persona": "PERSONA",
        "visual_constants": ["c1", "c2"],
        "reference_guidance": "GUIDE",
        "reference_image": "static/images/reference.png",
    },
    "image_gen": {"provider": "gemini", "api_key_env": "GEMINI_API_KEY"},
    "image": {"model": "gemini-3-pro-image-preview"},
}


def test_latest_version_is_4():
    assert latest_version() == 4


def test_metaphor_becomes_layers_and_reference_image():
    out = _load_004().migrate(METAPHOR_CFG)
    assert "metaphor" not in out
    layers = out["image"]["layers"]
    assert layers["base_style"] == "STYLE"
    assert layers["persona"] == "PERSONA"
    assert layers["visual_constants"] == ["c1", "c2"]
    assert layers["reference_guidance"] == "GUIDE"
    assert out["image"]["reference_image"] == "static/images/reference.png"
    assert out["image"]["composition_order"] == OLD_SKILL_ORDER
    assert out["version"] == 4


def test_metaphor_migration_preserves_composed_output():
    out = _load_004().migrate(METAPHOR_CFG)
    got = compose(out["image"]["composition_order"], out["image"]["layers"],
                  {"prompt": "THE SCENE"})
    # exactly the old skill's hand-concatenation, blank-line separated
    assert got == "STYLE\n\nPERSONA\n\n- c1\n- c2\n\nTHE SCENE\n\nGUIDE"


def test_image_gen_merges_but_image_wins():
    cfg = {
        "version": 3,
        "image_gen": {"model": "OLD-MODEL", "provider": "gemini"},
        "image": {"model": "NEW-MODEL"},
    }
    out = _load_004().migrate(cfg)
    assert "image_gen" not in out
    assert out["image"]["model"] == "NEW-MODEL"      # existing image.* wins
    assert out["image"]["provider"] == "gemini"      # merged in


def test_existing_layers_win_over_metaphor():
    cfg = {
        "version": 3,
        "metaphor": {"persona": "OLD"},
        "image": {"layers": {"persona": "KEEP"},
                  "composition_order": ["persona", "scene"]},
    }
    out = _load_004().migrate(cfg)
    assert out["image"]["layers"]["persona"] == "KEEP"
    assert out["image"]["composition_order"] == ["persona", "scene"]  # untouched


def test_torso_dict_gains_select():
    cfg = {
        "version": 3,
        "image": {"layers": {"torso": {"building": ["t0"]},
                             "mood": {"calm": "CALM"}}},
    }
    out = _load_004().migrate(cfg)
    assert out["image"]["layers"]["torso"]["_select"] == [["torso", "series"], "torso_variant"]
    assert "_select" not in out["image"]["layers"]["mood"]  # default [mood] is right


def test_torso_with_existing_select_untouched():
    cfg = {
        "version": 3,
        "image": {"layers": {"torso": {"_select": ["torso"], "building": ["t0"]}}},
    }
    out = _load_004().migrate(cfg)
    assert out["image"]["layers"]["torso"]["_select"] == ["torso"]


def test_scalar_torso_layer_untouched():
    cfg = {"version": 3, "image": {"layers": {"torso": "always this torso"}}}
    out = _load_004().migrate(cfg)
    assert out["image"]["layers"]["torso"] == "always this torso"


def test_empty_metaphor_block_injects_nothing():
    out = _load_004().migrate({"version": 3, "metaphor": {}, "image": {}})
    assert "metaphor" not in out
    assert "composition_order" not in out.get("image", {})
    assert "layers" not in out.get("image", {})


def test_version_gate():
    with pytest.raises(ValueError):
        _load_004().migrate({"version": 2})


def test_ladder_reaches_4_from_2():
    cfg = {"version": 2, "image": {"layers": {}}, "features": {}}
    out = upgrade(cfg)
    assert out["version"] == 4
