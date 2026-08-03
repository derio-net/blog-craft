"""`_contact_sheet` geometry is parameterizable (stickers P2.T3, decision 6).

WHY: frank's regen contact sheet is `cols=5, tile_width=420` (its own
`scripts/lib/contact_sheet.py`, called at
`frank/blog/_private/frank-stickers/generate-stickers.py:143`). blog-craft's
sheet hardcodes `cols = min(len, 3)` and 400x260 tiles. Letting frank's sheet
silently reflow to 3 columns is a visible change to an artifact the operator
reviews by eye, so the geometry becomes parameters — with today's values as the
defaults, so every existing caller's output is unchanged.
"""

import importlib.util
import os

from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(_ROOT, "templates/hugo-hextra/scripts/generate-images.py")


def _mod():
    spec = importlib.util.spec_from_file_location("generate_images", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _images(n):
    """Deterministic, differently-shaped inputs (so thumbnailing is exercised)."""
    palette = ["red", "green", "blue", "orange", "purple", "cyan", "brown"]
    return [(f"v{i+1}", Image.new("RGB", (600 + 40 * i, 400 - 20 * i), palette[i % 7]))
            for i in range(n)]


# --- 1. the default call is today's geometry, byte for byte ---

def test_default_geometry_is_unchanged(tmp_path):
    m = _mod()
    out = tmp_path / "a.png"
    m._contact_sheet(_images(4), out)
    with Image.open(out) as im:
        assert im.size == (3 * 400, 2 * 260)      # cols=min(len,3)=3, rows=2, 400x260


def test_defaults_equal_explicit_todays_values_byte_for_byte(tmp_path):
    """The parameters must default to exactly the hardcoded values they replace."""
    m = _mod()
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    m._contact_sheet(_images(5), a)
    m._contact_sheet(_images(5), b, cols=3, tile_width=400, tile_height=260)
    assert a.read_bytes() == b.read_bytes()


def test_single_image_default_is_one_tile(tmp_path):
    m = _mod()
    out = tmp_path / "a.png"
    m._contact_sheet(_images(1), out)
    with Image.open(out) as im:
        assert im.size == (400, 260)


# --- 2. explicit cols=5, tile_width=420 (frank's regen geometry) ---

def test_explicit_cols_and_tile_width(tmp_path):
    m = _mod()
    out = tmp_path / "a.png"
    m._contact_sheet(_images(5), out, cols=5, tile_width=420)
    with Image.open(out) as im:
        assert im.size == (5 * 420, 260)          # one row of five 420-wide tiles


def test_explicit_cols_wraps_into_rows(tmp_path):
    m = _mod()
    out = tmp_path / "a.png"
    m._contact_sheet(_images(7), out, cols=5, tile_width=420)
    with Image.open(out) as im:
        assert im.size == (5 * 420, 2 * 260)      # 7 images, 5 wide -> 2 rows


# --- 3. cols larger than the image count clamps to the count ---

def test_cols_larger_than_count_clamps(tmp_path):
    m = _mod()
    out = tmp_path / "a.png"
    m._contact_sheet(_images(2), out, cols=5)
    with Image.open(out) as im:
        assert im.size == (2 * 400, 260)          # no empty columns


# --- tile_height=None derives proportionally from tile_width ---

def test_tile_height_none_derives_proportionally(tmp_path):
    m = _mod()
    out = tmp_path / "a.png"
    m._contact_sheet(_images(1), out, tile_width=800, tile_height=None)
    with Image.open(out) as im:
        assert im.size == (800, 520)              # 800 * 260/400
