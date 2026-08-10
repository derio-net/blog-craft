"""`tools/migrate_stickers.py` — the one-time transform `/update` cannot do (P6).

`/update`'s `plan_update` skips the `content` class outright (`update.py:153`), and
every remaining frank sticker file IS content: `stickers.yaml` (his prose), the 18
curated masters, the 2 print sheets, the README. That skip is correct — those are
irreplaceable operator artifacts — so the port needs a transform the operator runs
once (spec §7).

The claim under test is **prompt preservation**: feeding the transform's output to
the shipped engine reproduces the phase-5 goldens byte-for-byte. Everything else
here guards a way that can be true while the migration is still wrong:

- the transform must PRINT the layer block, never edit `.blog-craft.yaml` (that
  file is `content` class; silent config surgery is how #60 happened);
- it must never emit a bare `mood:` — frank's own `mood` table holds complete
  sentences, so merging a `_template` into it double-frames all ~84 of his covers
  (journal `p1-mood-template-regresses-frank-covers`);
- it must rewrite the two SELF-REFERENTIAL style anchors: frank's sticker set uses
  two of its own masters as anchors, so relocating `images/` moves the anchors too.
  Get this wrong and the goldens still pass while generation silently loses them
  (spec risk 4) — which is why the anchors are asserted directly AND asserted to
  exist on disk after `--move-assets`;
- prose containing `{` or `}` must pass through UNHARMED. `str.format` never
  rescans the substituted argument, so only the `_template` string itself is
  parsed. Spec §Risks 2 claimed otherwise and is formally withdrawn: a brace guard
  here would reject valid content for no reason.

The engine is driven through a SHADOW CONFIG in the same directory as the real one
— neither `generate-images.py --print-prompt` nor `tools/validate_images.py` has a
prompts-file flag, and the engine resolves the blog root as `cfg_path.parent`, so a
shadow anywhere else would silently relocate every path (journal
`p4-shim-shadow-config-and-regen-location`, `p5-fixture-artifacts-for-phases-6-8`).
Here the shadow is built by MERGING the tool's printed fragments, which is the
operator action from spec §8 step 4 — so the fragments are proven usable, not merely
present. Both readings of that instruction are covered, and they are different
claims: the dict-level merge (`paste_and_shadow`) proves the fragments' CONTENT
composes frank's prompts, while the byte-level append at the bottom of this file
proves the printed TEXT cannot destroy the config it is put into. The second one is
new: the first shape of this block was rooted at `image:` and, appended literally,
replaced frank's whole `image:` mapping with no error anywhere.
"""
from __future__ import annotations

import copy
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from _stickers_fixture import (CONFIG, ENGINE_DIR, GOLDEN, MOOD_TEMPLATE,
                               PROSE_LAYERS, STICKER_ORDER, VENDORED,
                               fixture_config, frank_config, reference_paths,
                               sticker_entries, sticker_keys)

import migrate_stickers as ms   # tools/ is on sys.path (tests/conftest.py)

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "migrate_stickers.py"
FRANK = frank_config()
KEYS = sticker_keys()

LEGACY_REL = "blog/_private/frank-stickers"
NEW_REL = "blog/_private/stickers"

# frank's real cover `mood` layer shape (`frank/.blog-craft.yaml:154-167`): a flat
# table whose VALUES are already complete sentences. The whole point of
# `sticker_mood` is that a `_template` must never land on this.
COVER_MOOD = {
    "curious": "Frank's expression is curious — head tilted, brow lifted.",
    "satisfied": "Frank's expression is satisfied — a small closed-mouth smile.",
}

# frank's real cover `clothing` layer (`frank/.blog-craft.yaml:136-153`), read from
# the host: a NESTED two-level table keyed by group. Structurally faithful, with the
# real group names, because those keys ARE the collision surface. Measured
# 2026-08-03: it declares no `_select` and no directives, and 85 of frank's 90 cover
# entries select from it — 84 of those with the BRACKET form `group[variant]`, the
# 85th (`ops-30-silent-failure`) with free-form prose that survives via passthrough.
COVER_CLOTHING = {
    "generic": {"default": "Frank's torso/body is exposed server hardware"},
    "building": {
        "default": "Frank's torso/body is exposed server hardware",
        "dirty": "Frank wears dirty/patched work clothes.",
        "overalls": "Frank wears overalls.",
        "overalls_lab": "Frank wears overalls under a lab coat.",
        "apron": "Frank wears a work apron with tools in the pockets.",
    },
    "operating": {
        "hoodie_and_sunglasses": "Frank wears a hoodie and sunglasses.",
        "tshirt_rolled_sleeves": "Frank wears t-shirt with rolled-up sleeves.",
    },
    "papers": {"default": "Frank wears an open white lab coat."},
}


# --- fixture blog -------------------------------------------------------------

def _png(path: Path) -> None:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (27, 67, 50)).save(path)


def base_config() -> dict:
    """The config frank has BEFORE pasting: `features.stickers` from `/update`'s v7
    rung pointed at the NEW dirs, his cover layers, and no sticker layers at all."""
    cfg = copy.deepcopy(fixture_config())
    img = cfg["image"]
    img["composition_orders"] = {"hero": ["mood", "scene"]}
    img["layers"] = {"mood": copy.deepcopy(COVER_MOOD)}
    stk = cfg["features"]["stickers"]
    stk["prompts_file"] = f"{NEW_REL}/stickers-prompts.yaml"
    stk["images_dir"] = f"{NEW_REL}/images"
    stk["sheets_dir"] = f"{NEW_REL}/sheets"
    return cfg


def franklike_config() -> dict:
    """frank's ACTUAL pre-paste shape: populated `clothing` AND `mood` tables, and
    cover orders that name both plainly.

    `base_config` above has neither layer populated, which is the one case where
    emitting `clothing: {}` is correct — so every golden assertion written against
    it is blind to the whole class of "the pasted block collides with what the blog
    already has". This config exists to close that blind spot.
    """
    cfg = base_config()
    img = cfg["image"]
    img["layers"] = {
        "base_character": "Frank — a chibi-proportioned green Frankenstein monster.",
        "clothing": copy.deepcopy(COVER_CLOTHING),
        "mood": copy.deepcopy(COVER_MOOD),
    }
    img["composition_orders"] = {"hero": ["base_character", "clothing", "mood", "scene"]}
    return cfg


def build_legacy_blog(tmp_path, cfg=None, legacy_text=None, git=False) -> Path:
    """A blog root in frank's pre-migration state: legacy prose + curated assets."""
    blog = tmp_path / "blog-root"
    blog.mkdir(parents=True, exist_ok=True)
    cfg = base_config() if cfg is None else cfg
    (blog / ".blog-craft.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    (blog / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": []}))

    legacy = blog / LEGACY_REL
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "stickers.yaml").write_text(
        Path(VENDORED).read_text() if legacy_text is None else legacy_text)
    (legacy / "README.md").write_text("# frank stickers\n")
    for key in [s["key"] for s in yaml.safe_load((legacy / "stickers.yaml").read_text())
                .get("stickers", [])]:
        _png(legacy / "images" / f"sticker-{key}.png")
    for n in (1, 2):
        _png(legacy / "sheets" / f"frank-stickers-A4-sheet{n}.png")

    # the reference pool frank's paths resolve against (repo-root-relative in his
    # yaml, blog-root-relative here — the strings carry over unchanged)
    for s in FRANK["stickers"]:
        for rel in reference_paths(FRANK, s):
            if not rel.startswith(f"{LEGACY_REL}/"):
                p = blog / rel
                if not p.is_file():
                    _png(p)

    if git:
        # A COMMIT, not just `git add`: `git status --porcelain` reports renames
        # against a committed baseline only — with an empty HEAD every path reads
        # as `A `, so a plain `add` would make the rename assertion vacuous.
        subprocess.run(["git", "init", "-q"], cwd=blog, check=True)
        subprocess.run(["git", "add", "-A"], cwd=blog, check=True)
        subprocess.run(["git", "-c", "user.email=t@example.invalid",
                        "-c", "user.name=t", "commit", "-qm", "legacy state"],
                       cwd=blog, check=True)
    return blog


def run(blog: Path, *extra: str, legacy: str | None = None):
    """Invoke the shipped tool from OUTSIDE the blog — paths are config-relative."""
    args = [sys.executable, str(TOOL),
            "--config", str(blog / ".blog-craft.yaml"),
            "--legacy", legacy or str(blog / LEGACY_REL / "stickers.yaml"), *extra]
    return subprocess.run(args, capture_output=True, text=True, cwd=str(blog.parent))


def printed_region(stdout: str) -> str:
    """Everything the tool prints between its outer markers, the inner marker
    comments included — the widest thing an operator could select and copy."""
    assert ms.PASTE_BEGIN in stdout and ms.PASTE_END in stdout, stdout
    return stdout.split(ms.PASTE_BEGIN + "\n", 1)[1].split(ms.PASTE_END, 1)[0]


def fragments(stdout: str) -> tuple[str, str]:
    """The two fragments' exact bytes: `(composition_orders, layers)`.

    Each is already at the indentation it occupies inside `image:`, and neither
    carries an enclosing key — that is the property that makes the printed text safe
    to put in a config file at all (see the byte-append test at the bottom).
    """
    body = printed_region(stdout)
    assert ms.ORDERS_MARK in body and ms.LAYERS_MARK in body, body
    orders = body.split(ms.ORDERS_MARK + "\n", 1)[1].split(ms.LAYERS_MARK, 1)[0]
    return orders, body.split(ms.LAYERS_MARK + "\n", 1)[1]


def layer_block(stdout: str) -> dict:
    """The two fragments parsed back into the `image:` sub-mappings they belong to."""
    orders, layers = fragments(stdout)
    return {"composition_orders": yaml.safe_load(textwrap.dedent(orders)),
            "layers": yaml.safe_load(textwrap.dedent(layers))}


def entries_of(blog: Path, cfg=None) -> list[dict]:
    stk = (cfg or base_config())["features"]["stickers"]
    doc = yaml.safe_load((blog / stk["prompts_file"]).read_text())
    return doc["images"]


def paste_and_shadow(blog: Path, stdout: str, cfg=None) -> Path:
    """spec §8 step 4: MERGE the printed fragments, then repoint `prompts_file`.

    A dict-level merge is one of the two readings of the printed instruction — the
    semantic one, and the class this covers is "the fragments' CONTENT composes
    frank's prompts". The other reading (an operator selecting the printed lines and
    putting them in the file, bytes and all) is covered by
    `test_appending_the_printed_block_to_a_frank_shaped_config_keeps_the_cover_layers`;
    that one is about data loss, this one about prompt fidelity, and neither implies
    the other.

    The shadow lives beside the real config because the engine resolves the blog
    root as `cfg_path.parent`; a shadow in a temp dir would relocate every
    reference path and make the `--out` alias guard compare against `/tmp`.
    """
    cfg = copy.deepcopy(cfg or base_config())
    block = layer_block(stdout)
    cfg["image"]["layers"].update(block["layers"])
    cfg["image"]["composition_orders"].update(block["composition_orders"])
    cfg["image"]["prompts_file"] = cfg["features"]["stickers"]["prompts_file"]
    shadow = blog / "shadow.blog-craft.yaml"
    shadow.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    sdir = blog / "scripts"
    sdir.mkdir(exist_ok=True)
    for n in ("generate-images.py", "compose.py"):
        shutil.copy(os.path.join(ENGINE_DIR, n), sdir / n)
    return shadow


@pytest.fixture(scope="module")
def migrated(tmp_path_factory):
    """A migrated blog plus the tool's stdout, ready to compose through the engine.

    The reference PNGs are materialised from the paths the tool DECLARED, so the
    golden comparison is about prompt text only. That the declared anchor paths are
    the RIGHT ones is a separate assertion here, and that they exist on disk after
    the real relocation is asserted in the `--move-assets` task.
    """
    blog = build_legacy_blog(tmp_path_factory.mktemp("migrate"))
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    for e in entries_of(blog):
        ri = e["composition"]["reference_images"]
        for rel in [ri["primary"], *ri["clothing"]]:
            if not (blog / rel).is_file():
                _png(blog / rel)
    paste_and_shadow(blog, r.stdout)
    return blog, r.stdout


def print_prompt(blog: Path, key: str) -> bytes:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, str(blog / "scripts" / "generate-images.py"),
         "--config", str(blog / "shadow.blog-craft.yaml"), "--print-prompt", key],
        capture_output=True, env=env, cwd=str(blog.parent))
    assert r.returncode == 0, r.stderr.decode()
    assert b"WARN" not in r.stderr, r.stderr.decode()
    return r.stdout


# --- 1. the transform is prompt-preserving (the only claim that matters) ------

@pytest.mark.parametrize("key", KEYS)
def test_the_migrated_entry_composes_franks_prompt_byte_for_byte(migrated, key):
    blog, _ = migrated
    with open(os.path.join(GOLDEN, f"{key}.txt"), "rb") as fh:
        want = fh.read()
    got = print_prompt(blog, key)
    if got != want:
        gs = got.decode().rstrip("\n").split("\n\n")
        ws = want.decode().rstrip("\n").split("\n\n")
        detail = [f"{key}: {len(gs)} sections composed, {len(ws)} in the golden"]
        for i in range(max(len(gs), len(ws))):
            g = gs[i] if i < len(gs) else None
            w = ws[i] if i < len(ws) else None
            if g != w:
                detail.append(f"  section {i + 1} differs:\n    got:  {str(g)[:200]}"
                              f"\n    want: {str(w)[:200]}")
        pytest.fail("\n".join(detail))


def test_the_prompts_file_holds_eighteen_v5_entries(migrated):
    blog, _ = migrated
    entries = entries_of(blog)
    assert len(entries) == 18
    assert [e["key"] for e in entries] == KEYS      # frank's order, not sorted
    for e in entries:
        assert e["composition"]["order"] == "composition_orders[sticker]", e["key"]
        assert set(e["composition"]["modifiers"]) == {"sticker_mood", "clothing"}
        assert e["aspect_ratio"] == "1:1", e["key"]
        assert e["output"] == f"{NEW_REL}/images/sticker-{e['key']}.png", e["key"]
        assert e["sheet"] and e["pos"], e["key"]


def test_the_derived_entries_equal_the_phase5_fixture_derivation(migrated):
    """The shipped transform and `_stickers_fixture.sticker_entries` must agree —
    that equality is what makes the phase-5 goldens a proof about THIS tool."""
    blog, _ = migrated
    want = sticker_entries(FRANK, f"{NEW_REL}/images")
    # the fixture keeps frank's own anchor strings; the tool relocates them, which
    # is the one intended difference (spec risk 4).
    for e in want:
        ri = e["composition"]["reference_images"]
        ri["clothing"] = [c.replace(f"{LEGACY_REL}/images", f"{NEW_REL}/images")
                          for c in ri["clothing"]]
    assert entries_of(blog) == want


def test_validate_images_reports_no_errors_for_the_migrated_blog(migrated):
    """The only thing that catches an unresolvable composition order
    (`validate_images.py:50-58`) — the `order: sticker` trap, made loud."""
    blog, _ = migrated
    r = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_images.py"),
         "--config", str(blog / "shadow.blog-craft.yaml")],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "18 entries" in r.stdout, r.stdout


# --- 2. it PRINTS the layer block and does not touch the config ---------------

def test_the_layer_block_is_printed_for_the_operator_to_merge(migrated):
    _, out = migrated
    block = layer_block(out)
    layers = block["layers"]
    assert block["composition_orders"]["sticker"] == STICKER_ORDER
    assert set(layers) == set(PROSE_LAYERS) | {"clothing", "sticker_mood"}
    for layer, frank_key in PROSE_LAYERS.items():
        assert layers[layer] == FRANK[frank_key], layer
    assert layers["sticker_mood"] == {"_template": MOOD_TEMPLATE}
    assert layers["clothing"] == {}, \
        "an ABSENT clothing layer resolves to '' and compose() drops the section — " \
        "the clothing sentence would silently vanish from all 18 prompts"


def test_the_printed_block_is_byte_identical_to_the_phase5_fixture_config(migrated):
    """The fixture config is the shape frank ends up with. If the shipped tool and
    the fixture disagree by so much as a space, the goldens are proving something
    about a config nobody will ever have.

    Compared REGION BY REGION rather than as one blob, because the fragments no
    longer carry the two structural key lines (`  composition_orders:` / `  layers:`)
    — that is the FIX, and the emitted content either side of them is unchanged, at
    the same indentation, which is what this asserts."""
    _, out = migrated
    lines = Path(CONFIG).read_text().splitlines(keepends=True)
    i = next(n for n, ln in enumerate(lines) if ln.startswith("  composition_orders:"))
    j = next(n for n, ln in enumerate(lines) if ln.startswith("  layers:"))
    k = next(n for n, ln in enumerate(lines) if ln.startswith("features:"))
    orders, layers = fragments(out)
    assert orders == "".join(lines[i + 1:j])
    assert layers == "".join(lines[j + 1:k])


def test_the_config_file_is_never_edited(tmp_path):
    """`.blog-craft.yaml` is `content` class. #60 was silent config surgery."""
    blog = build_legacy_blog(tmp_path)
    cfgp = blog / ".blog-craft.yaml"
    before, mtime = cfgp.read_bytes(), cfgp.stat().st_mtime_ns
    r = run(blog, "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cfgp.read_bytes() == before
    assert cfgp.stat().st_mtime_ns == mtime


# --- 2b. never a bare `mood:` ------------------------------------------------

def test_the_printed_block_never_emits_a_bare_mood_key(migrated):
    _, out = migrated
    assert "mood" not in layer_block(out)["layers"]
    text = printed_region(out)
    assert re.search(r"(?m)^\s*mood:", text) is None, text


def test_pasting_the_block_leaves_franks_cover_mood_table_intact(tmp_path):
    """A `mood:` key in the block would CLOBBER frank's cover table on paste, and
    a `_template` merged into it composes "Frank's expression: Frank's expression
    is curious — …" on every one of his ~84 covers."""
    blog = build_legacy_blog(tmp_path)
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    shadow = yaml.safe_load(paste_and_shadow(blog, r.stdout).read_text())
    layers = shadow["image"]["layers"]
    assert layers["mood"] == COVER_MOOD
    assert layers["sticker_mood"] == {"_template": MOOD_TEMPLATE}
    from validate_config import validate_config
    assert validate_config(shadow) == []


# --- 3. the self-referential style anchors are relocated ---------------------

def test_the_style_anchors_are_rewritten_to_the_configured_images_dir(migrated):
    """frank's anchors ARE two of his own sticker masters, so relocating `images/`
    relocates the anchors. Nothing else notices: the prompt text never names a
    path, so all 18 goldens pass either way (spec risk 4)."""
    blog, _ = migrated
    want = [f"{NEW_REL}/images/sticker-09-server-blade.png",
            f"{NEW_REL}/images/sticker-20-tinkering.png"]
    for e in entries_of(blog):
        assert e["composition"]["reference_images"]["clothing"][:2] == want, e["key"]


def test_the_set_still_references_its_own_output(migrated):
    """The anchors must remain the `output:` of entries 09 and 20 — the property
    that makes the rewrite necessary in the first place."""
    blog, _ = migrated
    by_key = {e["key"]: e for e in entries_of(blog)}
    anchors = by_key["05-golden-key"]["composition"]["reference_images"]["clothing"][:2]
    assert anchors == [by_key["09-server-blade"]["output"],
                       by_key["20-tinkering"]["output"]]


def test_no_emitted_path_still_points_at_the_legacy_directory(migrated):
    """Every PATH in the file — the generated header still names the legacy source,
    which is provenance and the one mention that should survive."""
    blog, _ = migrated
    for e in entries_of(blog):
        ri = e["composition"]["reference_images"]
        for rel in [e["output"], ri["primary"], *ri["clothing"]]:
            assert not rel.startswith(f"{LEGACY_REL}/"), (e["key"], rel)


def test_paths_outside_the_legacy_dir_are_left_alone(migrated):
    """The canon face and the clothing subjects live in `.reference-pool/`, which
    does not move — rewriting them would kill 13 of the 18 payloads."""
    blog, _ = migrated
    for e in entries_of(blog):
        ri = e["composition"]["reference_images"]
        assert ri["primary"] == FRANK["references"]["canon_face"], e["key"]
        for rest in ri["clothing"][2:]:
            assert rest.startswith(FRANK["references"]["subjects_dir"] + "/"), e["key"]


# --- 4. braces pass through UNHARMED (spec §Risks 2 is withdrawn) ------------

BRACY_SCENE = "Frank points at a screen showing {\"status\": \"ok\"} in a JSON blob."
BRACY_MOOD = "amused — reading {0} of {n} retries, one brow up"


def bracy_legacy() -> str:
    d = yaml.safe_load(Path(VENDORED).read_text())
    d["stickers"][0]["scene"] = BRACY_SCENE
    d["stickers"][0]["mood"] = BRACY_MOOD
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True)


def test_prose_containing_braces_is_not_refused_and_composes_correctly(tmp_path):
    """`str.format` never rescans the substituted argument — only the `_template`
    string itself is parsed. A brace guard here would reject valid content for no
    reason, so spec §Risks 2 is withdrawn and this pins the behaviour."""
    blog = build_legacy_blog(tmp_path, legacy_text=bracy_legacy())
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    key = KEYS[0]
    entry = {e["key"]: e for e in entries_of(blog)}[key]
    assert entry["composition"]["scene"] == BRACY_SCENE
    assert entry["composition"]["modifiers"]["sticker_mood"] == BRACY_MOOD

    for e in entries_of(blog):
        ri = e["composition"]["reference_images"]
        for rel in [ri["primary"], *ri["clothing"]]:
            if not (blog / rel).is_file():
                _png(blog / rel)
    paste_and_shadow(blog, r.stdout)
    prompt = print_prompt(blog, key).decode()
    assert BRACY_SCENE in prompt
    assert f"Frank's expression: {BRACY_MOOD}." in prompt


# --- 5. idempotent ----------------------------------------------------------

def test_a_second_identical_run_rewrites_nothing(tmp_path):
    blog = build_legacy_blog(tmp_path)
    dest = blog / base_config()["features"]["stickers"]["prompts_file"]
    assert run(blog).returncode == 0
    first, mtime = dest.read_bytes(), dest.stat().st_mtime_ns
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    assert dest.read_bytes() == first
    assert dest.stat().st_mtime_ns == mtime, "an unchanged file must not be rewritten"
    assert not list(dest.parent.glob("*.bak"))
    assert "unchanged" in r.stdout


def test_running_over_its_own_output_is_a_no_op_not_a_double_transform(tmp_path):
    blog = build_legacy_blog(tmp_path)
    assert run(blog).returncode == 0
    dest = blog / base_config()["features"]["stickers"]["prompts_file"]
    before = dest.read_bytes()
    r = run(blog, legacy=str(dest))
    assert r.returncode == 0, r.stdout + r.stderr
    assert dest.read_bytes() == before
    assert "already migrated" in r.stdout.lower()


# --- 6. it never writes outside the configured dirs -------------------------

def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


def test_it_writes_nothing_outside_the_configured_dirs(tmp_path):
    blog = build_legacy_blog(tmp_path)
    (tmp_path / "sibling").mkdir()
    (tmp_path / "sibling" / "keep.txt").write_text("untouched\n")
    before = snapshot(tmp_path)
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    after = snapshot(tmp_path)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    rel = base_config()["features"]["stickers"]["prompts_file"]
    assert changed == {f"blog-root/{rel}"}, changed


def test_a_configured_path_escaping_the_blog_root_is_refused(tmp_path):
    cfg = base_config()
    cfg["features"]["stickers"]["prompts_file"] = "../escaped/stickers.yaml"
    blog = build_legacy_blog(tmp_path, cfg=cfg)
    before = snapshot(tmp_path)
    r = run(blog)
    assert r.returncode != 0
    assert "escap" in (r.stdout + r.stderr).lower() or "outside" in (r.stdout + r.stderr).lower()
    assert snapshot(tmp_path) == before


# --- --dry-run ---------------------------------------------------------------

def test_dry_run_prints_the_diff_and_writes_nothing(tmp_path):
    blog = build_legacy_blog(tmp_path)
    before = snapshot(tmp_path)
    r = run(blog, "--dry-run", "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    assert snapshot(tmp_path) == before
    assert "+  key: 05-golden-key" in r.stdout or "+- key: 05-golden-key" in r.stdout, r.stdout
    assert ms.PASTE_BEGIN in r.stdout


# --- anything ambiguous exits non-zero with the reason ----------------------

def test_a_missing_prose_key_is_refused_by_name(tmp_path):
    d = yaml.safe_load(Path(VENDORED).read_text())
    del d["border_spec"]
    blog = build_legacy_blog(tmp_path, legacy_text=yaml.safe_dump(d, sort_keys=False))
    r = run(blog)
    assert r.returncode != 0
    assert "border_spec" in r.stdout + r.stderr


def test_an_empty_mood_is_refused_because_it_would_drop_a_section(tmp_path):
    """frank's join does NOT filter empty sections; `compose()` DOES. An empty mood
    composes 7 sections here against frank's 8, so the port would stop being
    prompt-preserving — silently (journal `p5-goldens-byte-identical-first-run`)."""
    d = yaml.safe_load(Path(VENDORED).read_text())
    d["stickers"][3]["mood"] = "  "
    blog = build_legacy_blog(tmp_path, legacy_text=yaml.safe_dump(d, sort_keys=False))
    r = run(blog)
    assert r.returncode != 0
    assert d["stickers"][3]["key"] in r.stdout + r.stderr
    assert "mood" in r.stdout + r.stderr


def test_a_duplicate_sticker_key_is_refused(tmp_path):
    d = yaml.safe_load(Path(VENDORED).read_text())
    d["stickers"][1]["key"] = d["stickers"][0]["key"]
    blog = build_legacy_blog(tmp_path, legacy_text=yaml.safe_dump(d, sort_keys=False))
    r = run(blog)
    assert r.returncode != 0
    assert "duplicate" in (r.stdout + r.stderr).lower()


def test_a_missing_features_stickers_block_is_refused(tmp_path):
    cfg = base_config()
    del cfg["features"]["stickers"]
    blog = build_legacy_blog(tmp_path, cfg=cfg)
    r = run(blog)
    assert r.returncode != 0
    assert "features.stickers" in r.stdout + r.stderr


def test_writing_the_prompts_file_over_the_legacy_source_is_refused(tmp_path):
    """The legacy yaml is the operator's PROSE. If `prompts_file` happens to name
    it, writing would destroy the only copy of the input."""
    cfg = base_config()
    cfg["features"]["stickers"]["prompts_file"] = f"{LEGACY_REL}/stickers.yaml"
    blog = build_legacy_blog(tmp_path, cfg=cfg)
    src = blog / LEGACY_REL / "stickers.yaml"
    before = src.read_bytes()
    r = run(blog)
    assert r.returncode != 0
    assert src.read_bytes() == before
    assert "legacy" in (r.stdout + r.stderr).lower()


def test_a_legacy_file_that_does_not_exist_is_refused(tmp_path):
    blog = build_legacy_blog(tmp_path)
    r = run(blog, legacy=str(blog / LEGACY_REL / "nope.yaml"))
    assert r.returncode != 0
    assert "nope.yaml" in r.stdout + r.stderr


# --- Task 2: moving the curated images and sheets ----------------------------
#
# 18 masters + 2 print sheets, all `content` class — `/update`'s `plan_update`
# skips them by design (`update.py:153`) precisely because they are irreplaceable
# operator artifacts. That is why the tool REFUSES an existing destination instead
# of overwriting it, and why the refusal has to happen before ANY move so a
# half-migrated tree is impossible.

def listing(d: Path) -> set[str]:
    return {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()}


def test_move_assets_git_mvs_both_directories(tmp_path):
    blog = build_legacy_blog(tmp_path, git=True)
    src_images = listing(blog / LEGACY_REL / "images")
    src_sheets = listing(blog / LEGACY_REL / "sheets")
    assert len(src_images) == 18 and len(src_sheets) == 2
    r = run(blog, "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (blog / LEGACY_REL / "images").exists()
    assert not (blog / LEGACY_REL / "sheets").exists()
    assert listing(blog / NEW_REL / "images") == src_images
    assert listing(blog / NEW_REL / "sheets") == src_sheets
    porcelain = subprocess.run(["git", "status", "--porcelain"], cwd=blog,
                               capture_output=True, text=True).stdout
    assert porcelain.count("R  ") == 20, porcelain
    assert "git mv" in r.stdout


def test_move_assets_refuses_when_the_destination_exists(tmp_path):
    """A curated master is never overwritten — and the refusal precedes EVERY move,
    so `sheets/` does not travel while `images/` is being refused."""
    blog = build_legacy_blog(tmp_path, git=True)
    keeper = blog / NEW_REL / "images" / "sticker-01-wave.png"
    _png(keeper)
    before = keeper.read_bytes()
    r = run(blog, "--move-assets")
    assert r.returncode != 0
    assert "refusing" in (r.stdout + r.stderr).lower()
    assert keeper.read_bytes() == before
    assert len(listing(blog / LEGACY_REL / "images")) == 18
    assert (blog / LEGACY_REL / "sheets").is_dir(), "no partial move"
    assert not (blog / NEW_REL / "sheets").exists()


def test_move_assets_is_a_no_op_when_the_source_is_already_gone(tmp_path):
    blog = build_legacy_blog(tmp_path, git=True)
    assert run(blog, "--move-assets").returncode == 0
    r = run(blog, "--move-assets")          # second time: nothing left to move
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nothing to move" in r.stdout
    assert len(listing(blog / NEW_REL / "images")) == 18


def test_move_assets_dry_run_lists_the_moves_without_performing_them(tmp_path):
    blog = build_legacy_blog(tmp_path, git=True)
    r = run(blog, "--move-assets", "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "would move" in r.stdout
    assert f"{LEGACY_REL}/images" in r.stdout and f"{NEW_REL}/images" in r.stdout
    assert len(listing(blog / LEGACY_REL / "images")) == 18
    assert not (blog / NEW_REL).exists()


def test_move_assets_falls_back_to_a_plain_move_outside_a_git_repo(tmp_path):
    blog = build_legacy_blog(tmp_path, git=False)
    r = run(blog, "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(listing(blog / NEW_REL / "images")) == 18
    assert not (blog / LEGACY_REL / "images").exists()
    assert "moved" in r.stdout


def test_an_untracked_source_inside_a_git_repo_still_moves_with_a_note(tmp_path):
    """`git mv` refuses an untracked path. The move is still the right outcome, so
    it happens — with git's own reason on stderr rather than in silence."""
    blog = build_legacy_blog(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=blog, check=True)   # nothing added
    r = run(blog, "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "git mv declined" in r.stderr
    assert len(listing(blog / NEW_REL / "images")) == 18


def test_move_assets_is_a_no_op_when_source_and_destination_coincide(tmp_path):
    """frank may keep his current directories (the phase-5 fixture config does).
    Source == destination must be recognised, not read as "destination exists"."""
    cfg = base_config()
    cfg["features"]["stickers"]["images_dir"] = f"{LEGACY_REL}/images"
    cfg["features"]["stickers"]["sheets_dir"] = f"{LEGACY_REL}/sheets"
    blog = build_legacy_blog(tmp_path, cfg=cfg, git=True)
    r = run(blog, "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already at the configured path" in r.stdout
    assert len(listing(blog / LEGACY_REL / "images")) == 18


def test_every_declared_reference_path_exists_after_the_move(tmp_path):
    """The rewrite and the move have to agree. Nothing is synthesised here: if the
    two style anchors were rewritten to a path the move does not produce, the
    payload silently loses them and the model stops seeing the head/hair anchors
    (spec risk 4) — a failure all 18 goldens are blind to."""
    blog = build_legacy_blog(tmp_path, git=True)
    r = run(blog, "--move-assets")
    assert r.returncode == 0, r.stdout + r.stderr
    for e in entries_of(blog):
        ri = e["composition"]["reference_images"]
        for rel in [ri["primary"], *ri["clothing"]]:
            assert (blog / rel).is_file(), (e["key"], rel)


# --- the merged fragments must not collide with what the blog already has ------
#
# spec §8 step 4 tells the operator to merge the printed fragments into
# `.blog-craft.yaml`. PyYAML resolves a duplicate mapping key by silently taking
# the LAST one, so any key the fragments emit that the config already defines is
# DESTROYED on merge — no error, no warning.
#
# Measured against frank's real config (2026-08-03): `image.layers.clothing` is a
# populated nested table and 84 of his 90 cover entries select from it with the
# bracket form `group[variant]` (the 85th, `ops-30-silent-failure`, carries free-form
# prose and would survive via passthrough — see the journal correction). Under a
# `clothing: {}` merge, `_resolve_modifier`
# takes the bracket path, `table.get(group)` is None, and the section resolves to
# "" — 85 cover prompts silently lose their clothing sentence entirely.

@pytest.fixture(scope="module")
def franklike(tmp_path_factory):
    """A migrated frank-LIKE blog: populated clothing + mood, block pasted."""
    cfg = franklike_config()
    blog = build_legacy_blog(tmp_path_factory.mktemp("franklike"), cfg=cfg)
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    for e in entries_of(blog, cfg):
        ri = e["composition"]["reference_images"]
        for rel in [ri["primary"], *ri["clothing"]]:
            if not (blog / rel).is_file():
                _png(blog / rel)
    paste_and_shadow(blog, r.stdout, cfg)
    return blog, r.stdout


def test_an_absent_clothing_layer_is_emitted_as_an_empty_table(migrated):
    """Without it the layer is unknown, `resolve_layer` returns "" and compose()
    drops the section — the clothing sentence vanishes from all 18 prompts."""
    _, out = migrated
    assert layer_block(out)["layers"]["clothing"] == {}


def test_an_existing_clothing_layer_is_never_emitted(franklike):
    """Emitting it here is not redundant, it is DESTRUCTIVE (duplicate-key
    last-wins). The existing table already serves stickers: their clothing is
    free-form prose, which `_resolve_modifier` returns via passthrough."""
    _, out = franklike
    assert "clothing" not in layer_block(out)["layers"]
    text = printed_region(out)
    assert re.search(r"(?m)^\s*clothing:", text) is None, text
    assert ms.CLOTHING_KEPT_NOTE in out, "the omission must be explained, not silent"


@pytest.mark.parametrize("key", KEYS)
def test_the_goldens_still_reproduce_against_a_franklike_config(franklike, key):
    """THE blind-spot closer: the 18-golden proof, run against a config that
    already has populated `clothing` and `mood` tables."""
    blog, _ = franklike
    with open(os.path.join(GOLDEN, f"{key}.txt"), "rb") as fh:
        want = fh.read()
    got = print_prompt(blog, key)
    if got != want:
        gs = got.decode().rstrip("\n").split("\n\n")
        ws = want.decode().rstrip("\n").split("\n\n")
        detail = [f"{key}: {len(gs)} sections composed, {len(ws)} in the golden"]
        for i in range(max(len(gs), len(ws))):
            g = gs[i] if i < len(gs) else None
            w = ws[i] if i < len(ws) else None
            if g != w:
                detail.append(f"  section {i + 1} differs:\n    got:  {str(g)[:200]}"
                              f"\n    want: {str(w)[:200]}")
        pytest.fail("\n".join(detail))


def test_the_existing_cover_layers_still_RESOLVE_after_the_paste(franklike):
    """Presence is not enough — the claim is that frank's COVERS still compose. So
    this resolves a real bracket selector (`building[overalls]`, the shape 84 of his
    90 entries use) and a real mood key through the shipped `compose.py`, against
    the merged layers."""
    blog, _ = franklike
    from compose import resolve_layer          # tools/ is on sys.path
    layers = yaml.safe_load((blog / "shadow.blog-craft.yaml").read_text())["image"]["layers"]
    assert layers["clothing"] == COVER_CLOTHING
    assert layers["mood"] == COVER_MOOD
    assert resolve_layer("clothing", layers["clothing"],
                         {"clothing": "building[overalls]"}) == "Frank wears overalls."
    assert resolve_layer("mood", layers["mood"],
                         {"mood": "curious"}) == COVER_MOOD["curious"]
    # ... and the sticker path through that SAME table is untouched prose
    assert resolve_layer("clothing", layers["clothing"],
                         {"clothing": "Frank wears his white lab coat over a shirt."}) \
        == "Frank wears his white lab coat over a shirt."


def test_frank_has_no_other_colliding_key_so_the_run_is_warning_free(franklike):
    """The `sticker_*` namespacing is what closes the rest of the surface. Measured
    against frank's real config: his layers are base_character, base_atmosphere,
    reference_guidance, clothing, mood, and his orders are hero / scenery / banner /
    banner_transform — so once `clothing` is handled, nothing else the block emits
    already exists. `franklike` reproduces that shape, so the run must be silent."""
    blog, _ = franklike
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARN" not in r.stderr, r.stderr


def test_a_key_the_config_already_defines_is_warned_about(tmp_path):
    """Generalising past frank: ANY emitted key that already exists is replaced on
    paste. For a prose layer that is what re-running the migration means, so it is a
    WARN — but never silence."""
    cfg = franklike_config()
    cfg["image"]["layers"]["sticker_border_spec"] = "some older sticker prose"
    cfg["image"]["composition_orders"]["sticker"] = ["sticker_border_spec", "scene"]
    blog = build_legacy_blog(tmp_path, cfg=cfg)
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "image.layers.sticker_border_spec" in r.stderr
    assert "image.composition_orders.sticker" in r.stderr


def test_a_sticker_clothing_value_colliding_with_a_group_key_is_refused(tmp_path):
    """The residual hazard of reusing an existing table: a sticker whose clothing
    prose happens to EQUAL a group name hits the named lookup, resolves to a
    container, and `_chunk` returns "" — seven sections instead of eight, silently.
    The tool verifies the passthrough for all 18 rather than assuming it."""
    d = yaml.safe_load(Path(VENDORED).read_text())
    d["stickers"][2]["clothing"] = "building"          # a group name, not prose
    blog = build_legacy_blog(tmp_path, cfg=franklike_config(),
                             legacy_text=yaml.safe_dump(d, sort_keys=False))
    r = run(blog)
    assert r.returncode != 0
    assert d["stickers"][2]["key"] in r.stdout + r.stderr
    assert "clothing" in r.stdout + r.stderr


def test_appending_the_printed_block_to_a_frank_shaped_config_keeps_the_cover_layers(tmp_path):
    """The printed instruction, executed LITERALLY, on bytes.

    Everything above proves the block's semantic CONTENT — `paste_and_shadow` merges
    it with `dict.update`, which is one of the two readings of "paste this". The
    other reading is the one an operator with a text editor actually performs: select
    the printed lines, put them in the file. Nothing tested that, and until this
    commit it destroyed data:

    the emitted text was rooted at `image:` and carried `composition_orders:` and
    `layers:` under it — all three keys a blog with covers already has. Appended at
    top level, PyYAML's duplicate-key last-wins replaced the WHOLE `image:` mapping:
    `model`, `prompts_file`, every cover layer and every cover order, gone.
    `validate_config` returns [] for the result, and the only symptom is the
    empty-prompt WARN on every cover at rc 0.

    The fix is in what is emitted, not in how it is described: the fragments carry no
    structural key at all, so a byte append has nothing to duplicate. The `image:`
    section is untouched — which is also why the mis-paste stays LOUD on the side it
    does affect: the sticker layers never arrive, `composition_orders[sticker]` does
    not resolve, and `tools/validate_images.py` says so.
    """
    cfg = franklike_config()
    blog = build_legacy_blog(tmp_path, cfg=cfg)
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr

    appended = (blog / ".blog-craft.yaml").read_bytes() + printed_region(r.stdout).encode()
    img = yaml.safe_load(appended.decode())["image"]
    assert img["layers"]["clothing"] == COVER_CLOTHING, \
        "the cover clothing table did not survive a literal append of the printed text"
    assert img["layers"]["mood"] == COVER_MOOD
    assert img["layers"]["base_character"] == cfg["image"]["layers"]["base_character"]
    assert img["composition_orders"] == cfg["image"]["composition_orders"]
    assert img["model"] == cfg["image"]["model"]
    assert img["prompts_file"] == cfg["image"]["prompts_file"]


def test_the_printed_fragments_declare_no_key_a_mis_paste_could_clobber(migrated):
    """The generalisation: which emitted key could collide, at any level?

    Answer, and it is the whole list: one order name (`sticker`) and at most seven
    layer names (six `sticker_*` plus `clothing`, itself emitted only when absent) —
    each of them a leaf the tool WARNs about when the config already defines it. Plus
    `_template`, nested inside the `sticker_mood` mapping the tool itself creates, so
    it can only collide if that layer name does.

    What must never appear is a STRUCTURAL key — `image:`, `layers:`,
    `composition_orders:` — because duplicating one of those does not replace a leaf,
    it deletes every sibling the existing mapping holds.
    """
    _, out = migrated
    body = "\n".join(ln for ln in printed_region(out).splitlines()
                     if not ln.lstrip().startswith("#"))
    for key in ("image", "layers", "composition_orders"):
        assert re.search(rf"(?m)^\s*{key}:", body) is None, \
            f"the fragments must not emit a `{key}:` key for a paste to duplicate"


def test_without_move_assets_the_curated_masters_stay_put(tmp_path):
    """The flag is opt-in: a default run writes the prompts file and prints, and
    touches not one PNG."""
    blog = build_legacy_blog(tmp_path, git=True)
    before = listing(blog / LEGACY_REL)
    r = run(blog)
    assert r.returncode == 0, r.stdout + r.stderr
    assert listing(blog / LEGACY_REL) == before
    assert not (blog / NEW_REL / "images").exists()
