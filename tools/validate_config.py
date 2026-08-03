#!/usr/bin/env python3
"""Validate a .blog-craft.yaml config (schema + layer-resolution invariants, spec §4/§4.1).

Accepts schema versions 2..7 (the migration ladder's rungs); v4/v5 additions —
site_dir, _select, character_sheet, named composition_orders — are validated
whenever present, and the v6 addition — features.mermaid_view (diagram
rendering at natural size) + quality.mermaid_max_width (the width gate's
budget) — likewise, as are the v7 additions: features.stickers (the sticker
generation surface) and image.fallback_model / image.timeout_ms (generate-
images.py's retry target and HTTP timeout). The engine hardcodes no layer
vocabulary (spec D1), so no layer NAME implies a shape. A dict layer's
`_template` (the `str.format` frame stickers need) is likewise validated
whenever present.

Library: `validate_config(cfg: dict) -> list[str]` (empty == valid).
CLI:     `validate_config.py --check <path>` (exit 0 valid, 1 invalid).
"""
from __future__ import annotations

import sys

RESERVED_SCENE = "scene"
SERIES_INDEX_STYLES = frozenset({"cards", "table", "none"})
IMAGE_OPTIMIZE_FORMATS = frozenset({"webp"})
REQUIRED_TOP = ("project", "image", "series", "voice")
ACCEPTED_VERSIONS = (2, 3, 4, 5, 6, 7)
STICKER_PATH_KEYS = ("prompts_file", "images_dir", "sheets_dir")


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


def _validate_template(name: str, tmpl, errors: list[str]) -> None:
    """`_template` is a `str.format` frame: exactly one `{}`, no other braces.

    Checked here because the failure is otherwise invisible until IMAGE-
    GENERATION time, with a paid API call already in flight: a frame with no
    `{}` silently drops the resolved value from the prompt, two `{}` raise
    IndexError (compose supplies one positional arg), and a stray `{`/`}`
    raises ValueError from str.format. Cheap at validation, expensive mid-run.
    """
    where = f"image.layers.{name}._template"
    if not isinstance(tmpl, str):
        errors.append(f"{where} must be a string with exactly one '{{}}' (got {tmpl!r})")
        return
    if tmpl.count("{}") != 1 or tmpl.count("{") != 1 or tmpl.count("}") != 1:
        errors.append(
            f"{where} must contain exactly one '{{}}' and no other braces (got {tmpl!r})"
        )


def _validate_stickers(stk, errors: list[str]) -> None:
    """`features.stickers` — the v7 sticker-generation surface.

    Optional at every accepted version: the 88 existing blog configs have no
    such block, and `migrations/006_to_007.py` seeds only `{enabled: false}`.
    So the three path keys are required exactly when the capability is switched
    ON — a disabled block is allowed to be a stub. `sheet` geometry, in
    contrast, is checked whenever present: bad numbers there are nonsense
    regardless of whether generation runs, and `build-sheets.py` would only
    discover them at print time.

    Like `_template`, checks fire on the key being PRESENT rather than
    non-None, so a half-written `enabled:` (i.e. None) cannot silently do
    nothing. `sheet.size` stays unvalidated on purpose — the paper vocabulary
    belongs to build-sheets.py, which must reject a size it cannot lay out.
    """
    if not isinstance(stk, dict):
        errors.append("features.stickers must be a mapping")
        return

    enabled = stk.get("enabled")
    if "enabled" in stk and not isinstance(enabled, bool):
        errors.append(
            f"features.stickers.enabled must be a boolean (got {enabled!r})"
        )

    if enabled is True:
        for key in STICKER_PATH_KEYS:
            val = stk.get(key)
            if not isinstance(val, str) or not val.strip():
                errors.append(
                    f"features.stickers.{key} must be a non-empty path string "
                    f"when features.stickers.enabled is true (got {val!r})"
                )

    if "sheet" in stk:
        sheet = stk["sheet"]
        if not isinstance(sheet, dict):
            errors.append(f"features.stickers.sheet must be a mapping (got {sheet!r})")
            return
        for key in ("dpi", "gutter"):
            if key in sheet:
                v = sheet[key]
                if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                    errors.append(
                        f"features.stickers.sheet.{key} must be a positive int (got {v!r})"
                    )
        if "grid" in sheet:
            grid = sheet["grid"]
            if (
                not isinstance(grid, list)
                or len(grid) != 2
                or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in grid)
            ):
                errors.append(
                    "features.stickers.sheet.grid must be a list of two positive ints "
                    f"[cols, rows] (got {grid!r})"
                )


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

    # v4: any dict layer may declare a `_select` walk — validate its shape.
    # stickers: it may also declare `_template`, the frame applied to whatever
    # the layer resolves to (compose.py `_apply_template`).
    if isinstance(layers, dict):
        for name, layer in layers.items():
            if not isinstance(layer, dict):
                continue
            if "_select" in layer:
                _validate_select(name, layer["_select"], errors)
            if "_template" in layer:
                _validate_template(name, layer["_template"], errors)

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

    # v7: image.fallback_model — the model generate-images.py retries on when the
    # primary raises or returns no image part; image.timeout_ms — the HttpOptions
    # timeout in MILLISECONDS. Both optional: absent leaves the pre-v7 behaviour
    # (single model, SDK default timeout) byte-for-byte unchanged. Checked on
    # PRESENCE, so `fallback_model:` with an empty value is an error, not a
    # silent no-op — the failure would otherwise surface mid-generation.
    if "fallback_model" in image:
        fb = image["fallback_model"]
        if not isinstance(fb, str) or not fb.strip():
            errors.append(f"image.fallback_model must be a non-empty string (got {fb!r})")
    if "timeout_ms" in image:
        tmo = image["timeout_ms"]
        if isinstance(tmo, bool) or not isinstance(tmo, int) or tmo <= 0:
            errors.append(f"image.timeout_ms must be a positive int of milliseconds (got {tmo!r})")

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

    # v6: quality.mermaid_max_width — the width gate's px budget. 0 disables the
    # gate (documented, not an error); bool is guarded first since bool is an
    # int subclass (mirrors quality.lint.thresholds below).
    if isinstance(quality, dict) and "mermaid_max_width" in quality:
        w = quality["mermaid_max_width"]
        if isinstance(w, bool) or not isinstance(w, (int, float)) or w < 0:
            errors.append(
                f"quality.mermaid_max_width must be a non-negative number (got {w!r})"
            )

    # optional quality.lint block (ai-tells lint layer): enabled bool; severities
    # a mapping whose VALUES are fail|warn|off; thresholds a mapping whose VALUES
    # are numbers. Unknown severity/threshold KEYS are allowed — forward-
    # compatible with checks this validator doesn't know about yet.
    if isinstance(quality, dict) and "lint" in quality:
        lint = quality["lint"]
        if not isinstance(lint, dict):
            errors.append("quality.lint must be a mapping")
        else:
            if "enabled" in lint and not isinstance(lint["enabled"], bool):
                errors.append("quality.lint.enabled must be a boolean")
            sev = lint.get("severities")
            if sev is not None:
                if not isinstance(sev, dict):
                    errors.append("quality.lint.severities must be a mapping")
                else:
                    for k, v in sev.items():
                        if v not in ("fail", "warn", "off"):
                            errors.append(
                                f"quality.lint.severities.{k} must be one of "
                                f"fail | warn | off (got {v!r})"
                            )
            thr = lint.get("thresholds")
            if thr is not None:
                if not isinstance(thr, dict):
                    errors.append("quality.lint.thresholds must be a mapping")
                else:
                    for k, v in thr.items():
                        if isinstance(v, bool) or not isinstance(v, (int, float)):
                            errors.append(
                                f"quality.lint.thresholds.{k} must be a number "
                                f"(got {v!r})"
                            )

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

    # optional features.glossary block: the abbreviation glossary (§9). Only this
    # sub-block is checked — the rest of `features` stays unvalidated. Without it a
    # typo (`enable: true`) silently disables the whole feature with no signal.
    feats = cfg.get("features")
    if isinstance(feats, dict) and "glossary" in feats:
        gl = feats["glossary"]
        if not isinstance(gl, dict):
            errors.append("features.glossary must be a mapping")
        else:
            for key in ("enabled", "first_occurrence_only"):
                if key in gl and not isinstance(gl[key], bool):
                    errors.append(f"features.glossary.{key} must be a boolean")

    # v6: features.mermaid_view — diagrams render at natural size in a framed
    # scroller. Only checked when PRESENT; absent is legal and means true,
    # resolved at render time (bootstrap-render.sh), not here.
    if isinstance(feats, dict) and "mermaid_view" in feats:
        if not isinstance(feats["mermaid_view"], bool):
            errors.append("features.mermaid_view must be a boolean")

    # v7: features.stickers — sticker generation, default OFF. Absent is legal at
    # every version (the capability is optional); see _validate_stickers.
    if isinstance(feats, dict) and "stickers" in feats:
        _validate_stickers(feats["stickers"], errors)

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
