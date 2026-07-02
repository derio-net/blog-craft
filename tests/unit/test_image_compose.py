"""P2.T2 — prompt-equality (smoke-image-compose).

End-to-end proof of Approach A: the shipped generator, reading a v2 config + a
prompts file, composes each prompt byte-identically to frank's rule
("\\n\\n".join of the resolved sections). Expected strings are hardcoded
independently of compose.py — this catches config-extraction / layer-resolution
/ wiring bugs, not just the concatenator (unit-tested separately).
"""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "generate-images.py")


def _print_prompt(tmp_path, cfg, prompts, key):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump(prompts))
    out = subprocess.run(
        [sys.executable, GEN, "--config", str(tmp_path / ".blog-craft.yaml"), "--print-prompt", key],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.rstrip("\n")


FRANK_CFG = {
    "version": 2,
    "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {
        "prompts_file": "prompt_for_images.yaml",
        "composition_order": ["base_character", "base_atmosphere", "reference_guidance", "torso", "mood", "scene"],
        "layers": {
            "base_character": "CHAR", "base_atmosphere": "ATMO", "reference_guidance": "GUIDE",
            "torso": {"building": ["b0", "b1"], "papers": ["p0"]},
            "mood": {"focused": "FOC", "weighing": "WEI"},
        },
    },
}

STOA_CFG = {
    "version": 2,
    "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {
        "prompts_file": "prompt_for_images.yaml",
        "composition_order": ["base_style", "persona", "visual_constants", "scene", "reference_guidance"],
        "layers": {
            "base_style": "STYLE", "persona": "PER",
            "visual_constants": ["v1", "v2"], "reference_guidance": "RG",
        },
    },
}


def test_frank_style_prompt_equality(tmp_path):
    prompts = {"images": [
        {"key": "building-01", "torso": "building", "torso_variant": 1, "mood": "focused", "prompt": "SCENE"},
    ]}
    got = _print_prompt(tmp_path, FRANK_CFG, prompts, "building-01")
    assert got == "CHAR\n\nATMO\n\nGUIDE\n\nb1\n\nFOC\n\nSCENE"


def test_frank_series_defaults_torso_group(tmp_path):
    prompts = {"images": [
        {"key": "paper-01", "series": "papers", "torso_variant": 0, "mood": "weighing", "prompt": "S2"},
    ]}
    got = _print_prompt(tmp_path, FRANK_CFG, prompts, "paper-01")
    assert got == "CHAR\n\nATMO\n\nGUIDE\n\np0\n\nWEI\n\nS2"


def test_stoa_style_prompt_equality(tmp_path):
    prompts = {"images": [{"key": "forum-01", "prompt": "SC"}]}
    got = _print_prompt(tmp_path, STOA_CFG, prompts, "forum-01")
    assert got == "STYLE\n\nPER\n\n- v1\n- v2\n\nSC\n\nRG"
