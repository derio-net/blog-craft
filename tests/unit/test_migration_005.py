"""Schema migration v4 -> v5: composition_order becomes composition_orders.hero."""
import importlib.util
import os

import pytest

from migrate_config import latest_version, upgrade

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_005():
    p = os.path.join(_ROOT, "migrations", "004_to_005.py")
    spec = importlib.util.spec_from_file_location("m005", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_latest_version_is_5():
    # NB: the ladder head has moved to 6 (005_to_006, mermaid readability
    # config surface) — this checks that 004_to_005 still reaches its own
    # target rung, not that 5 is still the overall latest.
    assert latest_version() >= 5


def test_single_order_becomes_hero():
    cfg = {"version": 4, "image": {"composition_order": ["a", "scene"]}}
    out = _load_005().migrate(cfg)
    assert out["version"] == 5
    assert out["image"]["composition_orders"] == {"hero": ["a", "scene"]}
    assert "composition_order" not in out["image"]


def test_existing_orders_win():
    cfg = {"version": 4, "image": {"composition_order": ["a"],
                                   "composition_orders": {"hero": ["b"]}}}
    out = _load_005().migrate(cfg)
    assert out["image"]["composition_orders"] == {"hero": ["b"]}
    assert out["image"]["composition_order"] == ["a"]   # untouched when orders exist


def test_version_gate():
    with pytest.raises(ValueError):
        _load_005().migrate({"version": 3})


def test_ladder_reaches_5_from_2():
    cfg = {"version": 2, "image": {"layers": {}, "composition_order": ["scene"]}, "features": {}}
    out = upgrade(cfg)
    assert out["version"] == 6   # ladder now runs through 005_to_006 too
    assert out["image"]["composition_orders"]["hero"] == ["scene"]
