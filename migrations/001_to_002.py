#!/usr/bin/env python3
"""Schema migration: .blog-craft.yaml v1 -> v2 (pure, idempotent-per-version).

v1's `metaphor.*` becomes `image.layers` with a synthesized `composition_order`
that reproduces the v1 generation order (base_style + persona + visual_constants
+ scene + reference_guidance); `image_gen.*` folds into `image`; series gain an
explicit `content_type: posts`; `features` is normalized.

Library: `migrate(cfg: dict) -> dict`.
CLI:     `001_to_002.py <in.yaml>`  (prints migrated YAML to stdout).
"""
from __future__ import annotations

import sys

FROM_VERSION = 1
TO_VERSION = 2
COMPOSITION_ORDER = ["base_style", "persona", "visual_constants", "scene", "reference_guidance"]


def migrate(cfg: dict) -> dict:
    if cfg.get("version") != FROM_VERSION:
        raise ValueError(f"001_to_002 expects version {FROM_VERSION}, got {cfg.get('version')!r}")

    m = cfg.get("metaphor", {}) or {}
    ig = cfg.get("image_gen", {}) or {}
    feats = cfg.get("features", {}) or {}

    image = {
        "provider": ig.get("provider", "gemini"),
        "model": ig.get("model", "gemini-3-pro-image-preview"),
        "api_key_env": ig.get("api_key_env", "GEMINI_API_KEY"),
        "output_dir": ig.get("output_dir", "static/images"),
        "prompts_file": ig.get("prompts_file", "prompt_for_images.yaml"),
        "reference_pool": ".reference-pool",
        "curation": {"count_default": 1, "archive_cap": 30, "contact_sheet": True},
        "composition_order": list(COMPOSITION_ORDER),
        "layers": {
            "base_style": m.get("base_style"),
            "persona": m.get("persona"),
            "visual_constants": m.get("visual_constants", []),
            "reference_guidance": m.get("reference_guidance"),
        },
    }
    if m.get("reference_image"):
        image["reference_image"] = m["reference_image"]

    out = {
        "version": TO_VERSION,
        "project": cfg.get("project", {}),
        "image": image,
        "series": [dict(s, content_type=s.get("content_type", "posts"))
                   for s in (cfg.get("series") or [])],
        "voice": cfg.get("voice"),
        "features": {
            "series_overview_posts": feats.get("series_overview_posts", True),
            "read_tracker": bool(feats.get("read_tracker", False)),
            "roadmap": {"enabled": bool(feats.get("roadmap_shortcode", False))},
        },
    }
    if cfg.get("blog_craft_version"):
        out["blog_craft_version"] = cfg["blog_craft_version"]
    return out


if __name__ == "__main__":
    import yaml
    if len(sys.argv) != 2:
        print("usage: 001_to_002.py <in.yaml>", file=sys.stderr)
        raise SystemExit(2)
    with open(sys.argv[1]) as f:
        src = yaml.safe_load(f)
    yaml.safe_dump(migrate(src), sys.stdout, sort_keys=True, default_flow_style=False, allow_unicode=True)
