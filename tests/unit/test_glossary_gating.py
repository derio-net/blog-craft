"""P5.T5 — the glossary surface materializes iff features.glossary.enabled.

Opt-in is a contract with every existing blog-craft blog: one that never asked
for the feature must carry none of it — no shortcodes to shadow its own, no
stylesheet, no <link> in <head>. Mirrors test_features_gating.py.
"""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

SHIPPED = (
    "layouts/shortcodes/abbr.html",
    "layouts/shortcodes/glossary-index.html",
    "assets/css/glossary.css",
)


def _base():
    with open(os.path.join(FIX, "stoa-v2.expected.yaml")) as f:
        return yaml.safe_load(f)


def _bootstrap(cfg, tmp_path, name):
    ans = tmp_path / f"{name}.yaml"
    ans.write_text(yaml.safe_dump(cfg))
    target = tmp_path / name
    r = subprocess.run(["bash", RENDER, str(ans), str(target)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def test_enabled_materializes_the_whole_surface(tmp_path):
    cfg = _base()
    cfg.setdefault("features", {})["glossary"] = {"enabled": True}
    b = _bootstrap(cfg, tmp_path, "on")
    for rel in SHIPPED:
        assert (b / rel).exists(), f"{rel} missing when the feature is enabled"


def test_disabled_materializes_nothing(tmp_path):
    cfg = _base()
    cfg.setdefault("features", {})["glossary"] = {"enabled": False}
    b = _bootstrap(cfg, tmp_path, "off")
    for rel in SHIPPED:
        assert not (b / rel).exists(), f"{rel} present when the feature is disabled"


def test_absent_key_materializes_nothing(tmp_path):
    cfg = _base()
    cfg.setdefault("features", {}).pop("glossary", None)
    b = _bootstrap(cfg, tmp_path, "absent")
    for rel in SHIPPED:
        assert not (b / rel).exists(), f"{rel} present with no features.glossary at all"


def test_head_end_emits_no_glossary_link_when_disabled(tmp_path):
    cfg = _base()
    cfg.setdefault("features", {}).pop("glossary", None)
    b = _bootstrap(cfg, tmp_path, "nolink")
    head = (b / "layouts/partials/custom/head-end.html").read_text()
    # the partial always ships; it must be a no-op without the asset
    assert "css/glossary.css" in head
    assert "with resources.Get" in head
