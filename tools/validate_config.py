#!/usr/bin/env python3
"""Validate a .blog-craft.yaml v2 config (schema + layer-resolution invariants, spec §4/§4.1).

Library: `validate_config(cfg: dict) -> list[str]` (empty == valid).
CLI:     `validate_config.py --check <path>` (exit 0 valid, 1 invalid).
"""
from __future__ import annotations

import sys

RESERVED_SCENE = "scene"
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

    series = cfg.get("series")
    if series is not None:
        if not isinstance(series, list):
            errors.append("series must be a list")
        else:
            for i, s in enumerate(series):
                if not isinstance(s, dict) or "key" not in s or "title" not in s:
                    errors.append(f"series[{i}] must have at least key + title")

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
