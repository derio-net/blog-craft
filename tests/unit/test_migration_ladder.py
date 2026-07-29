"""P6.T1 — schema migration ladder (version-gated, idempotent, non-destructive)."""
import os
import subprocess
import sys

import yaml

from migrate_config import latest_version, upgrade

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "fixtures")
TOOL = os.path.join(ROOT, "tools", "migrate_config.py")


def _yaml(name):
    with open(os.path.join(FIX, name)) as f:
        return yaml.safe_load(f)


def test_latest_is_6():
    assert latest_version() == 6


def test_ladder_v1_to_latest():
    out = upgrade(_yaml("stoa-v1.blog-craft.yaml"))    # version 1
    assert out["version"] == 6
    # v2 transform ran (metaphor -> image.layers)
    assert out["image"]["composition_orders"]["hero"][0] == "base_style"
    # v3 transform ran (palette filled)
    assert out["features"]["css"]["mermaid_palette"]["node"] == "#1f3a5f"
    # v6 transform ran (default-on mermaid view)
    assert out["features"]["mermaid_view"] is True


def test_idempotent():
    v1 = _yaml("stoa-v1.blog-craft.yaml")
    once = upgrade(v1)
    twice = upgrade(once)          # already latest -> no-op
    assert once == twice


def test_002_to_003_preserves_explicit_palette():
    v2 = _yaml("stoa-v2.expected.yaml")
    v2["features"] = {"css": {"mermaid_palette": {"node": "#abc123", "stroke": "#111",
                                                  "edge": "#222", "label": "#333"}}}
    out = upgrade(v2)
    assert out["version"] == 6
    assert out["features"]["css"]["mermaid_palette"]["node"] == "#abc123"   # not overwritten


# --- 005_to_006: features.mermaid_view (default-on width fix) ----------------

def test_005_to_006_sets_version_and_default_flag():
    from importlib import import_module
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m005", os.path.join(ROOT, "migrations", "005_to_006.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = m.migrate({"version": 5})
    assert out["version"] == 6
    assert out["features"]["mermaid_view"] is True


def test_005_to_006_keeps_explicit_opt_out():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m005", os.path.join(ROOT, "migrations", "005_to_006.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = m.migrate({"version": 5, "features": {"mermaid_view": False}})
    assert out["version"] == 6
    assert out["features"]["mermaid_view"] is False   # never re-enable an opt-out


def test_005_to_006_wrong_version_raises():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m005", os.path.join(ROOT, "migrations", "005_to_006.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    import pytest
    with pytest.raises(ValueError, match="005_to_006.*5"):
        m.migrate({"version": 4})


def test_cli_non_destructive(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(open(os.path.join(FIX, "stoa-v1.blog-craft.yaml")).read())
    r = subprocess.run([sys.executable, TOOL, str(cfg)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "c.yaml.bak").exists()                       # backup written
    assert yaml.safe_load(open(os.path.join(FIX, "stoa-v1.blog-craft.yaml")))["version"] == 1
    assert (tmp_path / "c.yaml.bak").read_text().count("version: 1")  # bak has the original
    assert yaml.safe_load(cfg.read_text())["version"] == 6          # upgraded in place
