"""P2.T3 — reference-pool resolution + curation (archive FIFO, contact sheet)."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN_PATH = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "generate-images.py")


def _load_gen():
    spec = importlib.util.spec_from_file_location("gen_images", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load_gen()


# ---- reference resolution (5-step) ----

def test_reference_override_wins(tmp_path):
    ovr = tmp_path / "o.png"; ovr.write_bytes(b"x")
    assert gen.select_reference({}, {}, tmp_path, ovr) == ovr


def test_reference_single_image(tmp_path):
    (tmp_path / "static" / "images").mkdir(parents=True)
    ref = tmp_path / "static" / "images" / "reference.png"; ref.write_bytes(b"x")
    cfg = {"reference_image": "static/images/reference.png"}
    assert gen.select_reference({}, cfg, tmp_path, None) == ref


def test_reference_per_series_then_generic(tmp_path):
    pool = tmp_path / ".reference-pool"
    (pool / "papers").mkdir(parents=True)
    (pool / "generic").mkdir(parents=True)
    (pool / "papers" / "reference-papers.png").write_bytes(b"p")
    (pool / "generic" / "reference-generic.png").write_bytes(b"g")
    cfg = {"reference_pool": ".reference-pool"}
    # per-series hit
    assert gen.select_reference({"series": "papers"}, cfg, tmp_path, None) == pool / "papers" / "reference-papers.png"
    # unknown series -> generic fallback
    assert gen.select_reference({"series": "nope"}, cfg, tmp_path, None) == pool / "generic" / "reference-generic.png"


def test_reference_none_when_absent(tmp_path):
    assert gen.select_reference({"series": "x"}, {"reference_pool": ".reference-pool"}, tmp_path, None) is None


# ---- curation: archive FIFO ----

def test_archive_fifo_cap(tmp_path):
    out = tmp_path / "static" / "images" / "k.png"
    for b in (b"one", b"two", b"three"):
        gen.write_archive_entry(tmp_path, "k", b, "prompt", None, "m", out, cap=2)
    adir = tmp_path / ".regen-archive" / "k"
    pngs = sorted(adir.glob("k-*.png"))
    assert len(pngs) == 2, [p.name for p in pngs]              # oldest pruned
    assert all(p.with_suffix(".txt").exists() for p in pngs)   # sidecars pruned with images


# ---- curation: contact sheet + output via TEST_MODE generator ----

def test_count_makes_contact_sheet_and_output(tmp_path):
    cfg = {
        "version": 2, "project": {"name": "x"}, "series": [], "voice": "v",
        "image": {
            "prompts_file": "prompt_for_images.yaml", "output_dir": "static/images",
            "curation": {"archive_cap": 30, "contact_sheet": True},
            "composition_order": ["base_style", "scene"],
            "layers": {"base_style": "S"},
        },
    }
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump(
        {"images": [{"key": "t-01", "output": "static/images/t-01.png", "prompt": "SCENE"}]}))
    env = dict(os.environ, BLOG_CRAFT_TEST_MODE="1")
    r = subprocess.run([sys.executable, GEN_PATH, "--config", str(tmp_path / ".blog-craft.yaml"),
                        "--count", "3"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "static" / "images" / "t-01.png").exists()
    assert (tmp_path / ".regen-archive" / "t-01" / "contact-sheet.png").exists()
