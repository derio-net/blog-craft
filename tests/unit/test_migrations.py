"""P1.T3 — v1->v2 config migration (stoa is the real-world case)."""
import importlib.util
import os

import yaml

from validate_config import validate_config  # tools/ on sys.path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "fixtures")


def _load_migrate():
    path = os.path.join(ROOT, "migrations", "001_to_002.py")
    spec = importlib.util.spec_from_file_location("m001_to_002", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.migrate


migrate = _load_migrate()


def _yaml(name):
    with open(os.path.join(FIX, name)) as f:
        return yaml.safe_load(f)


def test_migration_produces_valid_v2():
    assert validate_config(migrate(_yaml("stoa-v1.blog-craft.yaml"))) == []


def test_migration_matches_golden():
    assert migrate(_yaml("stoa-v1.blog-craft.yaml")) == _yaml("stoa-v2.expected.yaml")


def test_migration_specifics():
    out = migrate(_yaml("stoa-v1.blog-craft.yaml"))
    assert out["version"] == 2
    assert out["image"]["composition_order"] == [
        "base_style", "persona", "visual_constants", "scene", "reference_guidance",
    ]
    assert out["series"] and all(s["content_type"] == "posts" for s in out["series"])
    assert {"base_style", "persona", "visual_constants", "reference_guidance"} <= set(out["image"]["layers"])
    # v1 spellings must be gone
    assert "metaphor" not in out
    assert "image_gen" not in out


def test_migration_rejects_wrong_version():
    import pytest
    with pytest.raises(ValueError):
        migrate({"version": 2})
