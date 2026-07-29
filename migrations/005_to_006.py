#!/usr/bin/env python3
"""Schema migration: v5 -> v6 (mermaid readability: default-on natural-size rendering).

Diagrams currently render at ~31% scale because mermaid's `useMaxWidth` shrinks
the SVG to Hextra's 672px content column. The fix ships as `features.mermaid_view`,
default true, so existing blogs adopt it through `/update` rather than by
hand-editing `.blog-craft.yaml`.

Uses setdefault semantics: a blog that has already set
`features.mermaid_view: false` (an explicit opt-out) keeps false. A migration
that re-enables an operator's opt-out is a bug, not a fix.

Pure + idempotent (only runs on version==5).
"""
from __future__ import annotations

FROM_VERSION = 5
TO_VERSION = 6


def migrate(cfg: dict) -> dict:
    if cfg.get("version") != FROM_VERSION:
        raise ValueError(f"005_to_006 expects version {FROM_VERSION}, got {cfg.get('version')!r}")
    out = dict(cfg)
    out["version"] = TO_VERSION
    features = dict(out.get("features") or {})
    features.setdefault("mermaid_view", True)
    out["features"] = features
    return out
