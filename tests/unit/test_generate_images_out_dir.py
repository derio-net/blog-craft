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
from pathlib import Path
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


def _run(tmp_path, *args, entries=(E1,), cfg=CFG, cwd=None):
    cfg_path = _blog(tmp_path, entries, cfg)
    env = dict(os.environ, BLOG_CRAFT_TEST_MODE="1")
    return subprocess.run([sys.executable, GEN, "--config", str(cfg_path), *args],
                          capture_output=True, text=True, env=env,
                          cwd=str(cwd) if cwd else None)


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


# --- 7. --out combines with --reference (the master override) ---

def test_out_dir_combines_with_reference(tmp_path):
    """`--reference` overrides the master for every entry; under `--out` it must
    still reach the generation path (the sidecar is the observable proof, since
    TEST_MODE never opens the file) and still not write `output:`."""
    master = tmp_path / "static" / "images" / "k-01.png"
    master.parent.mkdir(parents=True)
    master.write_bytes(CURATED)
    ref = tmp_path / "hand-picked-ref.png"
    ref.write_bytes(CURATED)

    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), "--reference", str(ref))
    assert r.returncode == 0, r.stderr
    assert (d / "k-01.png").is_file()
    assert master.read_bytes() == CURATED                       # the guard holds
    sidecar = next((tmp_path / ".regen-archive" / "k-01").glob("k-01-*.txt")).read_text()
    assert f"reference: {ref}" in sidecar                       # the override was used


# --- 8. --out does NOT relocate the per-key contact sheet ---

CONTACT = ".regen-archive/<key>/contact-sheet.png"


def test_out_dir_does_not_relocate_the_contact_sheet(tmp_path, monkeypatch):
    """The engine's curation sheet is per-KEY, under `.regen-archive/<key>/`, and
    `--out` does not move it — deliberately, because it is a per-key artifact and
    frank's is per-RUN. Phase 4's `generate-stickers.py` shim is built on exactly
    this non-movement (it calls `_contact_sheet` itself for the run-level sheet),
    so the placement is a contract, not an accident."""
    payloads = [_png("red"), _png("green")]
    _install_fake(monkeypatch, payloads)
    cfg_path = _blog(tmp_path)
    m = _mod()
    d = tmp_path / "regen"
    assert m.main(["--config", str(cfg_path), "--out", str(d), "--count", "2"]) == 0

    assert (tmp_path / ".regen-archive" / "k-01" / "contact-sheet.png").is_file()
    assert not (d / "contact-sheet.png").exists()
    assert list(d.rglob("contact-sheet.png")) == [], "no sheet anywhere under --out"


# --- 9. the FILENAME contract (spec §5a): basename of `output:`, key-prefixed on
#        a collision within the SELECTED set ---

STK_A = {"key": "coffee", "output": "static/stickers/sticker-coffee.png",
         "composition": {"modifiers": {}, "scene": "COFFEE", "reference_images": {}}}
STK_B = {"key": "sleepy", "output": "static/stickers/sticker-sleepy.png",
         "composition": {"modifiers": {}, "scene": "SLEEPY", "reference_images": {}}}
COV_A = {"key": "post-one", "output": "content/posts/one/cover.png",
         "composition": {"modifiers": {}, "scene": "ONE", "reference_images": {}}}
COV_B = {"key": "post-two", "output": "content/posts/two/cover.png",
         "composition": {"modifiers": {}, "scene": "TWO", "reference_images": {}}}


def test_out_dir_uses_the_output_basename(tmp_path):
    """frank's regen files are `sticker-<key>.png` (generate-stickers.py:118),
    matching the master its README says to copy over, so `<key>.png` would break
    the runbook. Unique basenames get the bare basename."""
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), entries=(STK_A, STK_B))
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in d.glob("*.png")) == ["sticker-coffee.png",
                                                       "sticker-sleepy.png"]
    assert not (d / "coffee.png").exists()


def test_colliding_basenames_are_all_key_prefixed(tmp_path):
    """85 of frank's 91 cover entries end in `/cover.png`, so the bare basename
    would collapse them onto one file. When two or more SELECTED entries collide,
    EVERY colliding entry is written as `<key>-<basename>` — never a mix of one
    bare and the rest prefixed, which would make 'who got the bare name' depend
    on iteration order."""
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), entries=(COV_A, COV_B))
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in d.glob("*.png")) == ["post-one-cover.png",
                                                       "post-two-cover.png"]
    assert not (d / "cover.png").exists()


def test_the_collision_decision_is_order_independent(tmp_path):
    """A function of the selected SET. Feeding the same entries in the opposite
    order must produce the identical file names."""
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    r = _run(a, "--out", str(a / "regen"), entries=(COV_A, COV_B, STK_A))
    assert r.returncode == 0, r.stderr
    r = _run(b, "--out", str(b / "regen"), entries=(STK_A, COV_B, COV_A))
    assert r.returncode == 0, r.stderr
    assert (sorted(p.name for p in (a / "regen").glob("*.png"))
            == sorted(p.name for p in (b / "regen").glob("*.png"))
            == ["post-one-cover.png", "post-two-cover.png", "sticker-coffee.png"])


def test_a_single_selected_entry_never_collides_with_itself(tmp_path):
    """`--only` narrows the selected set, so one cover entry on its own keeps the
    bare `cover.png`: the prefix exists to disambiguate, and there is nothing to
    disambiguate from."""
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), "--only", "post-one", entries=(COV_A, COV_B))
    assert r.returncode == 0, r.stderr
    assert [p.name for p in d.glob("*.png")] == ["cover.png"]


def test_a_non_png_output_keeps_its_real_extension(tmp_path):
    """The extension comes from `output:`, not from a hardcoded '.png' — an
    entry that publishes `.webp` must not land as a `.png` that is not one."""
    e = {"key": "k-w", "output": "static/images/hero.webp",
         "composition": {"modifiers": {}, "scene": "W", "reference_images": {}}}
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), entries=(e,))
    assert r.returncode == 0, r.stderr
    assert [p.name for p in d.iterdir()] == ["hero.webp"]


# --- 10. --out must REFUSE to alias `output:` rather than write it ---

def test_out_dir_that_aliases_output_is_refused(tmp_path):
    """`--out` is resolved against the process CWD, so `--out static/images` run
    from the blog root makes `dest` the very file `output:` names. A path-shaped
    promise that can alias is not a guarantee: refuse the run, naming both paths,
    before a single API call is spent."""
    master = tmp_path / "static" / "images" / "k-01.png"
    master.parent.mkdir(parents=True)
    master.write_bytes(CURATED)
    before = master.stat().st_mtime_ns

    r = _run(tmp_path, "--out", "static/images", cwd=tmp_path)
    assert r.returncode != 0
    assert master.read_bytes() == CURATED
    assert master.stat().st_mtime_ns == before
    assert str(master) in r.stderr or "static/images/k-01.png" in r.stderr
    assert "k-01" in r.stderr


def test_the_alias_guard_sees_through_a_symlinked_out_dir(tmp_path):
    """Resolved-path comparison, not string comparison: a symlink to the
    published directory is the same alias by another name."""
    master = tmp_path / "static" / "images" / "k-01.png"
    master.parent.mkdir(parents=True)
    master.write_bytes(CURATED)
    link = tmp_path / "regen-link"
    link.symlink_to(master.parent, target_is_directory=True)

    r = _run(tmp_path, "--out", str(link))
    assert r.returncode != 0, r.stdout
    assert master.read_bytes() == CURATED


def test_a_distinct_out_dir_under_the_published_tree_is_fine(tmp_path):
    """The guard is per-FILE, not per-tree: `--out static/images/regen` never
    aliases `static/images/k-01.png`, so it must not be refused."""
    d = tmp_path / "static" / "images" / "regen"
    r = _run(tmp_path, "--out", str(d))
    assert r.returncode == 0, r.stderr
    assert (d / "k-01.png").is_file()
    assert not (tmp_path / "static" / "images" / "k-01.png").exists()


# --- 11. the bare-name file is written ONCE, not once per variant ---

def test_the_bare_name_is_written_once_per_run(tmp_path, monkeypatch):
    """The copy sat inside the variant loop, so an N-variant run wrote `dest` N
    times (N-1 of them immediately overwritten). Hoisted below the loop: one
    write, of `variants[-1]`."""
    payloads = [_png("red"), _png("green"), _png("blue")]
    _install_fake(monkeypatch, payloads)
    cfg_path = _blog(tmp_path)
    m = _mod()
    d = tmp_path / "regen"

    writes: list = []
    real = m.Path.write_bytes

    def _counting(self, data):
        writes.append(Path(self))
        return real(self, data)

    monkeypatch.setattr(m.Path, "write_bytes", _counting)
    assert m.main(["--config", str(cfg_path), "--out", str(d), "--count", "3"]) == 0
    assert [p for p in writes if p == d / "k-01.png"] == [d / "k-01.png"], writes
    assert (d / "k-01.png").read_bytes() == payloads[-1]


# --- 12. an entry that composes to NOTHING is WARNed about, not silently dropped -

# The unresolvable spelling: `_ORDER_REF` (generate-images.py) matches only
# `composition_orders[<name>]`, so a bare `sticker` resolves to `[]`, `compose([])`
# is `""` and the entry drops out of the selected set. That produced ALL 18
# stickers, no output and exit code 0 during phase 4 (journal
# `p4-order-sticker-must-be-bracketed-reference`), and it is not sticker-specific:
# a typo'd order name on a COVER entry behaves the same way.
E_EMPTY = {"key": "k-empty", "output": "static/images/k-empty.png",
           "composition": {"order": "sticker", "modifiers": {}, "scene": "S",
                           "reference_images": {}}}


def test_an_entry_whose_prompt_composes_empty_is_warned_about_by_key(tmp_path):
    r = _run(tmp_path, entries=(E1, E_EMPTY))
    assert r.returncode == 0, r.stderr          # NOT an error — see below
    err = r.stderr + r.stdout
    assert "k-empty" in err, err
    assert "WARN" in err and "empty" in err, err
    # the fix is in the entry, so the WARN names the field to look at
    assert "composition.order" in err, err
    # the valid entry still generated, and the empty one wrote nothing
    assert (tmp_path / "static" / "images" / "k-01.png").is_file()
    assert not (tmp_path / "static" / "images" / "k-empty.png").exists()


def test_the_empty_prompt_stays_a_WARNING_and_never_changes_the_exit_code(tmp_path):
    """Deliberately a warning, not an error. An operator may have a legitimately
    empty entry, and making it non-zero would be a real behaviour change on the
    COVER path — every blog's generation run. Loud, not fatal."""
    r = _run(tmp_path, entries=(E_EMPTY,))
    assert r.returncode == 0, r.stderr
    assert "k-empty" in (r.stderr + r.stdout)
    assert not (tmp_path / "static").exists()


def test_the_warning_also_fires_under_out_where_there_is_no_file_to_miss(tmp_path):
    """Under `--out` nothing is written to `output:` even for a healthy entry, so
    the absent candidate is the ONLY symptom — which is exactly the case the
    silence was worst in."""
    d = tmp_path / "regen"
    r = _run(tmp_path, "--out", str(d), entries=(E1, E_EMPTY))
    assert r.returncode == 0, r.stderr
    assert "k-empty" in (r.stderr + r.stdout)
    assert (d / "k-01.png").is_file()
    assert not (d / "k-empty.png").exists()


def test_a_healthy_run_emits_no_such_warning(tmp_path):
    """The negative half: the WARN must not fire for entries that compose."""
    r = _run(tmp_path, entries=(E1, E2))
    assert r.returncode == 0, r.stderr
    assert "composes to nothing" not in (r.stderr + r.stdout)
