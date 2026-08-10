"""Shared fixture builders for the sticker golden + reference tests (stickers P5).

Not a test module (pytest ignores the leading underscore). It exists so the
**mechanical derivation** of the 18 v5 entries from frank's vendored
`stickers.yaml` lives in exactly one place: `test_stickers_golden.py` and
`test_stickers_references.py` must compose and resolve references from the SAME
entries, or neither proves anything about the other.

Deriving the entries mechanically rather than hand-writing 18 of them is what
makes the golden test a proof instead of a transcription check (spec §7) — and
it is the same transform `tools/migrate_stickers.py` implements in phase 6.

The layer PROSE is not derived here: it lives in the committed fixture config
`tests/fixtures/stickers/blog-craft.yaml`, which is the shape frank pastes into
his own `.blog-craft.yaml`. `test_the_fixture_layers_are_franks_prose_verbatim`
pins that file's five prose layers byte-for-byte against the vendored yaml, so a
"tidied" reflow of the prose fails loudly instead of quietly invalidating every
golden.
"""
from __future__ import annotations

import os
import shutil

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(_ROOT, "tests/fixtures/stickers")
VENDORED = os.path.join(FIXTURES, "frank-stickers.yaml")
CONFIG = os.path.join(FIXTURES, "blog-craft.yaml")
GOLDEN = os.path.join(FIXTURES, "golden")
ENGINE_DIR = os.path.join(_ROOT, "templates/hugo-hextra/scripts")

# Transcribed from frank's `compose_prompt` (generate-stickers.py:49-54). The
# counter-intuitive element is LAST: the border spec follows `scene`, because the
# sticker finish is described after the scene it frames. Swapping those two
# yields a prompt that reads perfectly well and is not frank's.
STICKER_ORDER = [
    "sticker_base_character",
    "sticker_atmosphere",
    "sticker_reference_guidance",
    "sticker_face_pins",
    "clothing",
    "sticker_mood",
    "scene",
    "sticker_border_spec",
]

# frank's five top-level prose keys -> the namespaced layer they become. They MUST
# be renamed: sticker `base_character` says the head is "NOT a hard blocky /
# square flat-top" while frank's COVER `base_character` says "flat-top hair" —
# the two contradict each other and cannot share a layer name (spec §Findings 2).
PROSE_LAYERS = {
    "sticker_base_character": "base_character",
    "sticker_atmosphere": "sticker_atmosphere",
    "sticker_reference_guidance": "reference_guidance",
    "sticker_face_pins": "face_pins",
    "sticker_border_spec": "border_spec",
}

MOOD_TEMPLATE = "Frank's expression: {}."


def frank_config() -> dict:
    with open(VENDORED, encoding="utf-8") as fh:
        return yaml.safe_load(fh.read())


def fixture_config() -> dict:
    with open(CONFIG, encoding="utf-8") as fh:
        return yaml.safe_load(fh.read())


def sticker_keys() -> list[str]:
    return [s["key"] for s in frank_config()["stickers"]]


def reference_paths(frank: dict, s: dict) -> list[str]:
    """frank's payload, as blog-root-relative paths, primary FIRST.

    frank's `scene_refs` (generate-stickers.py:57-65) builds
    `[canon_face, *style_anchors, subjects_dir/clothing_anchor?]` and resolves
    each against his REPO ROOT. blog-craft resolves against the BLOG ROOT
    (`cfg_path.parent`), and frank's paths are already repo-root-relative, so the
    strings carry over unchanged.
    """
    refs = [frank["references"]["canon_face"]]
    refs += list(frank["references"]["style_anchors"])
    anchor = s.get("clothing_anchor")
    if anchor:
        refs.append(f"{frank['references']['subjects_dir']}/{anchor}")
    return refs


def sticker_entries(frank: dict, images_dir: str) -> list[dict]:
    """frank's 18 sticker records as v5 `composition` entries (spec §5b).

    Every field of the mapping is load-bearing:

    - `order` is the BRACKETED reference `composition_orders[sticker]`. A bare
      `sticker` is not a synonym: `_ORDER_REF` (generate-images.py:99) only
      matches the bracketed form, an unmatched string resolves to `[]`,
      `compose([])` is `""`, and `main()` SKIPS an entry whose prompt is empty —
      so the wrong spelling means all 18 stickers, no output, exit code 0
      (journal `p4-order-sticker-must-be-bracketed-reference`).
    - the mood modifier is `sticker_mood`, not `mood`: `_resolve_modifier` looks
      up `entry.get(<layer name>)`, and the frame lives on its own layer so it
      cannot double-frame frank's ~84 covers (journal
      `p1-mood-template-regresses-frank-covers`).
    - `scene` goes in `composition.scene`, which `selector_source` exposes to the
      reserved `scene` token as `prompt`.
    - `sheet` / `pos` ride along untouched for `build-sheets.py`.
    """
    out = []
    for s in frank["stickers"]:
        key = s["key"]
        refs = reference_paths(frank, s)
        out.append({
            "key": key,
            "description": s["description"],
            "output": f"{images_dir}/sticker-{key}.png",
            "aspect_ratio": frank.get("defaults", {}).get("aspect_ratio", "1:1"),
            "sheet": s["sheet"],
            "pos": s["pos"],
            "composition": {
                "order": "composition_orders[sticker]",
                "modifiers": {"sticker_mood": s["mood"], "clothing": s["clothing"]},
                "scene": s["scene"],
                "reference_images": {"primary": refs[0], "clothing": refs[1:]},
            },
        })
    return out


def _png(path) -> None:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (30, 120, 60)).save(path)


def build_blog(tmp_path, entries=None, copy_scripts=True):
    """A blog root carrying the fixture config, the 18 derived entries, and a
    synthetic file at every reference path.

    Two details that are not incidental:

    - the reference PNGs must EXIST. `primary_reference` and
      `entry_reference_paths` both `is_file()`-gate and WARN-and-skip a miss, and
      `validate_images` flags a dead path — so a fixture without them would
      silently prove the wrong thing about payload order.
    - `shadow.blog-craft.yaml` is a copy of the fixture config with
      `image.prompts_file` pointed at the STICKER prompts file. That is exactly
      what the shipped `generate-stickers.py` shim does at runtime (journal
      `p4-shim-shadow-config-and-regen-location`), and it is what lets the
      engine's own `--print-prompt` / `validate_images.py --config` read sticker
      entries: neither has a prompts-file flag. It sits in the SAME directory as
      the real config, because the engine resolves the blog root as
      `cfg_path.parent`.
    """
    cfg = fixture_config()
    frank = frank_config()
    stk = cfg["features"]["stickers"]
    entries = sticker_entries(frank, stk["images_dir"]) if entries is None else entries

    blog = tmp_path / "blog-root"
    blog.mkdir(exist_ok=True)
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False,
                                                          allow_unicode=True))
    (blog / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": []}))

    prompts = blog / stk["prompts_file"]
    prompts.parent.mkdir(parents=True, exist_ok=True)
    prompts.write_text(yaml.safe_dump({"images": entries}, sort_keys=False,
                                      allow_unicode=True))

    shadow_cfg = fixture_config()
    shadow_cfg["image"]["prompts_file"] = stk["prompts_file"]
    (blog / "shadow.blog-craft.yaml").write_text(
        yaml.safe_dump(shadow_cfg, sort_keys=False, allow_unicode=True))

    for e in entries:
        ri = e["composition"]["reference_images"]
        for rel in [ri["primary"], *ri["clothing"]]:
            p = blog / rel
            if not p.is_file():
                _png(p)

    if copy_scripts:
        sdir = blog / "scripts"
        sdir.mkdir(exist_ok=True)
        for n in ("generate-images.py", "compose.py"):
            shutil.copy(os.path.join(ENGINE_DIR, n), sdir / n)
    return blog
