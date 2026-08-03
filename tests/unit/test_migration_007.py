"""P3.T1 — schema migration v6 -> v7: features.stickers, seeded DEFAULT OFF.

Unlike 005_to_006 (`features.mermaid_view`, default TRUE — a rendering fix every
blog wanted), a sticker set is per-blog *content* that only frank has. Seeding
`enabled: true` would render two sticker scripts into gondor and stoa for
nothing, so this rung seeds `{"enabled": False}` and — per the ladder's
`setdefault` convention — never overwrites an operator's explicit value.
"""
import copy
import importlib.util
import os

import pytest

from migrate_config import latest_version, upgrade

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_007():
    p = os.path.join(_ROOT, "migrations", "006_to_007.py")
    spec = importlib.util.spec_from_file_location("m006", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sets_version_and_seeds_stickers_disabled():
    out = _load_007().migrate({"version": 6})
    assert out["version"] == 7
    assert out["features"]["stickers"] == {"enabled": False}   # default OFF, not ON


def test_keeps_explicit_opt_in():
    # a migration that flips an operator's opt-in is a bug, not a fix
    out = _load_007().migrate({"version": 6, "features": {"stickers": {"enabled": True}}})
    assert out["version"] == 7
    assert out["features"]["stickers"]["enabled"] is True


def test_existing_sticker_block_keeps_every_key():
    block = {"enabled": True,
             "prompts_file": "blog/_private/stickers/stickers.yaml",
             "images_dir": "blog/_private/stickers/images",
             "sheets_dir": "blog/_private/stickers/sheets",
             "sheet": {"size": "a4", "dpi": 300, "grid": [3, 3], "gutter": 60}}
    out = _load_007().migrate({"version": 6, "features": {"stickers": copy.deepcopy(block)}})
    assert out["features"]["stickers"] == block


def test_pure_input_is_not_mutated():
    cfg = {"version": 6, "features": {"mermaid_view": True}}
    before = copy.deepcopy(cfg)
    _load_007().migrate(cfg)
    assert cfg == before          # migrations are pure functions over the dict


def test_wrong_version_raises():
    with pytest.raises(ValueError, match="006_to_007.*6"):
        _load_007().migrate({"version": 5})
    with pytest.raises(ValueError):
        _load_007().migrate({})   # no version at all


def test_unrelated_config_is_untouched():
    cfg = {"version": 6,
           "project": {"name": "gondor"},
           "image": {"layers": {"a": "A"}, "composition_orders": {"hero": ["a", "scene"]}},
           "features": {"mermaid_view": False},
           "quality": {"mermaid_max_width": 1400}}
    out = _load_007().migrate(cfg)
    assert out["project"] == cfg["project"]
    assert out["image"] == cfg["image"]
    assert out["quality"] == cfg["quality"]
    assert out["features"]["mermaid_view"] is False    # sits beside stickers, unchanged


def test_ladder_head_moved_to_7():
    assert latest_version() == 7


def test_ladder_reaches_7_from_2():
    cfg = {"version": 2, "image": {"layers": {}, "composition_order": ["scene"]}, "features": {}}
    out = upgrade(cfg)
    assert out["version"] == 7
    assert out["features"]["stickers"] == {"enabled": False}
    assert out["features"]["mermaid_view"] is True     # the v6 rung still ran
