#!/usr/bin/env python3
"""Schema migration: v6 -> v7 (sticker generation surface, default OFF).

Seeds `features.stickers = {enabled: false}` so the block exists to be
discovered and edited, without turning the capability on anywhere.

Default OFF is the deliberate difference from the previous rung. v5 -> v6
shipped `features.mermaid_view: true` because it was a *rendering fix* every
blog wanted the moment it existed. A sticker set is per-blog **content** — 18
hand-curated die-cut images that only frank has — so enabling it by default
would render `generate-stickers.py` and `build-sheets.py` into gondor and stoa,
where there is nothing for them to generate. An operator opts in by writing
`enabled: true` plus the prompts/images/sheets paths.

Uses setdefault semantics: a blog that has already configured
`features.stickers` (including an explicit `enabled: true`) keeps every key it
wrote. A migration that flips an operator's explicit value is a bug, not a fix.

Pure + idempotent (only runs on version==6): no filesystem access, no mutation
of the input dict. Nothing about a blog's sticker *files* happens here —
migrating frank's images and prompts is `tools/migrate_stickers.py`'s job.
"""
from __future__ import annotations

FROM_VERSION = 6
TO_VERSION = 7


def migrate(cfg: dict) -> dict:
    if cfg.get("version") != FROM_VERSION:
        raise ValueError(f"006_to_007 expects version {FROM_VERSION}, got {cfg.get('version')!r}")
    out = dict(cfg)
    out["version"] = TO_VERSION
    features = dict(out.get("features") or {})
    features.setdefault("stickers", {"enabled": False})
    out["features"] = features
    return out
