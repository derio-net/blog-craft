"""`build-sheets.py` — the print contract (stickers P4.T1, stk-3).

This is the only genuinely new code in the sticker port, and the only place in
blog-craft that does print-resolution layout. The assertions here are the print
contract, not smoke:

- the page is EXACTLY 2480x3508 for `size: a4` + `dpi: 300`, DERIVED from a
  millimetre table (`round(210 / 25.4 * 300)`), never configured. Those are
  precisely frank's hardcoded `A4_W, A4_H` — verified against the committed
  artifact `frank/blog/_private/frank-stickers/sheets/frank-stickers-A4-sheet1.png`
  (IHDR 2480x3508) on 2026-08-03;
- the DPI is written INTO the PNG, so "print at 100%" maps the page to A4 1:1 and
  the dark-green keyline stays a literal cut path. PNG stores resolution as
  integer pixels-per-metre in `pHYs`, so 300 dpi is 11811 px/m — again exactly
  what frank's committed sheet carries;
- the grid is CENTRED with frank's gutter algebra, generalised to `[cols, rows]`.
  frank hardcodes `3` in five places; for `[3, 3]` the generalised form must
  reproduce his numbers exactly, and that equality is the regression test.

`sheet.size` is deliberately NOT validated by `tools/validate_config.py` (phase-3
discovery `p3-stickers-validation-semantics`: the paper vocabulary belongs to this
script), so this script is the ONLY guard against an unlayoutable size.
"""

import os
import subprocess
import sys

import yaml
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(_ROOT, "templates/features/stickers/scripts/build-sheets.py")

# frank's constants (blog/_private/frank-stickers/build-sheets.py:21-25).
FRANK_W, FRANK_H = 2480, 3508
FRANK_GUTTER = 60
WHITE = (255, 255, 255)


def _colour(i: int) -> tuple:
    """A distinct, never-white solid colour per sticker index."""
    return ((i * 13 + 7) % 240, (i * 29 + 40) % 240, (i * 7 + 90) % 240)


def _cfg(**stickers) -> dict:
    stk = {
        "enabled": True,
        "prompts_file": "stickers.yaml",
        "images_dir": "images",
        "sheets_dir": "sheets",
    }
    stk.update(stickers)
    return {
        "version": 7,
        "project": {"name": "Frank"},
        "series": [],
        "voice": "v",
        "image": {"prompts_file": "prompt_for_images.yaml"},
        "features": {"stickers": stk},
    }


def _entries(placements) -> list:
    """`[(key, sheet, pos), ...]` -> sticker prompt entries (v5 shape)."""
    return [{"key": k,
             "output": f"images/sticker-{k}.png",
             "description": f"desc {k}",
             "sheet": sheet,
             "pos": pos,
             "composition": {"order": "sticker", "modifiers": {}, "scene": "S"}}
            for k, sheet, pos in placements]


def _blog(tmp_path, cfg, entries, images=True, size=(120, 120)):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    stk = cfg["features"]["stickers"]
    (tmp_path / stk["prompts_file"]).write_text(yaml.safe_dump({"images": entries}))
    if images:
        idir = tmp_path / stk["images_dir"]
        idir.mkdir(parents=True, exist_ok=True)
        for i, e in enumerate(entries):
            Image.new("RGB", size, _colour(i)).save(idir / f"sticker-{e['key']}.png")
    return tmp_path / ".blog-craft.yaml"


def _run(tmp_path, cfg, entries, images=True):
    cfg_path = _blog(tmp_path, cfg, entries, images=images)
    return subprocess.run([sys.executable, SCRIPT, "--config", str(cfg_path)],
                          capture_output=True, text=True)


def _sheet(tmp_path, n, prefix="frank-stickers", paper="A4", sheets_dir="sheets"):
    return tmp_path / sheets_dir / f"{prefix}-{paper}-sheet{n}.png"


def _frank_geometry(W=FRANK_W, H=FRANK_H, G=FRANK_GUTTER):
    """frank's HARDCODED 3x3 algebra, transcribed verbatim (build-sheets.py:29-31).

    The generalised `[cols, rows]` implementation must be numerically identical to
    this for `[3, 3]`. If it is not, the algebra is wrong, not this test.
    """
    cell = min((W - 4 * G) // 3, (H - 4 * G) // 3)
    grid = 3 * cell + 2 * G
    return cell, (W - grid) // 2, (H - grid) // 2


def _generalised(cols, rows, W=FRANK_W, H=FRANK_H, G=FRANK_GUTTER):
    cell = min((W - (cols + 1) * G) // cols, (H - (rows + 1) * G) // rows)
    grid_w, grid_h = cols * cell + (cols - 1) * G, rows * cell + (rows - 1) * G
    return cell, (W - grid_w) // 2, (H - grid_h) // 2


def _pHYs(path):
    """The PNG resolution chunk, read without Pillow: (px_per_m, py_per_m, unit)."""
    import struct
    b = path.read_bytes()
    i = 8
    while i < len(b):
        ln, typ = struct.unpack(">I4s", b[i:i + 8])
        if typ == b"pHYs":
            return struct.unpack(">IIB", b[i + 8:i + 17])
        if typ == b"IDAT":
            break
        i += 12 + ln
    return None


NINE = [(f"{p:02d}-k", 1, p) for p in range(1, 10)]
EIGHTEEN = NINE + [(f"{p + 9:02d}-k", 2, p) for p in range(1, 10)]


# --- 1. the page is exactly A4 @ 300 DPI --------------------------------------

def test_the_page_is_exactly_franks_a4_pixel_size(tmp_path):
    r = _run(tmp_path, _cfg(), _entries(NINE))
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1)) as im:
        assert im.size == (FRANK_W, FRANK_H)


# --- 2. the DPI is written INTO the file (what makes "print at 100%" work) ----

def test_the_saved_png_carries_the_dpi_metadata(tmp_path):
    r = _run(tmp_path, _cfg(), _entries(NINE))
    assert r.returncode == 0, r.stderr
    p = _sheet(tmp_path, 1)
    with Image.open(p) as im:
        dpi = im.info["dpi"]
    # PNG stores resolution as INTEGER pixels-per-metre, so 300 dpi round-trips as
    # 11811 px/m == 299.9994 dpi. Asserting the float `== (300, 300)` would fail
    # for a file that is correct; the integer chunk is the exact contract, and it
    # is byte-identical to frank's committed sheet (measured 2026-08-03).
    assert tuple(round(d) for d in dpi) == (300, 300), dpi
    assert _pHYs(p) == (11811, 11811, 1)


# --- 3. cell size + CENTRED grid, identical to frank's hardcoded 3x3 ----------

def test_cell_size_and_centred_offsets_reproduce_franks_numbers(tmp_path):
    cell, off_x, off_y = _frank_geometry()
    assert (cell, off_x, off_y) == (746, 61, 575)          # frank's actual numbers
    assert _generalised(3, 3) == (cell, off_x, off_y)      # the generalised algebra

    entries = _entries(NINE)
    r = _run(tmp_path, _cfg(), entries)
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1)) as im:
        px = im.convert("RGB").load()
        for i, e in enumerate(entries):
            row, col = divmod(e["pos"] - 1, 3)
            x, y = off_x + col * (cell + FRANK_GUTTER), off_y + row * (cell + FRANK_GUTTER)
            assert px[x, y] == _colour(i), f"{e['key']} not at ({x},{y})"
            assert px[x, y + cell - 1] == _colour(i)       # the cell is `cell` tall
            assert px[x + cell - 1, y] == _colour(i)       # ... and `cell` wide
        # the grid really is centred: the gutter margin left of column 0 is white
        assert px[off_x - 1, off_y] == WHITE
        assert px[off_x, off_y - 1] == WHITE


# --- 4. `pos` maps left->right, top->bottom ----------------------------------

def test_pos_maps_left_to_right_then_top_to_bottom(tmp_path):
    cell, off_x, off_y = _frank_geometry()
    # one sticker at pos 3 -> row 0, col 2 (divmod(2, 3)); pos 4 -> row 1, col 0.
    entries = _entries([("a", 1, 3), ("b", 1, 4)])
    r = _run(tmp_path, _cfg(), entries)
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1)) as im:
        px = im.convert("RGB").load()
        assert px[off_x + 2 * (cell + FRANK_GUTTER), off_y] == _colour(0)
        assert px[off_x, off_y + 1 * (cell + FRANK_GUTTER)] == _colour(1)
        assert px[off_x, off_y] == WHITE                    # pos 1 was never filled
        assert px[off_x + cell + FRANK_GUTTER, off_y] == WHITE   # nor pos 2


# --- 5. a missing image fails LOUDLY, never as a blank cell ------------------

def test_a_missing_image_fails_loudly_naming_the_path(tmp_path):
    entries = _entries(NINE)
    cfg_path = _blog(tmp_path, _cfg(), entries)
    missing = tmp_path / "images" / "sticker-05-k.png"
    missing.unlink()
    r = subprocess.run([sys.executable, SCRIPT, "--config", str(cfg_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert str(missing) in (r.stderr + r.stdout)
    # a half-built sheet with a silent hole is worse than no sheet
    assert not _sheet(tmp_path, 1).exists()


# --- 6. one file per declared sheet, prefix from CONFIG (never "frank-") -----

def test_two_sheets_are_produced_with_the_config_prefix(tmp_path):
    r = _run(tmp_path, _cfg(), _entries(EIGHTEEN))
    assert r.returncode == 0, r.stderr
    assert _sheet(tmp_path, 1).is_file()
    assert _sheet(tmp_path, 2).is_file()
    assert not _sheet(tmp_path, 3).exists()


def test_the_prefix_defaults_to_the_slugged_project_name(tmp_path):
    """`project.name: "Frank"` -> `frank-stickers-A4-sheet1.png`, frank's exact name."""
    r = _run(tmp_path, _cfg(), _entries(NINE))
    assert r.returncode == 0, r.stderr
    assert _sheet(tmp_path, 1, prefix="frank-stickers").is_file()


def test_an_explicit_sheets_prefix_wins_and_nothing_says_frank(tmp_path):
    cfg = _cfg(sheets_prefix="acme-labels")
    cfg["project"]["name"] = "Acme Blog"
    r = _run(tmp_path, cfg, _entries(NINE))
    assert r.returncode == 0, r.stderr
    assert _sheet(tmp_path, 1, prefix="acme-labels").is_file()
    produced = sorted(p.name for p in (tmp_path / "sheets").iterdir())
    assert produced == ["acme-labels-A4-sheet1.png"]
    assert not any("frank" in n for n in produced)


def test_a_slugged_multiword_project_name(tmp_path):
    cfg = _cfg()
    cfg["project"]["name"] = "Gondor Blog"
    r = _run(tmp_path, cfg, _entries(NINE))
    assert r.returncode == 0, r.stderr
    assert _sheet(tmp_path, 1, prefix="gondor-blog-stickers").is_file()


# --- 7. entries lacking sheet/pos are SKIPPED, not misplaced ----------------

def test_entries_without_sheet_or_pos_are_skipped(tmp_path):
    cell, off_x, off_y = _frank_geometry()
    entries = _entries([("placed", 1, 1)])
    entries.append({"key": "unplaced", "output": "images/sticker-unplaced.png",
                    "composition": {"order": "sticker", "modifiers": {}, "scene": "S"}})
    entries.append({"key": "sheet-only", "output": "images/sticker-sheet-only.png",
                    "sheet": 1,
                    "composition": {"order": "sticker", "modifiers": {}, "scene": "S"}})
    r = _run(tmp_path, _cfg(), entries)
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1)) as im:
        px = im.convert("RGB").load()
        assert px[off_x, off_y] == _colour(0)               # the placed one
        for pos in range(2, 10):
            row, col = divmod(pos - 1, 3)
            x, y = off_x + col * (cell + FRANK_GUTTER), off_y + row * (cell + FRANK_GUTTER)
            assert px[x, y] == WHITE, f"pos {pos} is not empty"


# --- 8. page dimensions are DERIVED from size + dpi, never configured -------

def test_page_dimensions_are_derived_from_size_and_dpi(tmp_path):
    """`round(mm / 25.4 * dpi)`. NOT a linear scale: at 600 dpi the A4 WIDTH is
    4961, not 2*2480 — `round(210/25.4*600) == 4961` while
    `round(210/25.4*300) == 2480`. The derivation is the contract; "it doubles"
    is not."""
    assert round(210 / 25.4 * 300) == FRANK_W
    assert round(297 / 25.4 * 300) == FRANK_H
    r = _run(tmp_path, _cfg(sheet={"dpi": 600}), _entries(NINE))
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1)) as im:
        assert im.size == (4961, 7016)
    assert (4961, 7016) == (round(210 / 25.4 * 600), round(297 / 25.4 * 600))


def test_letter_is_a_different_page(tmp_path):
    r = _run(tmp_path, _cfg(sheet={"size": "letter"}), _entries(NINE))
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1, paper="LETTER")) as im:
        assert im.size == (2550, 3300)      # 215.9 x 279.4 mm @ 300 dpi, exactly


# --- 9. an unrecognised size is a HARD error (validate_config won't catch it) -

def test_an_unrecognised_size_exits_non_zero_naming_it_and_the_known_sizes(tmp_path):
    r = _run(tmp_path, _cfg(sheet={"size": "a3"}), _entries(NINE))
    assert r.returncode != 0
    err = r.stderr + r.stdout
    assert "a3" in err
    assert "a4" in err and "letter" in err
    assert not (tmp_path / "sheets").exists()


# --- 10. `grid` genuinely works ---------------------------------------------

def test_grid_2x4_lays_out_two_columns_and_four_rows(tmp_path):
    cols, rows = 2, 4
    cell, off_x, off_y = _generalised(cols, rows)
    assert (cell, off_x, off_y) == (802, 408, 60)
    entries = _entries([(f"{p:02d}-k", 1, p) for p in range(1, cols * rows + 1)])
    r = _run(tmp_path, _cfg(sheet={"grid": [cols, rows]}), entries)
    assert r.returncode == 0, r.stderr
    with Image.open(_sheet(tmp_path, 1)) as im:
        assert im.size == (FRANK_W, FRANK_H)
        px = im.convert("RGB").load()
        for i, e in enumerate(entries):
            row, col = divmod(e["pos"] - 1, cols)
            x, y = off_x + col * (cell + FRANK_GUTTER), off_y + row * (cell + FRANK_GUTTER)
            assert px[x, y] == _colour(i), f"pos {e['pos']} not at ({x},{y})"


def test_pos_beyond_the_grid_is_rejected(tmp_path):
    """With `grid: [2, 4]` there is no cell 9. frank's `range(1, 10)` would have
    silently dropped it; a sticker missing from a PRINTED sheet must be loud."""
    entries = _entries([("a", 1, 1), ("nine", 1, 9)])
    r = _run(tmp_path, _cfg(sheet={"grid": [2, 4]}), entries)
    assert r.returncode != 0
    err = r.stderr + r.stdout
    assert "nine" in err and "9" in err and "8" in err
    assert not _sheet(tmp_path, 1).exists()


def test_a_grid_that_cannot_be_laid_out_is_refused(tmp_path):
    """The same judgement as `_contact_sheet(cols=0)` (phase-2 review fix 6): a
    computed grid dimension of zero, or a gutter that leaves no room, is a bug —
    and a plausible-looking sheet would hide it."""
    entries = _entries([("a", 1, 1)])
    r = _run(tmp_path, _cfg(sheet={"grid": [0, 3]}), entries)
    assert r.returncode != 0 and "grid" in (r.stderr + r.stdout)
    r = _run(tmp_path, _cfg(sheet={"gutter": 900}), entries)
    assert r.returncode != 0 and "gutter" in (r.stderr + r.stdout)
    assert not (tmp_path / "sheets").exists()


def test_grid_3x3_is_numerically_identical_to_franks_hardcoded_three(tmp_path):
    """The equality that IS the regression test: an EXPLICIT `grid: [3, 3]` and
    the default must both land on frank's cell/offsets, byte for byte."""
    entries = _entries(NINE)
    a = tmp_path / "default"
    a.mkdir()
    b = tmp_path / "explicit"
    b.mkdir()
    assert _run(a, _cfg(), entries).returncode == 0
    assert _run(b, _cfg(sheet={"grid": [3, 3]}), entries).returncode == 0
    assert _sheet(a, 1).read_bytes() == _sheet(b, 1).read_bytes()
