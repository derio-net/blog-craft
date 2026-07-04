"""Card colouring is opt-in: with a data/layer_palette.yaml + a `layer:` frontmatter,
cards carry a `layer-<code>` class, the palette colour, and the full-name tag; without
a palette (or without a `layer`), cards are neutral with no layer tag.
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
SERIES = "tutorials"
LAYERS = [{"code": "api", "name": "API Layer"}, {"code": "db", "name": "Database"}]


def _build(tmp_path, with_layers):
    cfg = yaml.safe_load(open(os.path.join(FIX, "valid-v2.blog-craft.yaml")))
    cfg["series_index"] = {"style": "cards"}
    if with_layers:
        cfg["series_index"]["layers"] = LAYERS
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, str(ans), blog], check=True, capture_output=True, text=True)

    if with_layers:  # bootstrap doesn't generate the palette yet (that's a later phase)
        out = subprocess.run([sys.executable, GEN, "--config", str(ans)],
                             check=True, capture_output=True, text=True).stdout
        os.makedirs(os.path.join(blog, "data"), exist_ok=True)
        open(os.path.join(blog, "data", "layer_palette.yaml"), "w").write(out)

    d = os.path.join(blog, "content", "docs", SERIES, "01-first")
    os.makedirs(d)
    layer_line = "layer: api\n" if with_layers else ""
    open(os.path.join(d, "index.md"), "w").write(
        f"---\ntitle: First\nseries: [{SERIES}]\n{layer_line}weight: 2\ndraft: false\nsummary: s\n---\nb\n")

    r = subprocess.run(["hugo"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(os.path.join(blog, "public", "**", SERIES, "00-overview", "index.html"),
                     recursive=True)
    assert hits
    return open(hits[0]).read()


def test_cards_coloured_by_layer_when_opted_in(tmp_path):
    html = _build(tmp_path, with_layers=True)
    assert "si-card layer-api" in html, "card missing its layer class"
    assert "tag tag-layer" in html and "API Layer" in html, "full-name layer tag missing"
    # the palette colour for `api` appears in the emitted per-layer CSS
    assert ".series-index .layer-api" in html


def test_cards_neutral_without_palette(tmp_path):
    html = _build(tmp_path, with_layers=False)
    assert 'class="si-card' in html            # still cards
    assert 'class="tag tag-layer"' not in html  # but no layer tag element
    assert "si-card layer-" not in html         # no layer class on any card
    assert ".series-index .layer-" not in html  # no per-layer colour CSS
