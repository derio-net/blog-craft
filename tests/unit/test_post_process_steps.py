"""post_process() — the three derivative steps must agree with each other.

`crop_resize` and `ico` both write to a `target`; `resize` historically did not,
so it always clobbered the source image. That made the canonical "one master ->
many derivatives" pipeline (a favicon set) inexpressible: each `resize` destroyed
the source the next step had to read.

These tests pin the shared contract — `target` on every step, `size` as the
square shorthand — and the backwards-compatible default (no `target` -> write
back over the source).
"""
import importlib.util
import os

from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(_ROOT, "templates/hugo-hextra/scripts/generate-images.py")


def _mod():
    """Import the hyphenated script by path (not importable as a module name)."""
    spec = importlib.util.spec_from_file_location("generate_images", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _src(tmp_path, w=1024, h=1024):
    p = tmp_path / "master.png"
    Image.new("RGB", (w, h), (10, 80, 160)).save(p)
    return p


def test_resize_writes_to_target_leaving_the_source_intact(tmp_path):
    m = _mod()
    src = _src(tmp_path)
    out = tmp_path / "small.png"
    m.post_process(src, [{"resize": {"target": str(out), "width": 180, "height": 180}}])
    assert Image.open(out).size == (180, 180)
    assert Image.open(src).size == (1024, 1024), "source clobbered despite an explicit target"


def test_resize_size_is_the_square_shorthand(tmp_path):
    m = _mod()
    src = _src(tmp_path)
    out = tmp_path / "sq.png"
    m.post_process(src, [{"resize": {"target": str(out), "size": 32}}])
    assert Image.open(out).size == (32, 32)


def test_resize_without_target_still_overwrites_the_source(tmp_path):
    """Backwards compatibility: the pre-existing width/height form is unchanged."""
    m = _mod()
    src = _src(tmp_path)
    m.post_process(src, [{"resize": {"width": 64, "height": 48}}])
    assert Image.open(src).size == (64, 48)


def test_favicon_pipeline_produces_every_derivative(tmp_path):
    """The end-to-end case the missing `target` made impossible: one master
    cropped square, then fanned out to each derivative in a single pass."""
    m = _mod()
    src = _src(tmp_path, 1600, 900)
    master = tmp_path / "favicon.png"
    touch = tmp_path / "apple-touch-icon.png"
    p32 = tmp_path / "favicon-32x32.png"
    ico = tmp_path / "favicon.ico"
    m.post_process(src, [
        {"crop_resize": {"target": str(master), "width": 512, "height": 512}},
        {"resize": {"target": str(touch), "size": 180}},
        {"resize": {"target": str(p32), "size": 32}},
        {"ico": {"target": str(ico), "size": 32}},
    ])
    assert Image.open(master).size == (512, 512)
    assert Image.open(touch).size == (180, 180)
    assert Image.open(p32).size == (32, 32)
    assert ico.exists()
