"""`generate-stickers.py` — frank's CLI over the shared engine (stickers P4.T2/T4).

Preserving frank's flags is part of "no behavioral changes": his README documents
`--list`, `--only`, `--out`, `--dry-run`, and the operator's runbook and muscle
memory have to survive the port. So this is a SHIM — it resolves
`features.stickers.prompts_file` and delegates to the sibling
`generate-images.py`, adding only the two things the engine cannot supply:

- the sticker-shaped `--list` (sheet/pos/description, not just keys);
- the run-level contact sheet across the KEYS generated (the engine's is per-key
  across a key's variants and fires only on `--count > 1`, so for frank's
  one-image-per-key runs it never appears at all — journal
  `p2-decision6-insufficient-for-frank-sheet`, spec Decision 6 correction).

Two contracts inherited from phase 2 that these tests pin from the shim side:

- `--out` is CWD-relative in the engine, like `--reference`, so the shim passes an
  ABSOLUTE path resolved against the CONFIG ROOT. Every test here runs the shim
  from a directory outside the blog, which is what makes that observable.
- the `--out` filename is the BASENAME of the entry's `output:` (spec §5a), which
  for stickers is exactly frank's `sticker-<key>.png` — the name of the master his
  README says to copy over. No renaming layer in the shim; if one is ever needed,
  §5a is wrong.

The scripts are copied into a `scripts/` directory per test rather than run from
the repo tree, because `generate-stickers.py` imports `generate-images.py` as a
SIBLING — which is what they are once `bootstrap-render.sh` materializes them into
`<site_dir>/scripts/`. Running them from their template locations would prove
nothing about the shape they ship in.
"""

import importlib.util
import os
import shutil
import subprocess
import sys

import yaml
from PIL import Image

from compose import compose   # tools/ is on sys.path (tests/conftest.py)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENGINE_DIR = os.path.join(_ROOT, "templates/hugo-hextra/scripts")
SHIM_SRC = os.path.join(_ROOT, "templates/features/stickers/scripts/generate-stickers.py")

STK_DIR = "blog/_private/stickers"
POOL = ".reference-pool/building"

BASE = "BASE CHARACTER: Frank is a chibi-proportioned green Frankenstein monster."
ATMO = "ATMOSPHERE: a die-cut character STICKER on a FLAT PURE-WHITE background."
REFG = "REFERENCE GUIDANCE: the attached images are ANCHORS, not subjects to render."
PINS = "FACE PINS: " + "identity lock prose that is deliberately long. " * 8
BORDER = "BORDER SPEC: white bleed plus a dark-green #1b4332 keyline die-cut edge."

CURATED = b"\x89PNG\r\n\x1a\nHAND-PICKED-MASTER-DO-NOT-TOUCH"

STICKER_ORDER = ["sticker_base_character", "sticker_atmosphere",
                 "sticker_reference_guidance", "sticker_face_pins",
                 "clothing", "sticker_mood", "scene", "sticker_border_spec"]


def _cfg(**stk) -> dict:
    """A v7 config whose sticker surface is exactly the shape phase 5 must author."""
    stickers = {
        "enabled": True,
        "prompts_file": f"{STK_DIR}/stickers.yaml",
        "images_dir": f"{STK_DIR}/images",
        "sheets_dir": f"{STK_DIR}/sheets",
        "sheet": {"size": "a4", "dpi": 300, "grid": [3, 3], "gutter": 60},
    }
    stickers.update(stk)
    return {
        "version": 7,
        "project": {"name": "Frank"},
        "series": [],
        "voice": "v",
        "image": {
            "prompts_file": "prompt_for_images.yaml",
            "model": "primary-m",
            "composition_orders": {"hero": ["scene"], "sticker": list(STICKER_ORDER)},
            "layers": {
                "sticker_base_character": BASE,
                "sticker_atmosphere": ATMO,
                "sticker_reference_guidance": REFG,
                "sticker_face_pins": PINS,
                "sticker_border_spec": BORDER,
                # the frame Decision 1 exists for, on its OWN layer (never `mood`)
                "sticker_mood": {"_template": "Frank's expression: {}."},
                # frank's sticker clothing is per-entry free-form prose: an empty
                # table means every value misses and passes through unframed.
                "clothing": {},
            },
        },
        "features": {"stickers": stickers},
    }


def _sticker(i: int, anchor=True) -> dict:
    key = f"{i:02d}-k"
    refs = {"primary": f"{POOL}/reference-building.png",
            "clothing": [f"{STK_DIR}/images/sticker-09-server-blade.png",
                         f"{STK_DIR}/images/sticker-20-tinkering.png"]}
    if anchor:
        refs["clothing"] = refs["clothing"] + [f"{POOL}/reference/frank-lab-coat-shirt.png"]
    return {
        "key": key,
        "description": f"Frank does thing {i}",
        "output": f"{STK_DIR}/images/sticker-{key}.png",
        "aspect_ratio": "1:1",
        "sheet": 1 if i <= 9 else 2,
        "pos": i if i <= 9 else i - 9,
        "composition": {
            # NOT `order: sticker` — `order_tokens()` only accepts the
            # `composition_orders[name]` spelling or an inline list.
            "order": "composition_orders[sticker]",
            "modifiers": {"sticker_mood": f"mood {i} — a half-smile",
                          "clothing": f"Frank wears outfit {i}."},
            "scene": f"SCENE {i}: Frank does thing {i}.",
            "reference_images": refs,
        },
    }


def _expected_prompt(entry: dict, cfg: dict) -> str:
    comp = entry["composition"]
    sel = dict(comp["modifiers"])
    sel["prompt"] = comp["scene"]
    return compose(STICKER_ORDER, cfg["image"]["layers"], sel)


def _blog(tmp_path, cfg=None, entries=None, masters=False):
    cfg = cfg if cfg is not None else _cfg()
    entries = entries if entries is not None else [_sticker(1), _sticker(2)]
    blog = tmp_path / "blog-root"
    blog.mkdir(exist_ok=True)
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (blog / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": []}))

    stk = (cfg.get("features") or {}).get("stickers") or {}
    if stk.get("prompts_file"):
        p = blog / stk["prompts_file"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump({"images": entries}))
    idir = blog / STK_DIR / "images"
    idir.mkdir(parents=True, exist_ok=True)
    # the two style anchors ARE sticker images (the set references its own output)
    for name in ("sticker-09-server-blade.png", "sticker-20-tinkering.png"):
        Image.new("RGB", (8, 8), (10, 120, 60)).save(idir / name)
    pool = blog / POOL
    (pool / "reference").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (200, 30, 30)).save(pool / "reference-building.png")
    Image.new("RGB", (8, 8), (30, 30, 200)).save(pool / "reference" / "frank-lab-coat-shirt.png")
    if masters:
        for e in entries:
            (blog / e["output"]).write_bytes(CURATED)

    sdir = blog / "scripts"
    sdir.mkdir(exist_ok=True)
    for n in ("generate-images.py", "compose.py"):
        shutil.copy(os.path.join(ENGINE_DIR, n), sdir / n)
    shutil.copy(SHIM_SRC, sdir / "generate-stickers.py")
    return blog


def _run(blog, *args, cwd=None):
    """Run the shim from OUTSIDE the blog: `--out` must resolve against the config
    root, not the process CWD."""
    elsewhere = blog.parent / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    env = dict(os.environ, BLOG_CRAFT_TEST_MODE="1")
    return subprocess.run(
        [sys.executable, str(blog / "scripts" / "generate-stickers.py"),
         "--config", str(blog / ".blog-craft.yaml"), *args],
        capture_output=True, text=True, env=env, cwd=str(cwd or elsewhere))


# --- 1. --list is frank's list: key, sheet/pos, description -------------------

def test_list_prints_keys_with_sheet_pos_and_description(tmp_path):
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2), _sticker(12)])
    r = _run(blog, "--list")
    assert r.returncode == 0, r.stderr
    assert "01-k" in r.stdout and "sheet1/pos1" in r.stdout
    assert "02-k" in r.stdout and "sheet1/pos2" in r.stdout
    assert "12-k" in r.stdout and "sheet2/pos3" in r.stdout
    assert "Frank does thing 1" in r.stdout
    # the sticker prompts file, NOT image.prompts_file (which is empty here)
    assert r.stdout.strip(), "listed nothing — did it read image.prompts_file?"


def test_list_reads_the_sticker_prompts_file_not_the_cover_one(tmp_path):
    cfg = _cfg()
    blog = _blog(tmp_path, cfg=cfg, entries=[_sticker(1)])
    (blog / "prompt_for_images.yaml").write_text(
        yaml.safe_dump({"images": [{"key": "a-cover-key", "output": "static/images/cover.png"}]}))
    r = _run(blog, "--list")
    assert r.returncode == 0, r.stderr
    assert "01-k" in r.stdout
    assert "a-cover-key" not in r.stdout


# --- 2/3. the default run is NON-DESTRUCTIVE: regen/, never `output:` ---------

def test_the_default_run_writes_regen_and_leaves_every_master_untouched(tmp_path):
    entries = [_sticker(1), _sticker(2)]
    blog = _blog(tmp_path, entries=entries, masters=True)
    before = {e["key"]: (blog / e["output"]).stat().st_mtime_ns for e in entries}
    r = _run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    for e in entries:
        # spec §5a: the basename of `output:`, i.e. frank's own regen filename
        assert (blog / "regen" / f"sticker-{e['key']}.png").is_file()
        assert not (blog / "regen" / f"{e['key']}.png").exists()
        master = blog / e["output"]
        assert master.read_bytes() == CURATED
        assert master.stat().st_mtime_ns == before[e["key"]]


def test_regen_resolves_against_the_config_root_not_the_cwd(tmp_path):
    blog = _blog(tmp_path, entries=[_sticker(1)])
    r = _run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (blog / "regen" / "sticker-01-k.png").is_file()
    assert not (blog.parent / "elsewhere" / "regen").exists()


def test_only_generates_just_those_keys(tmp_path):
    entries = [_sticker(1), _sticker(2), _sticker(3)]
    blog = _blog(tmp_path, entries=entries)
    r = _run(blog, "--only", "01-k,03-k")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (blog / "regen" / "sticker-01-k.png").is_file()
    assert (blog / "regen" / "sticker-03-k.png").is_file()
    assert not (blog / "regen" / "sticker-02-k.png").exists()


def test_an_explicit_out_dir_is_honoured(tmp_path):
    blog = _blog(tmp_path, entries=[_sticker(1)])
    r = _run(blog, "--out", "candidates")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (blog / "candidates" / "sticker-01-k.png").is_file()
    assert not (blog / "regen").exists()


# --- 4. --dry-run prints the FULL prompt and the resolved refs, no API call ---

def test_dry_run_prints_the_untruncated_prompt_and_the_resolved_refs(tmp_path):
    cfg = _cfg()
    e1 = _sticker(1)
    blog = _blog(tmp_path, cfg=cfg, entries=[e1])
    expected = _expected_prompt(e1, cfg)
    assert len(expected) > 300, "the fixture must be long enough to catch truncation"

    r = _run(blog, "--dry-run")
    assert r.returncode == 0, r.stderr
    # frank's own --dry-run cut the prompt at 300 chars (generate-stickers.py:101),
    # which is why his goldens had to come from compose_prompt() instead. The shim
    # fixes that deliberately: the whole prompt, verbatim.
    assert expected in r.stdout, "the composed prompt is truncated or reordered"
    assert BORDER in r.stdout            # the LAST section, well past char 300
    assert "Frank's expression: mood 1 — a half-smile." in r.stdout
    # the resolved reference FILENAMES, primary first
    at = [r.stdout.index(n) for n in ("reference-building.png",
                                      "sticker-09-server-blade.png",
                                      "sticker-20-tinkering.png",
                                      "frank-lab-coat-shirt.png")]
    assert at == sorted(at), "references are out of frank's order"
    # ... and nothing was generated
    assert not (blog / "regen").exists()


def test_dry_run_covers_every_selected_key(tmp_path):
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2)])
    r = _run(blog, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "SCENE 1: Frank does thing 1." in r.stdout
    assert "SCENE 2: Frank does thing 2." in r.stdout


# --- 5. an unknown key names the valid ones ----------------------------------

def test_an_unknown_key_exits_non_zero_naming_the_valid_keys(tmp_path):
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2)])
    r = _run(blog, "--only", "01-k,nope")
    assert r.returncode != 0
    err = r.stderr + r.stdout
    assert "nope" in err
    assert "01-k" in err and "02-k" in err
    assert not (blog / "regen").exists()


# --- 6. the capability gate: absent AND disabled both refuse -----------------

def test_features_stickers_disabled_exits_non_zero_pointing_at_the_knob(tmp_path):
    """After `migrations/006_to_007.py`, EVERY updated blog carries
    `features.stickers: {enabled: false}` — so `disabled` is the common shape."""
    cfg = _cfg(enabled=False)
    blog = _blog(tmp_path, cfg=cfg, entries=[_sticker(1)])
    for args in ([], ["--list"], ["--dry-run"]):
        r = _run(blog, *args)
        assert r.returncode != 0, args
        assert "features.stickers.enabled" in (r.stderr + r.stdout), args
    assert not (blog / "regen").exists()


def test_features_stickers_absent_exits_non_zero_pointing_at_the_knob(tmp_path):
    """The legacy shape: a config that predates the v7 rung has no block at all."""
    cfg = _cfg()
    cfg["features"] = {}
    blog = _blog(tmp_path, cfg=cfg, entries=[_sticker(1)])
    r = _run(blog)
    assert r.returncode != 0
    assert "features.stickers" in (r.stderr + r.stdout)


# --- P4.T4: the RUN-LEVEL contact sheet the engine cannot produce -------------
#
# The engine's sheet is per-KEY across that key's variants and fires only on
# `--count > 1`. frank's is per-RUN across the keys generated and fires whenever >=2
# succeeded (generate-stickers.py:141-144). frank generates ONE image per key, so
# `count == 1` and the engine's sheet never appears at all — geometry parameters
# (Decision 6) are necessary but not sufficient, so the shim owns this artifact.
#
# Its LAYOUT is an ACCEPTED DIVERGENCE, not a reproduction. frank's helper
# `frank/scripts/lib/contact_sheet.py` was deleted by his own blog-craft cutover
# (bd0415e6) and used a different algorithm — aspect-preserving thumbnails, the
# label in a strip along the BOTTOM, background-coloured trailing cells — where
# `_contact_sheet` draws the label at the TOP of a fixed tile. What is reproduced is
# frank's COLUMN COUNT and TILE WIDTH; the pixels differ, phase 8 declares it, and
# nothing regresses because frank's version cannot run.

def _engine_mod():
    spec = importlib.util.spec_from_file_location(
        "generate_images_ref", os.path.join(ENGINE_DIR, "generate-images.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_a_run_of_two_or_more_keys_writes_the_run_level_contact_sheet(tmp_path):
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2)])
    r = _run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    sheet = blog / "regen" / "contact-sheet.png"
    assert sheet.is_file()
    with Image.open(sheet) as im:
        assert im.size == (2 * 420, 260)   # cols clamps to the image count


def test_the_sheet_is_franks_five_columns_at_tile_width_420(tmp_path):
    entries = [_sticker(i) for i in range(1, 7)]
    blog = _blog(tmp_path, entries=entries)
    r = _run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    with Image.open(blog / "regen" / "contact-sheet.png") as im:
        assert im.size == (5 * 420, 2 * 260)   # 6 keys, 5 wide -> 2 rows


def test_the_tiles_are_the_generated_KEYS_labelled_by_key(tmp_path):
    """One tile per KEY (not per variant of one key), labelled with the key, in the
    order the run generated them. Pinned by byte-equality against a sheet built
    directly from the same files — which fixes the labels and the order, not just
    the geometry."""
    entries = [_sticker(1), _sticker(2), _sticker(3)]
    blog = _blog(tmp_path, entries=entries)
    r = _run(blog)
    assert r.returncode == 0, r.stdout + r.stderr

    gi = _engine_mod()
    expected = tmp_path / "expected.png"
    images = [(e["key"], Image.open(blog / "regen" / f"sticker-{e['key']}.png"))
              for e in entries]
    gi._contact_sheet(images, expected, cols=5, tile_width=420)
    assert (blog / "regen" / "contact-sheet.png").read_bytes() == expected.read_bytes()


def test_a_single_key_run_writes_no_contact_sheet(tmp_path):
    """frank's threshold is >=2 (generate-stickers.py:141): one candidate needs no
    grid to compare it against."""
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2)])
    r = _run(blog, "--only", "01-k")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (blog / "regen" / "sticker-01-k.png").is_file()
    assert not (blog / "regen" / "contact-sheet.png").exists()


def test_the_engines_per_key_sheet_is_untouched(tmp_path):
    """`--count` is 1 here, so the engine's own curation sheet must NOT appear —
    the shim adds an artifact, it does not move or duplicate the engine's."""
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2)])
    r = _run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    for key in ("01-k", "02-k"):
        adir = blog / ".regen-archive" / key
        assert list(adir.glob(f"{key}-*.png")), "the archive snapshot is still written"
        assert not (adir / "contact-sheet.png").exists()
    # ... and the run-level one is the only contact sheet anywhere under --out
    assert [p.name for p in (blog / "regen").rglob("contact-sheet.png")] == \
        ["contact-sheet.png"]


def test_a_stale_regen_file_is_not_counted_as_generated(tmp_path):
    """frank's `done` list is what SUCCEEDED THIS RUN. A leftover candidate from an
    earlier run must not silently pad the sheet — with `--only 01-k` there is one
    success, so there is no sheet, even though regen/ holds two files."""
    blog = _blog(tmp_path, entries=[_sticker(1), _sticker(2)])
    stale = blog / "regen" / "sticker-02-k.png"
    stale.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (90, 90, 90)).save(stale)
    os.utime(stale, (1_000_000, 1_000_000))
    r = _run(blog, "--only", "01-k")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (blog / "regen" / "contact-sheet.png").exists()
    assert stale.stat().st_mtime_ns == 1_000_000 * 10**9
