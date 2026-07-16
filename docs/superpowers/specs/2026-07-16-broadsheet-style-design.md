# Broadsheet editorial style + self-contained font embedding for /explainers

- **Issue:** derio-net/blog-craft#22
- **Branch:** `feat/explainer-broadsheet-style`
- **Date:** 2026-07-16
- **Type:** feature (renderer + bundled assets + docs + tests)

## Goal

Make a standalone explainer look genuinely *published*, not templated: a
bespoke `broadsheet` editorial theme, self-contained web-font embedding, and
per-style palette-matched Mermaid. Reduced scope — the issue's part 3(a)
(themed Mermaid) already shipped in `743c431`; what remained was a new style,
`--embed-fonts`, and making the Mermaid palette travel *per style*.

## Operator decisions (batched Q&A, 2026-07-16)

1. **Font source — bundle woff2 in the repo.** A pinned fetch script
   (`tools/fetch_broadsheet_fonts.py`) downloads Fraunces + Newsreader (latin +
   latin-ext, roman + italic, ~744K) into
   `templates/content-type-explainers/shared/fonts/broadsheet/`; `--embed-fonts`
   inlines them. Turnkey, reproducible, offline, unit-testable — chosen over
   render-time Google Fonts fetch (a network dependency in a build tool, at odds
   with reproducibility).
2. **Scope — include the schematics doc.** `references/schematics.md`
   (CSS-only schematic primitives) ships in this PR alongside the style + fonts.

## Design

### `tools/render_explainer.py` (+ byte-mirror)

- `_THEMES["broadsheet"]` — warm-dark editorial CSS to the issue's design
  tokens (`--brass`/`--teal` two-accent system, Fraunces display / Newsreader
  body, hairline rules) plus the component vocabulary (`.eyebrow`, `.pull`,
  `.ledger`, `.rv`).
- **Per-style Mermaid.** `_MERMAID_VARS` re-keyed from an `is_dark` *boolean* to
  a **style-name** map (light/minimal/dark/broadsheet), fallback light.
  `_mermaid_init(style)` and `_wrap(..., style, font_css)` thread the style
  through — fixing the latent bug where a warm theme would get the light
  diagram palette.
- **`--embed-fonts` / `--fonts-dir`.** `_embed_fonts_css(dir)` reads
  `broadsheet-fonts.css` and rewrites each local `url(*.woff2) format('woff2')`
  to a base64 `data:` URI. `_resolve_fonts_dir` auto-locates the bundle for both
  the materialized-blog layout (`scripts/../fonts/broadsheet`) and the plugin
  `tools/` layout. Missing fonts → warn + fall back to system serifs (never
  crash).
- **Reveal.** A 6-line IntersectionObserver adds `.in` to `.rv` elements —
  emitted for `broadsheet` only; a no-op when no `.rv` nodes exist.

All edits mirror to
`templates/content-type-explainers/shared/scripts/render_explainer.py`
(`tests/unit/test_mirrors.py` enforces byte-identity).

### Bundled assets

`templates/content-type-explainers/shared/fonts/broadsheet/`: 8 woff2 +
`broadsheet-fonts.css` (generated) + `OFL.txt` (SIL OFL 1.1, both families).

### Docs

`skills/explainers/SKILL.md` standalone section documents `broadsheet`,
`--embed-fonts`, the bundle location, and `references/schematics.md`.

## Test Plan

Renderer + assets; **no deployment** → no post-merge Test Plan. Verification is
the unit suite (`tests/unit/test_explainers_broadsheet.py`, new):

- broadsheet registered; CSS carries the display serif + both accents.
- render(broadsheet) applies the theme, converts the fence, emits the reveal
  observer; other styles do NOT emit it.
- per-style Mermaid: broadsheet ≠ light; unknown style → light fallback.
- `_embed_fonts_css` inlines base64 and drops every local woff2 url.
- `--embed-fonts` end-to-end produces a `data:` URI; missing dir falls back
  without crashing.
- bundled-fonts sanity: every woff2 referenced by the committed CSS exists +
  OFL present; real bundle embeds ≥ 4 faces.
- Full suite: **172 passed**.

## Acceptance rows (matrix backfill — same PR)

- **explainer-broadsheet-style** (ci) — broadsheet style + per-style Mermaid.
- **explainer-embed-fonts** (ci) — `--embed-fonts` inlines the bundled fonts.

## Out of scope

- Render-time font fetching (declined for reproducibility).
- Auto-applying `.pull`/`.ledger`/`.eyebrow` to generated markdown (they're for
  hand-authored HTML; documented, not injected).
