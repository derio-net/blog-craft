"""image.optimize — the WebP pipeline over a real Hugo build.

Bootstraps a blog with image.optimize.enabled, drops a post carrying an inline
markdown image + a screenshot shortcode + a remote image, and an assets banner,
then builds and asserts: bundle images become width-capped WebP with a srcset;
remote images pass through; and with optimize OFF, images stay raw PNG.

Requires Hugo Extended (WebP encode) — skipped if absent.
"""
import glob
import os
import re
import shutil
import subprocess

import yaml
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
SERIES = "tutorials"   # from valid-v2.blog-craft.yaml

import pytest

_hugo = shutil.which("hugo")
_extended = _hugo and "+extended" in subprocess.run([_hugo, "version"], capture_output=True, text=True).stdout
pytestmark = pytest.mark.skipif(not _extended, reason="Hugo Extended required for WebP encode")


def _base_cfg():
    with open(os.path.join(FIX, "valid-v2.blog-craft.yaml")) as f:
        return yaml.safe_load(f)


def _png(path, w, h, colour=(120, 90, 200)):
    Image.new("RGB", (w, h), colour).save(path)


def _build(tmp_path, optimize):
    cfg = _base_cfg()
    if optimize is not None:
        cfg.setdefault("image", {})["optimize"] = optimize
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, str(ans), blog], check=True, capture_output=True, text=True)
    # a post bundle with inline + screenshot + remote images
    d = os.path.join(blog, "content", "docs", SERIES, "01-alpha")
    os.makedirs(d)
    _png(os.path.join(d, "inline.png"), 2000, 1200)
    _png(os.path.join(d, "shot.png"), 1800, 1000)
    open(os.path.join(d, "index.md"), "w").write(
        "---\ntitle: Alpha\nseries: [%s]\nweight: 2\ndraft: false\nsummary: s\n---\n\n"
        "![an inline pic](inline.png)\n\n"
        '{{< screenshot src="shot.png" caption="a shot" >}}\n\n'
        "![remote](https://example.com/x.png)\n" % SERIES)
    # a track banner as an assets resource
    ai = os.path.join(blog, "assets", "images"); os.makedirs(ai, exist_ok=True)
    _png(os.path.join(ai, "banner-%s.png" % SERIES), 3000, 800, (30, 30, 60))
    r = subprocess.run(["hugo"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(os.path.join(blog, "public", "**", SERIES, "01-alpha", "index.html"),
                     recursive=True)
    assert hits, "post not built"
    return open(hits[0]).read()


def test_bundle_images_become_capped_webp_with_srcset(tmp_path):
    html = _build(tmp_path, {"enabled": True, "quality": 80,
                             "max_width": 1600, "banner_max_width": 2560})
    # inline + screenshot became webp
    assert re.search(r'src="[^"]+\.webp"', html), "no webp <img> src emitted"
    assert "srcset=" in html and ".webp" in html
    # the 2000px inline capped to 1600
    assert re.search(r'<img src="[^"]+\.webp"[^>]*\bwidth="1600"', html), "cover/inline not capped to 1600"
    # explicit width/height (no layout shift)
    assert 'height="' in html
    # remote image passes through unoptimized
    assert "https://example.com/x.png" in html
    # banner present + optimized + capped to bannerMaxWidth (3000px -> 2560)
    assert 'class="site-track-banner"' in html
    assert re.search(r'site-track-banner[^<]*<img src="[^"]+\.webp"[^>]*\bwidth="2560"', html), \
        "banner not optimized/capped to bannerMaxWidth"
    assert html.count(".webp") >= 3   # inline + screenshot + banner


def test_optimize_off_leaves_raw_png(tmp_path):
    html = _build(tmp_path, {"enabled": False})
    assert ".webp" not in html, "optimize disabled but webp emitted"
    assert re.search(r'src="[^"]+inline\.png"', html) or "inline.png" in html
    # the banner (an assets resource) still renders — raw, unoptimized
    assert 'class="site-track-banner"' in html, "banner lost when optimize disabled"
