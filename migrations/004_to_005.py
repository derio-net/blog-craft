#!/usr/bin/env python3
"""Schema migration: v4 -> v5 (named composition orders).

The single `image.composition_order` becomes the named map
`image.composition_orders` with the old list as the `hero` order — the default
every entry composes with unless it names another. Layer tables and entries
are untouched here: entry restructuring (prompt -> composition.scene,
selectors -> composition.modifiers, references -> composition.reference_images)
is the prompts-file migration, `tools/migrate_prompts.py`, because entries
live outside the config.

Pure + idempotent (only runs on version==4).
"""
from __future__ import annotations

FROM_VERSION = 4
TO_VERSION = 5


def migrate(cfg: dict) -> dict:
    if cfg.get("version") != FROM_VERSION:
        raise ValueError(f"004_to_005 expects version {FROM_VERSION}, got {cfg.get('version')!r}")
    out = dict(cfg)
    out["version"] = TO_VERSION
    image = dict(out.get("image") or {})
    if "composition_orders" not in image and isinstance(image.get("composition_order"), list):
        image["composition_orders"] = {"hero": list(image.pop("composition_order"))}
        out["image"] = image
    return out
