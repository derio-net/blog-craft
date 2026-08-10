"""THE GATE: frank's 18 sticker prompts compose byte-identically through blog-craft.

Phase 5 of the stickers plan. If these 18 assertions are not byte-exact, the port
has failed regardless of what else is green — every other phase is machinery in
service of this equality.

What makes it a proof rather than a transcription check:

- the goldens in `tests/fixtures/stickers/golden/` are the output of frank's OWN
  `compose_prompt()` (see `GOLDEN-PROVENANCE.md` for the stub recipe and the frank
  sha). Nothing in blog-craft produced them.
- the 18 entries are DERIVED mechanically from the vendored `stickers.yaml`
  (`_stickers_fixture.sticker_entries`), not hand-written — spec §7.
- the layer prose is pinned byte-for-byte against the vendored yaml by
  `test_the_fixture_layers_are_franks_prose_verbatim`. A golden that matched
  RETYPED prose would mean the golden had been edited, which is the one failure
  mode this file cannot otherwise see.

If a golden and the engine disagree, **the fixture is wrong, not the golden.**

The comparison runs the shipped CLI (`generate-images.py --print-prompt <key>`)
rather than calling `compose()` in-process, because the composition path the
operator actually gets includes `order_tokens` (the bracketed order reference) and
`selector_source` (scene -> `prompt`) — the two places the entry shape can be
wrong while `compose()` itself is perfect.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from _stickers_fixture import (CONFIG, GOLDEN, MOOD_TEMPLATE, PROSE_LAYERS,
                               STICKER_ORDER, build_blog, frank_config,
                               fixture_config, sticker_entries, sticker_keys)

KEYS = sticker_keys()


@pytest.fixture(scope="module")
def blog(tmp_path_factory):
    return build_blog(tmp_path_factory.mktemp("golden"))


def _print_prompt(blog, key) -> bytes:
    """`--print-prompt` stdout as raw BYTES, run from outside the blog.

    Bytes, not text, because "byte-identical" is the claim. `PYTHONIOENCODING` is
    pinned so the assertion cannot become a statement about the runner's locale
    (the prose carries em dashes and `#FFFFFF`-style prose throughout).
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, str(blog / "scripts" / "generate-images.py"),
         "--config", str(blog / "shadow.blog-craft.yaml"), "--print-prompt", key],
        capture_output=True, env=env, cwd=str(blog.parent))
    assert r.returncode == 0, r.stderr.decode()
    assert b"WARN" not in r.stderr, r.stderr.decode()
    return r.stdout


# --- the 18 assertions -------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_the_composed_prompt_is_byte_identical_to_franks(blog, key):
    golden = os.path.join(GOLDEN, f"{key}.txt")
    with open(golden, "rb") as fh:
        want = fh.read()
    got = _print_prompt(blog, key)
    if got != want:
        # A diff here is a real finding about the PORT. Report it as sections, so
        # a reordering (border/scene) reads as a reordering and a lost frame reads
        # as a lost frame, instead of as a 4.6k-character wall.
        gs = got.decode().rstrip("\n").split("\n\n")
        ws = want.decode().rstrip("\n").split("\n\n")
        detail = [f"{key}: {len(gs)} sections composed, {len(ws)} in the golden"]
        for i in range(max(len(gs), len(ws))):
            g, w = (gs[i] if i < len(gs) else None), (ws[i] if i < len(ws) else None)
            if g != w:
                detail.append(f"  section {i + 1} differs:\n    got:  {str(g)[:200]}"
                              f"\n    want: {str(w)[:200]}")
        pytest.fail("\n".join(detail))


def test_all_eighteen_stickers_are_covered():
    """A fixture that silently lost a key would make the 18 assertions above pass
    by not running."""
    assert len(KEYS) == 18
    assert len(set(KEYS)) == 18
    for key in KEYS:
        assert os.path.isfile(os.path.join(GOLDEN, f"{key}.txt")), key


# --- the fixture is frank's data, not a retyping of it -----------------------

def test_the_fixture_layers_are_franks_prose_verbatim():
    """The five prose layers must be the vendored prose, character for character.

    This is the assertion that keeps the goldens honest. Reflowing, retyping or
    "tidying" one of these blocks would either break all 18 goldens (loud, fine)
    or — if someone then regenerated the goldens to match — silently redefine the
    contract. Renaming is the only transformation allowed, and it is REQUIRED:
    sticker `base_character` contradicts frank's cover `base_character` outright
    (spec §Findings 2).
    """
    frank = frank_config()
    layers = fixture_config()["image"]["layers"]
    for layer, frank_key in PROSE_LAYERS.items():
        assert layers[layer] == frank[frank_key], layer


def test_the_mood_frame_is_its_own_template_only_layer():
    """`_template` on a layer named `mood` would compose "Frank's expression:
    Frank's expression is curious — …" on every one of frank's ~84 COVERS, because
    his cover mood table already holds complete sentences and his hero/banner
    orders name plain `mood` (journal `p1-mood-template-regresses-frank-covers`).
    Nothing else in blog-craft catches that: these goldens are sticker-only and
    `test_image_compose.py` uses a `_template`-free fixture. So the frame lives on
    `sticker_mood`, and the fixture must not carry a `mood` layer at all.
    """
    layers = fixture_config()["image"]["layers"]
    assert layers["sticker_mood"] == {"_template": MOOD_TEMPLATE}
    assert "mood" not in layers
    # ... and the order names it PLAIN. `sticker_mood[...]` would drop the frame
    # (`_apply_template` is not on `resolve_token`'s bracket path) and is now
    # rejected outright by `validate_config` (review fix 9).
    assert "sticker_mood" in STICKER_ORDER


def test_clothing_is_an_empty_table_so_sticker_prose_passes_through():
    """frank's sticker `clothing` is per-entry free-form prose, so the layer only
    has to exist for the free-form passthrough to fire. It cannot be OMITTED:
    `resolve_layer` returns "" for an unknown layer, and compose() drops empty
    sections — the clothing section would silently vanish from all 18 prompts.
    """
    assert fixture_config()["image"]["layers"]["clothing"] == {}


def test_the_composition_order_is_franks_eight_tokens_with_the_border_last():
    order = fixture_config()["image"]["composition_orders"]["sticker"]
    assert order == STICKER_ORDER
    assert order[-2:] == ["scene", "sticker_border_spec"], \
        "border_spec follows scene (generate-stickers.py:49-54) — swapping them " \
        "yields a prompt that reads correctly and is wrong"


def test_every_entry_uses_the_bracketed_order_reference():
    """`order: sticker` composes an EMPTY prompt and `main()` then skips the entry
    in silence — 18 stickers, no output, exit 0 (spec §5b)."""
    frank = frank_config()
    entries = sticker_entries(frank, "images")
    assert len(entries) == 18
    for e in entries:
        assert e["composition"]["order"] == "composition_orders[sticker]", e["key"]
        assert set(e["composition"]["modifiers"]) == {"sticker_mood", "clothing"}, e["key"]
        assert e["aspect_ratio"] == "1:1", e["key"]


# --- the two structural invariants the equality rests on ---------------------

def test_every_golden_has_eight_non_empty_sections():
    """frank's join does NOT filter empty sections; `compose()` DOES. The two agree
    only because all eight sections are non-empty for all 18 stickers — so that is
    an invariant of the fixture data, not an accident to be discovered later.
    """
    for key in KEYS:
        with open(os.path.join(GOLDEN, f"{key}.txt"), encoding="utf-8") as fh:
            body = fh.read()
        assert body.endswith("\n") and not body.endswith("\n\n"), key
        sections = body[:-1].split("\n\n")
        assert len(sections) == 8, (key, len(sections))
        assert all(s.strip() for s in sections), key


def test_the_fixture_config_is_a_valid_v7_config():
    """The fixture is the shape frank pastes, so it has to pass the shipped
    validator — which is also where the `X[y]`-on-a-`_template`-layer rule and the
    `features.stickers` shape are enforced."""
    from validate_config import validate_config   # tools/ is on sys.path
    cfg = fixture_config()
    assert cfg["version"] == 7
    assert validate_config(cfg) == []


def test_validate_images_reports_no_errors_for_the_fixture(blog):
    """The ONLY thing that catches an unresolvable composition order
    ("unknown composition order reference", validate_images.py:50-58). One
    assertion turns the whole class of entry-shape mistake from silent to loud.
    """
    r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "tools/validate_images.py"),
         "--config", str(blog / "shadow.blog-craft.yaml")],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "18 entries" in r.stdout, r.stdout


def test_the_fixture_config_file_is_committed():
    """The goldens are worthless without the config that composes them."""
    assert os.path.isfile(CONFIG), CONFIG
