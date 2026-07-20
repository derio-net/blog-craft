"""tools/migrate_prompts.py — v4 entries -> v5 composition blocks.

The critical behavior: v5 references are EXPLICIT, so the migrator FREEZES
what the v4 precedence chain would have picked into
composition.reference_images.primary — the dynamic chain's last act.
"""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "migrate_prompts.py")

CFG = {"version": 5, "image": {"prompts_file": "prompt_for_images.yaml",
                               "reference_pool": ".reference-pool"}}


def _run(tmp_path, entries, cfg=CFG, extra_files=(), *args):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": entries}))
    for rel in extra_files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    r = subprocess.run([sys.executable, TOOL, "--config", str(tmp_path / ".blog-craft.yaml"), *args],
                       capture_output=True, text=True)
    doc = yaml.safe_load((tmp_path / "prompt_for_images.yaml").read_text())
    return r, doc.get("images", [])


def test_prompt_becomes_scene_and_selectors_become_modifiers(tmp_path):
    e = {"key": "b-01", "output": "o.png", "series": "building",
         "torso_variant": 1, "mood": "calm", "prompt": "SCENE"}
    r, out = _run(tmp_path, [e])
    assert r.returncode == 0, r.stderr
    c = out[0]["composition"]
    assert c["scene"] == "SCENE"
    assert c["modifiers"] == {"series": "building", "torso_variant": 1, "mood": "calm"}
    assert "prompt" not in out[0] and "mood" not in out[0]


def test_precedence_chain_frozen_into_primary(tmp_path):
    e = {"key": "b-01", "output": "o.png", "series": "building", "prompt": "S"}
    r, out = _run(tmp_path, [e],
                  extra_files=[".reference-pool/building/reference-building.png"])
    assert r.returncode == 0, r.stderr
    ri = out[0]["composition"]["reference_images"]
    assert ri["primary"] == ".reference-pool/building/reference-building.png"


def test_config_reference_image_beats_pool(tmp_path):
    cfg = {"version": 5, "image": {"prompts_file": "prompt_for_images.yaml",
                                   "reference_image": "static/images/reference.png"}}
    e = {"key": "k", "output": "o.png", "prompt": "S"}
    r, out = _run(tmp_path, [e], cfg=cfg, extra_files=["static/images/reference.png"])
    assert out[0]["composition"]["reference_images"]["primary"] == "static/images/reference.png"


def test_references_become_clothing(tmp_path):
    e = {"key": "k", "output": "o.png", "prompt": "S",
         "references": ["refs/a.png", "refs/b.png"]}
    r, out = _run(tmp_path, [e])
    assert out[0]["composition"]["reference_images"]["clothing"] == ["refs/a.png", "refs/b.png"]
    assert "references" not in out[0]


def test_no_resolvable_reference_means_none(tmp_path):
    e = {"key": "k", "output": "o.png", "prompt": "S"}
    r, out = _run(tmp_path, [e])
    assert "reference_images" not in out[0]["composition"]


def test_already_v5_untouched_and_idempotent(tmp_path):
    e = {"key": "k", "output": "o.png", "composition": {"scene": "S"}}
    r, out = _run(tmp_path, [e])
    assert "already v5" in r.stdout
    assert out[0] == e


def test_check_mode(tmp_path):
    legacy = {"key": "k", "output": "o.png", "prompt": "S"}
    r, _ = _run(tmp_path, [legacy], CFG, (), "--check")
    assert r.returncode == 1 and "k" in r.stderr
    v5 = {"key": "k", "output": "o.png", "composition": {"scene": "S"}}
    r2, _ = _run(tmp_path, [v5], CFG, (), "--check")
    assert r2.returncode == 0
