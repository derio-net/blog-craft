"""roadmap.html adopts data/layer_palette.yaml when present (a layer is the same colour
as in the series-index cards), and falls back to neutral — with no --rm-accent — when the
blog has no palette.
"""
import glob
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
GEN = os.path.join(ROOT, "tools", "gen-layer-palette.py")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _roadmap_html(tmp_path, with_palette):
    cfg = yaml.safe_load(open(os.path.join(FIX, "valid-v2.blog-craft.yaml")))
    cfg["series_index"] = {"style": "cards"}
    if with_palette:
        cfg["series_index"]["layers"] = [{"code": "api", "name": "API Layer"}]
    tag = "p" if with_palette else "n"    # unique per call (the test bootstraps twice)
    ans = tmp_path / f"ans-{tag}.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = str(tmp_path / f"blog-{tag}")
    b = subprocess.run(["bash", RENDER, str(ans), blog], capture_output=True, text=True)
    assert b.returncode == 0, f"bootstrap failed:\n{b.stdout}\n{b.stderr}"

    os.makedirs(os.path.join(blog, "data"), exist_ok=True)
    open(os.path.join(blog, "data", "roadmap.yaml"), "w").write(
        "layers:\n  - { num: 1, key: api, title: \"API\", sub_items: [x], tags: [t] }\n")
    if with_palette:
        out = subprocess.run([sys.executable, GEN, "--config", str(ans)],
                             check=True, capture_output=True, text=True).stdout
        open(os.path.join(blog, "data", "layer_palette.yaml"), "w").write(out)

    d = os.path.join(blog, "content", "docs", "rm"); os.makedirs(d)
    open(os.path.join(d, "index.md"), "w").write(
        "---\ntitle: RM\nweight: 9\ndraft: false\n---\n{{< roadmap >}}\n")

    r = subprocess.run(["hugo"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(os.path.join(blog, "public", "**", "rm", "index.html"), recursive=True)
    assert hits
    return open(hits[0]).read()


def test_roadmap_never_emits_rm_accent(tmp_path):
    assert "rm-accent" not in _roadmap_html(tmp_path, with_palette=True)
    assert "rm-accent" not in _roadmap_html(tmp_path, with_palette=False)


def test_roadmap_uses_palette_when_present(tmp_path):
    html = _roadmap_html(tmp_path, with_palette=True)
    assert ".roadmap .layer-api" in html, "roadmap not colouring from the palette"
    assert "roadmap-card layer-api" in html


def test_roadmap_neutral_without_palette(tmp_path):
    html = _roadmap_html(tmp_path, with_palette=False)
    assert ".roadmap .layer-" not in html   # no per-layer colour rules
    assert "roadmap-card layer-api" in html  # class still applied (just uncoloured)
