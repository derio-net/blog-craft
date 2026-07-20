#!/usr/bin/env python3
"""Validate a .blog-craft.yaml config (schema + layer-resolution invariants, spec §4/§4.1).

Accepts schema versions 2..5 (the migration ladder's rungs); v4/v5 additions —
site_dir, _select, character_sheet, named composition_orders — are validated
whenever present. The engine hardcodes no layer vocabulary (spec D1), so no
layer NAME implies a shape.

Library: `validate_config(cfg: dict) -> list[str]` (empty == valid).
CLI:     `validate_config.py --check <path>` (exit 0 valid, 1 invalid).
"""
from __future__ import annotations

import sys

RESERVED_SCENE = "scene"
SERIES_INDEX_STYLES = frozenset({"cards", "table", "none"})
IMAGE_OPTIMIZE_FORMATS = frozenset({"webp"})
REQUIRED_TOP = ("project", "image", "series", "voice")
ACCEPTED_VERSIONS = (2, 3, 4, 5)


def _validate_select(name: str, select, errors: list[str]) -> None:
    """`_select` is a list of steps; each step a field name or list of names."""
    if not isinstance(select, list):
        errors.append(f"image.layers.{name}._select must be a list of steps")
        return
    for step in select:
        if isinstance(step, str):
            continue
        if isinstance(step, list) and step and all(isinstance(f, str) for f in step):
            continue
        errors.append(
            f"image.layers.{name}._select steps must be strings or lists of strings"
        )
        return


def validate_config(cfg: dict) -> list[str]:
    errors: list[str] = []

    if not isinstance(cfg, dict):
        return ["config is not a mapping"]

    if cfg.get("version") not in ACCEPTED_VERSIONS:
        errors.append(
            f"version must be one of {list(ACCEPTED_VERSIONS)} (got {cfg.get('version')!r})"
        )

    for key in REQUIRED_TOP:
        if key not in cfg:
            errors.append(f"missing required top-level key: {key}")

    # v4: optional site_dir — where the Hugo site lives relative to the config
    site_dir = cfg.get("site_dir")
    if site_dir is not None:
        if not isinstance(site_dir, str) or site_dir.startswith("/"):
            errors.append("site_dir must be a relative path string")

    image = cfg.get("image")
    if not isinstance(image, dict):
        errors.append("image block missing or not a mapping")
        return errors  # nothing else resolvable without image

    if "layers" not in image:
        errors.append("missing required key: image.layers")

    order = image.get("composition_order")
    orders = image.get("composition_orders")
    layers = image.get("layers")

    if order is None and orders is None:
        errors.append(
            "missing required key: image.composition_order (v4) or image.composition_orders (v5)"
        )
    if order is not None and not isinstance(order, list):
        errors.append("image.composition_order must be a list")
        order = None
    if orders is not None and not isinstance(orders, dict):
        errors.append("image.composition_orders must be a mapping of name -> token list")
        orders = None
    if layers is not None and not isinstance(layers, dict):
        errors.append("image.layers must be a mapping")
        layers = None

    # scene is reserved: resolves from the per-image entry's scene text, never a layer.
    if isinstance(layers, dict) and RESERVED_SCENE in layers:
        errors.append(f"image.layers must not define the reserved name '{RESERVED_SCENE}'")

    # every order (the v4 single or each v5 named one): tokens resolve, scene present
    named_orders: dict = {}
    if isinstance(order, list):
        named_orders["composition_order"] = order
    if isinstance(orders, dict):
        for oname, toks in orders.items():
            if not isinstance(toks, list) or not all(isinstance(t, str) for t in toks):
                errors.append(f"image.composition_orders.{oname} must be a list of token strings")
            else:
                named_orders[f"composition_orders.{oname}"] = toks
    for oname, toks in named_orders.items():
        if RESERVED_SCENE not in toks:
            errors.append(f"image.{oname} must include the reserved '{RESERVED_SCENE}'")
        if isinstance(layers, dict):
            for tok in toks:
                if tok == RESERVED_SCENE:
                    continue
                base = tok.split("[", 1)[0]
                if base not in layers:
                    errors.append(
                        f"image.{oname} names '{tok}' but image.layers has no such layer"
                    )

    # v4: any dict layer may declare a `_select` walk — validate its shape
    if isinstance(layers, dict):
        for name, layer in layers.items():
            if isinstance(layer, dict) and "_select" in layer:
                _validate_select(name, layer["_select"], errors)

    # v4: optional image.character_sheet.layers — the character-defining layers
    cs = image.get("character_sheet")
    if cs is not None:
        if not isinstance(cs, dict):
            errors.append("image.character_sheet must be a mapping")
        else:
            cs_layers = cs.get("layers")
            if cs_layers is not None and (
                not isinstance(cs_layers, list)
                or not all(isinstance(x, str) for x in cs_layers)
            ):
                errors.append("image.character_sheet.layers must be a list of layer names")

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
