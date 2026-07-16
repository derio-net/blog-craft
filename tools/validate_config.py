#!/usr/bin/env python3
"""Validate a .blog-craft.yaml v2 config (schema + layer-resolution invariants, spec §4/§4.1).

Library: `validate_config(cfg: dict) -> list[str]` (empty == valid).
CLI:     `validate_config.py --check <path>` (exit 0 valid, 1 invalid).
"""
from __future__ import annotations

import sys

RESERVED_SCENE = "scene"
SERIES_INDEX_STYLES = frozenset({"cards", "table", "none"})
IMAGE_OPTIMIZE_FORMATS = frozenset({"webp"})
REQUIRED_TOP = ("project", "image", "series", "voice")
REQUIRED_IMAGE = ("composition_order", "layers")
# Layers that, when named in composition_order, must be a mapping (indexed-table),
# selected per-image (torso by series+index, mood by name).
INDEXED_TABLE_LAYERS = ("torso", "mood")


def validate_config(cfg: dict) -> list[str]:
    errors: list[str] = []

    if not isinstance(cfg, dict):
        return ["config is not a mapping"]

    if cfg.get("version") != 2:
        errors.append(f"version must be 2 (got {cfg.get('version')!r})")

    for key in REQUIRED_TOP:
        if key not in cfg:
            errors.append(f"missing required top-level key: {key}")

    image = cfg.get("image")
    if not isinstance(image, dict):
        errors.append("image block missing or not a mapping")
        return errors  # nothing else resolvable without image

    for key in REQUIRED_IMAGE:
        if key not in image:
            errors.append(f"missing required key: image.{key}")

    order = image.get("composition_order")
    layers = image.get("layers")

    if order is not None and not isinstance(order, list):
        errors.append("image.composition_order must be a list")
        order = None
    if layers is not None and not isinstance(layers, dict):
        errors.append("image.layers must be a mapping")
        layers = None

    # scene is reserved: resolves from the per-image entry's `prompt`, never a layer.
    if isinstance(layers, dict) and RESERVED_SCENE in layers:
        errors.append(f"image.layers must not define the reserved name '{RESERVED_SCENE}'")
    if isinstance(order, list) and RESERVED_SCENE not in order:
        errors.append(f"image.composition_order must include the reserved '{RESERVED_SCENE}'")

    # every composition_order name (except scene) resolves in layers
    if isinstance(order, list) and isinstance(layers, dict):
        for name in order:
            if name == RESERVED_SCENE:
                continue
            if name not in layers:
                errors.append(
                    f"image.composition_order names '{name}' but image.layers has no such layer"
                )
                continue
            if name in INDEXED_TABLE_LAYERS and not isinstance(layers[name], dict):
                errors.append(
                    f"image.layers.{name} must be a mapping (indexed-table layer)"
                )

    # optional image.optimize block: the WebP build-time pipeline knob. Absent →
    # passthrough (raw images). enabled bool; format ∈ {webp}; quality int 1–100;
    # max_width / banner_max_width positive ints.
    opt = image.get("optimize")
    if opt is not None:
        if not isinstance(opt, dict):
            errors.append("image.optimize must be a mapping")
        else:
            if "enabled" in opt and not isinstance(opt["enabled"], bool):
                errors.append("image.optimize.enabled must be a boolean")
            fmt = opt.get("format")
            if fmt is not None and fmt not in IMAGE_OPTIMIZE_FORMATS:
                errors.append(
                    f"image.optimize.format must be one of {sorted(IMAGE_OPTIMIZE_FORMATS)} (got {fmt!r})"
                )
            q = opt.get("quality")
            if q is not None and (isinstance(q, bool) or not isinstance(q, int) or not (1 <= q <= 100)):
                errors.append("image.optimize.quality must be an int in 1–100")
            for wk in ("max_width", "banner_max_width"):
                w = opt.get(wk)
                if w is not None and (isinstance(w, bool) or not isinstance(w, int) or w <= 0):
                    errors.append(f"image.optimize.{wk} must be a positive int")

    series = cfg.get("series")
    if series is not None:
        if not isinstance(series, list):
            errors.append("series must be a list")
        else:
            for i, s in enumerate(series):
                if not isinstance(s, dict) or "key" not in s or "title" not in s:
                    errors.append(f"series[{i}] must have at least key + title")

    # optional quality block: mermaid_syntax opt-out (default on) must be a bool.
    quality = cfg.get("quality")
    if isinstance(quality, dict) and "mermaid_syntax" in quality:
        if not isinstance(quality["mermaid_syntax"], bool):
            errors.append("quality.mermaid_syntax must be a boolean")

    # optional series_index block: style cards|table|none (default cards at render
    # time), optional layers registry (opts into layer colour-coding).
    si = cfg.get("series_index")
    if si is not None:
        if not isinstance(si, dict):
            errors.append("series_index must be a mapping")
        else:
            style = si.get("style")
            if style is not None and style not in SERIES_INDEX_STYLES:
                errors.append(
                    f"series_index.style must be one of {sorted(SERIES_INDEX_STYLES)} (got {style!r})"
                )
            layers = si.get("layers")
            if layers is not None:
                if not isinstance(layers, list):
                    errors.append("series_index.layers must be a list of {code, name}")
                else:
                    for i, ly in enumerate(layers):
                        if not isinstance(ly, dict) or "code" not in ly or "name" not in ly:
                            errors.append(f"series_index.layers[{i}] must have code + name")

    return errors


def _main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "--check":
        print("usage: validate_config.py --check <path>", file=sys.stderr)
        return 2
    import yaml  # local import so importing the library needs no yaml

    with open(argv[1]) as f:
        cfg = yaml.safe_load(f)
    errors = validate_config(cfg)
    if errors:
        print(f"INVALID: {argv[1]}", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"OK: {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
