"""Schema v5 entries (blog-craft #44): composition block, named orders,
explicit reference_images.

v5 entry shape:
  composition:
    reference_images: {primary: path, clothing: [paths]}   # explicit — REPLACES
                                                           # the v4 precedence chain
    order: composition_orders[name] | [inline tokens]      # absent -> hero
    modifiers: {series, clothing: grp[sub], mood, ...}
    scene: <text>                                          # was `prompt`
Legacy v4 entries (top-level prompt + selector fields) keep the old behavior —
one engine serves both, so /update can ship it to blogs on either schema.
"""
import os
import shutil
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "generate-images.py")

CFG = {
    "version": 5,
    "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {
        "prompts_file": "prompt_for_images.yaml",
        "reference_image": "static/images/legacy-ref.png",   # must be IGNORED for v5 entries
        "composition_orders": {
            "hero": ["base_character", "reference_guidance[anchor]",
                     "reference_guidance[character]", "clothing", "mood", "scene"],
            "scenery": ["base_atmosphere", "reference_guidance[anchor]",
                        "reference_guidance[scenery_reference_image]", "scene"],
        },
        "layers": {
            "base_character": "CHAR",
            "base_atmosphere": "ATMO",
            "reference_guidance": {"anchor": "ANCHOR", "character": "CHAR-REF",
                                   "scenery_reference_image": "SCENERY-REF"},
            "clothing": {"papers": {"default": "NECKTIE", "white_lab_coat": "LAB COAT"}},
            "mood": {"worried": "WORRIED"},
        },
    },
}


def _run(tmp_path, entries, *args, extra_files=()):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(CFG))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": entries}))
    for rel in extra_files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG\r\n\x1a\nx")
    return subprocess.run(
        [sys.executable, GEN, "--config", str(tmp_path / ".blog-craft.yaml"), *args],
        capture_output=True, text=True,
    )


HERO = {
    "key": "papers-01", "output": "static/images/papers-01.png",
    "composition": {
        "reference_images": {"primary": "refs/sheet.png",
                             "clothing": ["refs/coat.png", "refs/tie.png"]},
        "modifiers": {"series": "papers", "clothing": "papers[white_lab_coat]",
                      "mood": "worried"},
        "scene": "THE SCENE",
    },
}


def test_default_order_is_hero_with_modifiers_and_scene(tmp_path):
    r = _run(tmp_path, [HERO], "--print-prompt", "papers-01")
    assert r.returncode == 0, r.stderr
    assert r.stdout.rstrip("\n") == "CHAR\n\nANCHOR\n\nCHAR-REF\n\nLAB COAT\n\nWORRIED\n\nTHE SCENE"


def test_named_order_reference(tmp_path):
    e = {"key": "s-01", "output": "o.png",
         "composition": {"order": "composition_orders[scenery]",
                         "modifiers": {"series": "building"}, "scene": "S"}}
    r = _run(tmp_path, [e], "--print-prompt", "s-01")
    assert r.returncode == 0, r.stderr
    assert r.stdout.rstrip("\n") == "ATMO\n\nANCHOR\n\nSCENERY-REF\n\nS"


def test_inline_order_override(tmp_path):
    e = {"key": "i-01", "output": "o.png",
         "composition": {"order": ["base_character", "scene"], "scene": "S"}}
    r = _run(tmp_path, [e], "--print-prompt", "i-01")
    assert r.returncode == 0, r.stderr
    assert r.stdout.rstrip("\n") == "CHAR\n\nS"


def test_explicit_references_replace_precedence(tmp_path):
    # config reference_image exists on disk but the v5 entry declares its own —
    # payload must be primary + clothing, in order, and NOT the legacy ref
    r = _run(tmp_path, [HERO], "--dry-run",
             extra_files=["static/images/legacy-ref.png", "refs/sheet.png",
                          "refs/coat.png", "refs/tie.png"])
    assert r.returncode == 0, r.stderr
    assert "3 image(s) to model" in r.stdout
    assert "refs/sheet.png" in r.stdout and "refs/coat.png" in r.stdout
    assert "legacy-ref.png" not in r.stdout


def test_no_reference_images_means_no_references(tmp_path):
    # v5 composition entry WITHOUT reference_images -> prompt-only; the legacy
    # precedence chain (config reference_image on disk!) must NOT kick in
    e = {"key": "n-01", "output": "o.png",
         "composition": {"modifiers": {}, "scene": "S",
                         "reference_images": {}}}
    r = _run(tmp_path, [e], "--dry-run", extra_files=["static/images/legacy-ref.png"])
    assert r.returncode == 0, r.stderr
    assert "0 image(s) to model" in r.stdout


def test_missing_declared_reference_warns_and_skips(tmp_path):
    r = _run(tmp_path, [HERO], "--dry-run", extra_files=["refs/sheet.png"])
    assert r.returncode == 0, r.stderr
    assert "1 image(s) to model" in r.stdout
    assert "WARN" in r.stderr and "coat.png" in r.stderr


def test_legacy_v4_entry_keeps_old_reference_precedence(tmp_path):
    e = {"key": "l-01", "output": "o.png", "prompt": "LEGACY SCENE", "mood": "worried"}
    cfg_v4_entryish = dict(e)
    r = _run(tmp_path, [cfg_v4_entryish], "--dry-run",
             extra_files=["static/images/legacy-ref.png"])
    assert r.returncode == 0, r.stderr
    assert "legacy-ref.png" in r.stdout          # old precedence still serves v4 entries


def test_generation_writes_output_in_test_mode(tmp_path):
    env = dict(os.environ, BLOG_CRAFT_TEST_MODE="1")
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(CFG))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": [HERO]}))
    r = subprocess.run([sys.executable, GEN, "--config", str(tmp_path / ".blog-craft.yaml"),
                        "--only", "papers-01"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "static" / "images" / "papers-01.png").is_file()
    shutil.rmtree(tmp_path / ".regen-archive", ignore_errors=True)
