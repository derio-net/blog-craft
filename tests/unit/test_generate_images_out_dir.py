"""`--out <dir>`: a non-destructive generate mode (stickers P2.T2, stk-2).

WHY this exists — it is a data-loss guard, not a convenience flag. The engine
writes the last variant straight to the entry's `output:` path
(`generate-images.py`, `out.write_bytes(variants[-1][1].read_bytes())`). frank's
sticker workflow is the exact opposite: generate candidates into `regen/`,
eyeball them, then copy a winner over the master BY HAND
(`frank/blog/_private/frank-stickers/README.md:28-29`;
`generate-stickers.py:71,89` only ever writes under `--out`). Porting the 18
stickers as ordinary entries without `--out` would overwrite the curated sticker
master on every regeneration — silently destroying the hand-picked artwork the
whole print workflow exists to protect.

`test_pre_existing_output_is_byte_unchanged` is the assertion that pins that.
Do not weaken it.

`BLOG_CRAFT_TEST_MODE=1` is fine here: these exercise the WRITE path, not the
API. The one test that needs distinct bytes per variant injects a fake
`google.genai` instead (see test_generate_images_fallback.py for the mechanics).
"""

import importlib.util
import os
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(_ROOT, "templates/hugo-hextra/scripts/generate-images.py")

CFG = {
    "version": 5, "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {"prompts_file": "prompt_for_images.yaml", "model": "primary-m",
              "composition_orders": {"hero": ["scene"]}, "layers": {}},
}
E1 = {"key": "k-01", "output": "static/images/k-01.png",
      "composition": {"modifiers": {}, "scene": "SCENE ONE", "reference_images": {}}}
E2 = {"key": "k-02", "output": "static/images/k-02.png",
      "composition": {"modifiers": {}, "scene": "SCENE TWO", "reference_images": {}}}

CURATED = b"\x89PNG\r\n\x1a\nHAND-PICKED-MASTER-DO-NOT-TOUCH"


def _blog(tmp_path, entries=(E1,), cfg=CFG):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": list(entries)}))
    return tmp_path / ".blog-craft.yaml"


def _run(tmp_path, *args, entries=(E1,), cfg=CFG):
    cfg_path = _blog(tmp_path, entries, cfg)
    env = dict(os.environ, BLOG_CRAFT_TEST_MODE="1")
    return subprocess.run([sys.executable, GEN, "--config", str(cfg_path), *args],
                          capture_output=True, text=True, env=env)


# --- 1. --out DIR creates DIR/<key>.png ---

def test_out_dir_receives_the_image(tmp_path):
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d))
    assert r.returncode == 0, r.stderr
    assert (d / "k-01.png").is_file()


# --- 2. THE GUARD: a pre-existing `output:` is byte-UNCHANGED ---

def test_pre_existing_output_is_byte_unchanged(tmp_path):
    master = tmp_path / "static" / "images" / "k-01.png"
    master.parent.mkdir(parents=True)
    master.write_bytes(CURATED)
    before = master.stat().st_mtime_ns

    r = _run(tmp_path, "--out", str(tmp_path / "regen"))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "regen" / "k-01.png").is_file()      # generation did happen
    assert master.read_bytes() == CURATED                   # ... and the master is intact
    assert master.stat().st_mtime_ns == before              # not even rewritten


# --- 3. with --out and no pre-existing output:, that path is never created ---

def test_out_dir_never_creates_the_output_path(tmp_path):
    r = _run(tmp_path, "--out", str(tmp_path / "regen"))
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "static" / "images" / "k-01.png").exists()
    assert not (tmp_path / "static").exists()   # not even the parent dirs


# --- 4. WITHOUT --out, `output:` is written exactly as today (regression) ---

def test_without_out_dir_output_is_written_as_today(tmp_path):
    master = tmp_path / "static" / "images" / "k-01.png"
    master.parent.mkdir(parents=True)
    master.write_bytes(CURATED)
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert master.read_bytes() != CURATED, "default mode still overwrites output:"
    assert master.read_bytes().startswith(b"\x89PNG")


# --- --dry-run must name the destination it would ACTUALLY write ---

def test_dry_run_reports_the_out_dir_not_the_output_path(tmp_path):
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), "--dry-run")
    assert r.returncode == 0, r.stderr
    assert str(d / "k-01.png") in r.stdout
    assert "static/images/k-01.png" not in r.stdout
    # ... and without --out the preview is unchanged
    r = _run(tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert str(tmp_path / "static" / "images" / "k-01.png") in r.stdout


# --- 5. --out combines with --only ---

def test_out_dir_combines_with_only(tmp_path):
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), "--only", "k-02", entries=(E1, E2))
    assert r.returncode == 0, r.stderr
    assert (d / "k-02.png").is_file()
    assert not (d / "k-01.png").exists()
    assert not (tmp_path / "static").exists()


# --- 5b. post_process is skipped: it targets the PUBLISHED asset ---

def test_out_dir_skips_post_process(tmp_path):
    """`post_process` derivatives are written next to / over the published
    asset, so running them on a candidate would clobber shipped files that
    --out promised not to touch."""
    # NB the target is absolute on purpose: `post_process` step targets are
    # resolved against the process CWD, not the blog root (unlike `output:`) —
    # pre-existing behavior, journaled, not this phase's to change.
    derived = tmp_path / "derived.png"
    e = dict(E1, post_process=[{"resize": {"size": 8, "target": str(derived)}}])
    r = _run(tmp_path, "--out", str(tmp_path / "regen"), entries=(e,))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "regen" / "k-01.png").is_file()
    assert not derived.exists()
    # ... and without --out it still runs (the regression half of the pair)
    r = _run(tmp_path, entries=(e,))
    assert r.returncode == 0, r.stderr
    assert derived.is_file()


# --- 6. --out with --count N>1: N variants in DIR, still no `output:` ---

def _fake_genai(payloads, calls):
    """`google.genai` stand-in yielding a DIFFERENT image per call, so N
    variants are genuinely N distinct files (TEST_MODE's fixed 1x1 PNG cannot
    show that — identical bytes collapse onto one archive sha)."""

    class _Kwargs:
        def __init__(self, **kw):
            self.kw = kw

    class _Part:
        def __init__(self, data):
            self.inline_data = SimpleNamespace(data=data)

    class _Models:
        def generate_content(self, *, model, contents, config=None):
            calls.append(model)
            return SimpleNamespace(parts=[_Part(payloads[len(calls) - 1])])

    class Client:
        def __init__(self, api_key=None):
            self.models = _Models()

    genai = ModuleType("google.genai")
    genai.Client = Client
    genai.types = SimpleNamespace(HttpOptions=_Kwargs, GenerateContentConfig=_Kwargs,
                                  ImageConfig=_Kwargs)
    return genai


def _png(color):
    from io import BytesIO

    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


def _install_fake(monkeypatch, payloads):
    calls = []
    genai = _fake_genai(payloads, calls)
    pkg = ModuleType("google")
    pkg.genai = genai
    monkeypatch.setitem(sys.modules, "google", pkg)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("BLOG_CRAFT_TEST_MODE", raising=False)
    return calls


def _mod():
    spec = importlib.util.spec_from_file_location("generate_images", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_out_dir_with_count_writes_every_variant_and_no_output(tmp_path, monkeypatch):
    payloads = [_png("red"), _png("green"), _png("blue")]
    calls = _install_fake(monkeypatch, payloads)

    master = tmp_path / "static" / "images" / "k-01.png"
    master.parent.mkdir(parents=True)
    master.write_bytes(CURATED)

    cfg_path = _blog(tmp_path)
    m = _mod()
    d = tmp_path / "regen"
    assert m.main(["--config", str(cfg_path), "--out", str(d), "--count", "3"]) == 0

    assert len(calls) == 3
    assert master.read_bytes() == CURATED                  # the guard, under --count too
    # every variant is visible in the out dir, and the bare name is the last one
    files = sorted(p.name for p in d.glob("*.png"))
    assert (d / "k-01.png").read_bytes() == payloads[-1]
    variants = [n for n in files if n != "k-01.png" and n.startswith("k-01-")]
    assert len(variants) == 3, files
    assert {(d / n).read_bytes() for n in variants} == set(payloads)


# --- --count larger than curation.archive_cap: the FIFO prunes mid-run ---

CFG_CAP1 = {**CFG, "image": {**CFG["image"], "curation": {"archive_cap": 1}}}


def test_count_above_archive_cap_warns_instead_of_crashing(tmp_path, monkeypatch):
    """`write_archive_entry` applies the FIFO cap on EVERY call, so while a
    --count run is still in flight it deletes the earlier variants of that same
    run. Both the contact sheet and the --out copy read every variant, so the
    pruned ones must be dropped with a warning, not blow the run up."""
    payloads = [_png("red"), _png("green"), _png("blue")]
    _install_fake(monkeypatch, payloads)
    cfg_path = _blog(tmp_path, cfg=CFG_CAP1)
    m = _mod()
    d = tmp_path / "regen"
    assert m.main(["--config", str(cfg_path), "--out", str(d), "--count", "3"]) == 0
    assert (d / "k-01.png").read_bytes() == payloads[-1]    # newest survives the FIFO
    assert not (tmp_path / "static").exists()


def test_count_above_archive_cap_without_out_dir(tmp_path, monkeypatch, capsys):
    """The same pruning already existed on the default path (the contact sheet
    opens every variant), so pin it there too."""
    payloads = [_png("red"), _png("green"), _png("blue")]
    _install_fake(monkeypatch, payloads)
    cfg_path = _blog(tmp_path, cfg=CFG_CAP1)
    m = _mod()
    assert m.main(["--config", str(cfg_path), "--count", "3"]) == 0
    assert (tmp_path / "static" / "images" / "k-01.png").read_bytes() == payloads[-1]
    assert "archive_cap" in capsys.readouterr().err


# --- archives are unaffected by --out ---

def test_archive_entries_still_land_in_regen_archive(tmp_path):
    r = _run(tmp_path, "--out", str(tmp_path / "regen"))
    assert r.returncode == 0, r.stderr
    adir = tmp_path / ".regen-archive" / "k-01"
    assert list(adir.glob("k-01-*.png")), "archive snapshot still written"
    assert list(adir.glob("k-01-*.txt")), "archive sidecar still written"
