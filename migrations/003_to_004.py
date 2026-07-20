#!/usr/bin/env python3
"""Schema migration: v3 -> v4 (spec D7 — the dead vocabularies become config data).

Output-preserving by construction:
  1. `metaphor.*` (old bootstrap-blog vocabulary) -> `image.layers` +
     `image.reference_image`; `composition_order` (when absent) is set to the
     exact order the old blog-post skill hand-concatenated, so composed
     prompts are byte-identical. Existing `image.layers` keys win.
  2. `image_gen.*` (old settings vocabulary) merges into `image.*`
     (existing `image.*` keys win).
  3. A dict layer named `torso` without `_select` gains the engine rule that
     used to be hardcoded: `_select: [[torso, series], torso_variant]`.
     (`mood`'s old behaviour — named lookup with free-form passthrough — IS
     the v4 default for any dict layer, so it needs nothing.)

Pure + idempotent (only runs on version==3).
"""
from __future__ import annotations

FROM_VERSION = 3
TO_VERSION = 4

# the concatenation order the pre-v4 blog-post skill hand-composed
OLD_SKILL_ORDER = ["base_style", "persona", "visual_constants", "scene", "reference_guidance"]
METAPHOR_LAYER_KEYS = ("base_style", "persona", "visual_constants", "reference_guidance")
TORSO_SELECT = [["torso", "series"], "torso_variant"]


def migrate(cfg: dict) -> dict:
    if cfg.get("version") != FROM_VERSION:
        raise ValueError(f"003_to_004 expects version {FROM_VERSION}, got {cfg.get('version')!r}")
    out = dict(cfg)
    out["version"] = TO_VERSION
    image = dict(out.get("image") or {})

    metaphor = out.pop("metaphor", None)
    if isinstance(metaphor, dict):
        moved = {k: metaphor[k] for k in METAPHOR_LAYER_KEYS if metaphor.get(k) is not None}
        layers = {**moved, **(image.get("layers") or {})}  # existing layers win
        if layers:
            image["layers"] = layers
        if metaphor.get("reference_image") and "reference_image" not in image:
            image["reference_image"] = metaphor["reference_image"]
        # the old skill's hand-concat order — only when the metaphor block
        # actually contributed prose (an empty block must not invent an order)
        if moved and "composition_order" not in image:
            image["composition_order"] = list(OLD_SKILL_ORDER)

    image_gen = out.pop("image_gen", None)
    if isinstance(image_gen, dict):
        image = {**image_gen, **image}                    # existing image.* wins

    layers = image.get("layers")
    if isinstance(layers, dict):
        torso = layers.get("torso")
        if isinstance(torso, dict) and "_select" not in torso:
            layers = dict(layers)
            layers["torso"] = {"_select": [list(s) if isinstance(s, list) else s
                                           for s in TORSO_SELECT], **torso}
            image["layers"] = layers

    if image:
        out["image"] = image
    return out
