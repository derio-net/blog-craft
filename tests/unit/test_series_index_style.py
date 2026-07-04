"""series_index.style — cards (default) / table / none, over a real Hugo build.

Bootstraps a blog from a fixture config (varying series_index.style), drops a couple
of posts into a series, builds, and inspects the series' 00-overview HTML.
"""
import glob
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
SERIES = "tutorials"   # from valid-v2.blog-craft.yaml


def _base_cfg():
    with open(os.path.join(FIX, "valid-v2.blog-craft.yaml")) as f:
        return yaml.safe_load(f)


def _bootstrap(tmp_path, cfg):
    ans = tmp_path / "ans.yaml"
    ans.write_text(yaml.safe_dump(cfg))
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, str(ans), blog], check=True, capture_output=True, text=True)
    return blog


def _overview_html(blog):
    for n, slug in (("01", "alpha"), ("02", "beta")):
        d = os.path.join(blog, "content", "docs", SERIES, f"{n}-{slug}")
        os.makedirs(d)
        open(os.path.join(d, "index.md"), "w").write(
            f"---\ntitle: {slug.title()}\nseries: [{SERIES}]\nweight: {int(n) + 1}\n"
            f"draft: false\nsummary: about {slug}\n---\nbody\n")
    r = subprocess.run(["hugo"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(os.path.join(blog, "public", "**", SERIES, "00-overview", "index.html"),
                     recursive=True)
    assert hits, f"no 00-overview for {SERIES}"
    return open(hits[0]).read()


def test_default_style_is_cards(tmp_path):
    html = _overview_html(_bootstrap(tmp_path, _base_cfg()))   # no series_index -> cards
    assert '<div class="series-index">' in html
    assert 'class="si-card' in html
    assert '<table class="series-index">' not in html


def test_table_style(tmp_path):
    cfg = _base_cfg(); cfg["series_index"] = {"style": "table"}
    html = _overview_html(_bootstrap(tmp_path, cfg))
    assert '<table class="series-index">' in html
    assert 'class="si-card' not in html


def test_none_style_renders_no_index(tmp_path):
    cfg = _base_cfg(); cfg["series_index"] = {"style": "none"}
    html = _overview_html(_bootstrap(tmp_path, cfg))
    assert 'class="series-index"' not in html
    assert 'class="si-card' not in html
