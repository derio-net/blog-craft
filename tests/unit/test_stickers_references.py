"""Sticker reference payloads keep frank's exact order (stickers P5.T2).

The composed prompt tells the model that the FIRST attached image is canonical for
Frank's face ("The FIRST reference image is the canonical character-design sheet …
IGNORE those facial details"), so payload ORDER is not cosmetic: a payload whose
first image is a clothing anchor instructs the model to take the face from the
wrong picture. Prompt equality (`test_stickers_golden.py`) cannot see that at all.

The expectations are the committed `golden/<key>.refs.txt` files — the output of
frank's own `scene_refs()`, derived alongside the prompts (see
`tests/fixtures/stickers/GOLDEN-PROVENANCE.md`). Basenames rather than paths,
because the directories move in the port (frank resolved against his repo root,
blog-craft against the blog root) while the order is the thing under test.

No engine change is involved, and that is the claim: `primary_reference()` puts
`reference_images.primary` first and `entry_reference_paths()` appends
`reference_images.clothing` in declared order (generate-images.py:228-272), so
frank's `[canon_face, *style_anchors, clothing_subject?]` is expressible as-is. If
an engine change ever looks necessary here, the mapping is wrong.

The payload is resolved through the engine's `payload_paths()` — the same call
`_gen_bytes` makes — rather than re-assembled here. Re-assembling it was a real hole:
this file would stay green through a reordering inside `_gen_bytes`, and that is the
single class the goldens cannot see (prompt text is identical whichever image leads).
"""
from __future__ import annotations

import importlib.util
import os

import pytest

from _stickers_fixture import (ENGINE_DIR, GOLDEN, build_blog, fixture_config,
                               frank_config, sticker_entries)

FRANK = frank_config()
STICKERS = {s["key"]: s for s in FRANK["stickers"]}
KEYS = list(STICKERS)
WITH_ANCHOR = [k for k, s in STICKERS.items() if s.get("clothing_anchor")]
WITHOUT_ANCHOR = [k for k, s in STICKERS.items() if not s.get("clothing_anchor")]


def _engine():
    spec = importlib.util.spec_from_file_location(
        "generate_images_refs", os.path.join(ENGINE_DIR, "generate-images.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def blog(tmp_path_factory):
    return build_blog(tmp_path_factory.mktemp("refs"))


@pytest.fixture(scope="module")
def payloads(blog):
    """{key: [resolved Path, …]} as `_gen_bytes` assembles it — through the ENGINE's
    `payload_paths`, which is the assembly `_gen_bytes` itself calls.

    This used to re-implement the order (`[primary] + entry_reference_paths(...)`),
    which made the guard blind to exactly the change it exists to catch: a reordering
    inside `_gen_bytes` would have left this file green. Now there is one assembly and
    three callers of it (engine, sticker shim `--dry-run`, here)."""
    gi = _engine()
    cfg = fixture_config()
    image_cfg = cfg["image"]
    entries = {e["key"]: e
               for e in sticker_entries(FRANK, cfg["features"]["stickers"]["images_dir"])}
    return {key: gi.payload_paths(e, image_cfg, blog) for key, e in entries.items()}


def _golden_refs(key) -> list[str]:
    with open(os.path.join(GOLDEN, f"{key}.refs.txt"), encoding="utf-8") as fh:
        return [line for line in fh.read().splitlines() if line]


# --- the 18 payloads ----------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_the_resolved_payload_is_franks_payload_in_franks_order(key, payloads):
    assert [p.name for p in payloads[key]] == _golden_refs(key)


@pytest.mark.parametrize("key", KEYS)
def test_the_first_payload_image_is_the_canon_face(key, payloads):
    """The prose calls the FIRST image the face authority, so primary must lead."""
    assert payloads[key][0].name == os.path.basename(FRANK["references"]["canon_face"])


@pytest.mark.parametrize("key", KEYS)
def test_the_two_style_anchors_follow_in_declared_order(key, payloads):
    want = [os.path.basename(a) for a in FRANK["references"]["style_anchors"]]
    assert [p.name for p in payloads[key][1:3]] == want


@pytest.mark.parametrize("key", WITH_ANCHOR)
def test_a_clothing_anchor_adds_a_fourth_image_last(key, payloads):
    assert len(payloads[key]) == 4, [p.name for p in payloads[key]]
    assert payloads[key][3].name == STICKERS[key]["clothing_anchor"]


@pytest.mark.parametrize("key", WITHOUT_ANCHOR)
def test_a_null_clothing_anchor_yields_exactly_three(key, payloads):
    assert len(payloads[key]) == 3, [p.name for p in payloads[key]]


# --- the fixture actually exercises both shapes -------------------------------

def test_both_the_three_and_four_image_cases_occur():
    """Measured 2026-08-03: 12 stickers carry a clothing_anchor, 6 are null. If the
    fixture ever covered only one shape, the count assertions above would be
    vacuous for the other."""
    assert len(WITH_ANCHOR) == 12
    assert len(WITHOUT_ANCHOR) == 6
    assert len(KEYS) == 18


def test_every_payload_image_exists_on_disk(payloads):
    """`primary_reference` and `entry_reference_paths` both WARN-and-SKIP a missing
    file, so a dead path would shorten a payload rather than fail — which would
    make a length assertion pass for the wrong reason if the fixture were thin."""
    for key, paths in payloads.items():
        assert paths, key
        for p in paths:
            assert p.is_file(), (key, str(p))


def test_no_payload_repeats_an_image(payloads):
    """The style anchors are themselves sticker masters (the set references its own
    output), so a mapping that reused `images_dir` carelessly could attach the same
    file twice — which changes what the model sees."""
    for key, paths in payloads.items():
        names = [p.name for p in paths]
        assert len(names) == len(set(names)), (key, names)
