"""tools/validate_images.py — prompts-file gate (spec D8).

Replaces frank's orphaned tests/image-pipeline/test_pipeline.py: validates
prompt_for_images.yaml against the config — schema, references existence, and
selector-walk health (a selector that silently resolves to "" would drop a
layer from every future regen of that cover).
"""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "validate_images.py")

CFG = {
    "version": 4, "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {
        "prompts_file": "prompt_for_images.yaml",
        "composition_order": ["base_character", "torso", "mood", "scene"],
        "layers": {
            "base_character": "CHAR",
            "torso": {"_select": [["torso", "series"], "torso_variant"],
                      "building": ["t0", "t1"]},
            "mood": {"calm": "CALM"},
        },
    },
}

GOOD = {"key": "building-01", "series": "building", "torso_variant": 1, "mood": "calm",
        "output": "static/images/building-01-cover.png", "prompt": "scene"}


def _run(tmp_path, entries, cfg=CFG, extra_files=()):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": entries}))
    for rel in extra_files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    return subprocess.run(
        [sys.executable, TOOL, "--config", str(tmp_path / ".blog-craft.yaml")],
        capture_output=True, text=True,
    )


def test_healthy_entries_pass(tmp_path):
    r = _run(tmp_path, [GOOD])
    assert r.returncode == 0, r.stderr


def test_duplicate_key_flagged(tmp_path):
    r = _run(tmp_path, [GOOD, dict(GOOD)])
    assert r.returncode == 1
    assert "building-01" in r.stderr and "duplicate" in r.stderr.lower()


def test_missing_required_fields_flagged(tmp_path):
    r = _run(tmp_path, [{"series": "building", "prompt": "s"}])
    assert r.returncode == 1
    assert "key" in r.stderr and "output" in r.stderr


def test_missing_prompt_flagged_unless_operator_generated(tmp_path):
    no_prompt = {k: v for k, v in GOOD.items() if k != "prompt"}
    r = _run(tmp_path, [no_prompt])
    assert r.returncode == 1 and "prompt" in r.stderr
    op = dict(no_prompt, operator_generated=True, key="banner-x")
    r2 = _run(tmp_path, [op])
    assert r2.returncode == 0, r2.stderr


def test_empty_prompt_is_a_placeholder_not_a_failure(tmp_path):
    # bootstrap ships tile entries with `prompt: ""` awaiting fill-in — a fresh
    # blog's first CI run must be green
    placeholder = dict(GOOD, key="tile-landing", prompt="")
    r = _run(tmp_path, [placeholder])
    assert r.returncode == 0, r.stderr


def test_missing_reference_path_flagged(tmp_path):
    bad = dict(GOOD, references=[".reference-pool/building/subjects/nope.png"])
    r = _run(tmp_path, [bad])
    assert r.returncode == 1
    assert "nope.png" in r.stderr


def test_existing_reference_ok(tmp_path):
    ref = ".reference-pool/building/subjects/anchor.png"
    good = dict(GOOD, references=[ref])
    r = _run(tmp_path, [good], extra_files=[ref])
    assert r.returncode == 0, r.stderr


def test_selector_out_of_range_flagged(tmp_path):
    bad = dict(GOOD, torso_variant=9)
    r = _run(tmp_path, [bad])
    assert r.returncode == 1
    assert "torso" in r.stderr and "building-01" in r.stderr


def test_selector_unknown_group_flagged(tmp_path):
    bad = dict(GOOD, series="unknown-series", torso="unknown-series")
    r = _run(tmp_path, [bad])
    assert r.returncode == 1
    assert "torso" in r.stderr


def test_freeform_passthrough_is_legit(tmp_path):
    ok = dict(GOOD, mood="a bespoke free-form mood")
    r = _run(tmp_path, [ok])
    assert r.returncode == 0, r.stderr


def test_absent_selector_field_at_any_step_is_legit(tmp_path):
    # `series` is a standard field every entry carries, so frank's torso head
    # ([torso, series]) is ALWAYS present — tiles/banners without torso_variant
    # must not be flagged. The engine's own semantics apply: a missing field at
    # ANY step is a deliberate skip; only present-but-invalid values flag.
    tile = {k: v for k, v in GOOD.items() if k not in ("torso_variant",)}
    r = _run(tmp_path, [tile])
    assert r.returncode == 0, r.stderr
    no_selector = {k: v for k, v in GOOD.items() if k not in ("series", "torso_variant")}
    r2 = _run(tmp_path, [no_selector])
    assert r2.returncode == 0, r2.stderr


def test_output_escaping_blog_tree_flagged(tmp_path):
    for bad_out in ("/abs/out.png", "../outside.png"):
        r = _run(tmp_path, [dict(GOOD, output=bad_out)])
        assert r.returncode == 1
        assert "output" in r.stderr


def test_mirror_is_byte_identical():
    mirror = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "validate_images.py")
    with open(TOOL, "rb") as a, open(mirror, "rb") as b:
        assert a.read() == b.read(), "tools/validate_images.py and its scripts/ mirror drifted"
