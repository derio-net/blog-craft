#!/usr/bin/env python3
"""Schema migration: v2 -> v3.

Example forward migration proving the ladder handles multi-step upgrades:
fills `features.css.mermaid_palette` with the shipped defaults when a v2 config
omitted it, so every v3 blog carries an explicit palette. Pure + idempotent
(only runs on version==2).
"""
from __future__ import annotations

FROM_VERSION = 2
TO_VERSION = 3

DEFAULT_PALETTE = {"node": "#1f3a5f", "stroke": "#4dabf7", "edge": "#51cf66", "label": "#eaf2ff"}


def migrate(cfg: dict) -> dict:
    if cfg.get("version") != FROM_VERSION:
        raise ValueError(f"002_to_003 expects version {FROM_VERSION}, got {cfg.get('version')!r}")
    out = dict(cfg)
    out["version"] = TO_VERSION
    feats = dict(out.get("features") or {})
    css = dict(feats.get("css") or {})
    if not css.get("mermaid_palette"):
        css["mermaid_palette"] = dict(DEFAULT_PALETTE)
    feats["css"] = css
    out["features"] = feats
    return out
