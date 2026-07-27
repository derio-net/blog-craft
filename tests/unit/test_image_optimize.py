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


def _corrupt_png(path):
    """A .png whose bytes don't decode (broken IDAT) — like a placeholder stub.
    Hugo rejects it with 'invalid checksum'; opt-image must not crash the build."""
    import io
    buf = io.BytesIO(); Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(buf, "PNG")
    data = bytearray(buf.getvalue())
    data[-8] ^= 0xFF  # corrupt a byte in the IDAT/CRC → undecodable
    with open(path, "wb") as f:
        f.write(bytes(data))


def _build(tmp_path, optimize, cover=False):
    cfg = _base_cfg()
    if optimize is not None:
        cfg.setdefault("image", {})["optimize"] = optimize
    if cover:
        # the cover <img> lives in docs/single.html, which only materializes with
        # the papers content-type enabled
        cfg.setdefault("content_types", {}).setdefault("papers", {})["enabled"] = True
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, str(ans), blog], check=True, capture_output=True, text=True)
    # a post bundle with inline + screenshot + remote images
    d = os.path.join(blog, "content", "docs", SERIES, "01-alpha")
    os.makedirs(d)
    _png(os.path.join(d, "inline.png"), 2000, 1200)
    _png(os.path.join(d, "shot.png"), 1800, 1000)
    _corrupt_png(os.path.join(d, "broken.png"))   # a placeholder stub that won't decode
    if cover:
        _png(os.path.join(d, "cover.png"), 2400, 1000, (200, 60, 60))
    open(os.path.join(d, "index.md"), "w").write(
        "---\ntitle: Alpha\nseries: [%s]\nweight: 2\ndraft: false\nsummary: s\n---\n\n"
        "![an inline pic](inline.png)\n\n"
        '{{< screenshot src="shot.png" caption="a shot" >}}\n\n'
        "![a broken placeholder](broken.png)\n\n"
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
    # a corrupt/undecodable image falls through to raw (build did NOT crash — _build
    # asserts returncode 0 — and the stub is served as-is, not a broken webp)
    assert "broken.png" in html, "corrupt image not passed through raw"
    # banner present + optimized + capped to bannerMaxWidth (3000px -> 2560)
    assert 'class="site-track-banner"' in html
    assert re.search(r'site-track-banner[^<]*<img src="[^"]+\.webp"[^>]*\bwidth="2560"', html), \
        "banner not optimized/capped to bannerMaxWidth"
    assert html.count(".webp") >= 3   # inline + screenshot + banner


def test_post_cover_is_optimized(tmp_path):
    """The post cover is the largest image on the page — it must go through
    opt-image like every other image path, not ship as a raw <img>."""
    html = _build(tmp_path, {"enabled": True, "quality": 80,
                             "max_width": 1600, "banner_max_width": 2560},
                  cover=True)
    m = re.search(r'<div class="post-cover">\s*(<img [^>]*>)', html)
    assert m, "post cover not rendered"
    img = m.group(1)
    assert ".webp" in img, "cover not optimized to webp: %s" % img
    assert "srcset=" in img, "cover has no srcset: %s" % img
    assert 'width="1600"' in img, "2400px cover not capped to maxWidth: %s" % img
    assert 'height="' in img, "cover missing explicit height (layout shift): %s" % img


def test_srcset_reaches_the_primary_when_the_source_is_narrower_than_the_cap(tmp_path):
    """The top srcset candidate must be the PRIMARY's width, not the cap.

    Every other case here feeds a source LARGER than the cap (3000px banner under
    2560, 2400px cover under 1600), where the cap and the primary width coincide
    and the bug is invisible. Raise the caps above the fixtures and they diverge:
    the cap-derived candidate fails the source-width clamp, is dropped, and
    nothing left in the srcset matches the primary.

    That is not a cosmetic gap. Per the HTML spec, once a srcset carries `w`
    descriptors the `src` attribute stops being a selection candidate — so the
    full-resolution derivative becomes unreachable and the browser renders an
    upscaled one instead, while every file still returns 200. Measured downstream
    on derio-net/frank#710: 179 images affected, banners rendering at a 2.0x
    upscale on a 1512px viewport at DPR 2.
    """
    html = _build(tmp_path, {"enabled": True, "quality": 80,
                             "max_width": 4000, "banner_max_width": 4000},
                  cover=True)

    checked = 0
    for img in re.findall(r"<img [^>]*>", html):
        ss = re.search(r'srcset="([^"]*)"', img)
        w = re.search(r'width="(\d+)"', img)
        if not ss or not w:
            continue
        cands = []
        for part in ss.group(1).split(", "):
            bits = part.strip().rsplit(" ", 1)
            if len(bits) == 2 and bits[1].endswith("w") and bits[1][:-1].isdigit():
                cands.append(int(bits[1][:-1]))
        if not cands:
            continue          # density descriptors keep src as a candidate
        checked += 1
        primary = int(w.group(1))
        assert max(cands) >= primary, (
            "srcset tops out at %dw but src is %dw — the full-resolution image "
            "is unreachable and renders upscaled: %s" % (max(cands), primary, img)
        )

    assert checked >= 2, "expected at least the cover and the banner to be checked"


def test_optimize_off_leaves_raw_png(tmp_path):
    html = _build(tmp_path, {"enabled": False})
    assert ".webp" not in html, "optimize disabled but webp emitted"
    assert re.search(r'src="[^"]+inline\.png"', html) or "inline.png" in html
    # the banner (an assets resource) still renders — raw, unoptimized
    assert 'class="site-track-banner"' in html, "banner lost when optimize disabled"
