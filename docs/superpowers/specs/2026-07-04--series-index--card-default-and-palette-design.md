# blog-craft — card series-index as default + opt-in layer palette

**Date:** 2026-07-04
**Status:** draft
**Repo:** derio-net/blog-craft
**Upstream source:** derio-net/frank (on `main`) — the card `series-index.html`,
`layer_palette.yaml` + `gen-layer-palette.py`, and the `layer:` frontmatter convention
shipped in frank #605. This standardises that pattern back into blog-craft.

## Problem

blog-craft ships a **plain-table** `series-index` shortcode (blog-craft #10). frank
then built a much richer **card** version (papers-roadmap-style timeline, colour-coded by
layer, full layer-name tag) that reads a shared `layer_palette.yaml`. That card layout
should become blog-craft's **default**, so stoa and future blogs inherit it — with the
table preserved as a fallback and an option to disable the index entirely.

## Goals

- blog-craft's default `series-index` becomes the **card layout**.
- A `series_index.style` config knob selects **`cards`** (default) / **`table`** (the
  current plain table, preserved) / **`none`** (no index).
- The **layer palette is generalised as an opt-in**: blog-craft ships the generator +
  the `layer_palette.yaml` data convention + `layer:` frontmatter support. A blog that
  declares layers gets colour-coded, layer-named cards; a blog with no layers gets tidy
  neutral cards. `roadmap.html` adopts the same palette.
- No stoa edits — stoa **adopts `cards`** on its next build (operator decision).

## Non-goals

- **frank is not changed here.** frank already ships its own (card) copy; a later,
  separate step can re-sync frank to blog-craft's standardised version.
- **papers-roadmap is not added to blog-craft.** It is frank-specific (roster + status).
  Only the `series-index` + generic `roadmap` are in scope.
- No new content-type; no bootstrap flow redesign.

## Design

### 1. Config — `series_index` block (`.blog-craft.yaml` v2)

Add an optional top-level block (absent → all defaults):

```yaml
series_index:
  style: cards          # cards (default) | table | none
  layers:               # optional — declaring layers opts INTO colour-coding
    - { code: hw,  name: "Hardware & Nodes" }
    - { code: net, name: "Networking" }
    # ...
```

- `tools/validate_config.py`: `series_index` optional; if present, `style` ∈
  {`cards`,`table`,`none`} and `layers` (if present) a list of `{code, name}`. Absent
  `style` → `cards`.
- `templates/hugo-hextra/hugo.toml.tmpl`: emit `[params.seriesIndex]` with
  `style = "{{ … | default "cards" }}"` so the shortcode can read `site.Params.seriesIndex.style`.
- No config migration needed — the key is optional with a `cards` default; existing v2
  configs render cards. (`migrate_config.py`/`001_to_002.py` unchanged.)

### 2. `series-index.html` shortcode — style branch

Rework the shipped shortcode to select on `site.Params.seriesIndex.style` (default
`cards`); same page-derived selection (`where … Params.series intersect`, weight-sorted,
host page self-excluded) feeds all styles:

- **`none`** → render nothing.
- **`table`** → the current `<table class="series-index">` (byte-preserved as the fallback).
- **`cards`** → the frank card timeline: per post a card with number badge, linked title,
  `summary` takeaway, and — when the post has a `layer` — a leading full-name layer tag.

**Card colour (opt-in):** if `site.Data.layer_palette` exists and the post has a
`layer`, colour the card's left border + number badge from
`site.Data.layer_palette.layers[<layer>]` (`light`/`dark` + `lt`/`dt` text) and show
`layers[<layer>].name` as the `.tag-layer`. With no palette or no `layer`, the card
renders in a single **neutral accent** and omits the layer tag. (Layer *names* live in
the palette data — not a hardcoded map — so the shortcode is blog-agnostic.)

### 3. Layer palette — generalise the generator + data convention

- `tools/gen-layer-palette.py` (ported from frank, generalised): reads the layer registry
  from the blog's `.blog-craft.yaml` `series_index.layers` (codes **+ names**), emits
  `data/layer_palette.yaml` mapping each `code → { name, light, dark, lt, dt }`. Same
  OKLCH engine: 21-safe unique hues, hue-dependent lightness (no muddy olives), permuted
  order for successive-layer contrast, per-badge text colour. (frank's version hardcodes
  its 21 codes and keeps names in the shortcode; the generalised version is registry-driven
  and carries names in the data.)
- `data/layer_palette.yaml` is the single source of truth for `series-index` **and**
  `roadmap`. It exists only for blogs that opt into layers.

### 4. `roadmap.html` — adopt the palette (opt-in)

Rework blog-craft's `roadmap.html` (currently ~57 `--rm-accent` refs) the way frank's
was: replace the hardcoded per-layer accent rules with a loop over
`site.Data.layer_palette.layers`, retiring the `--rm-accent` scale. When no palette is
present, fall back to a neutral accent (roadmap without layer colours). A layer is then
the same colour in `series-index` and `roadmap`.

### 5. Bootstrap

`tools/bootstrap-render.sh`: when the config declares `series_index.layers`, generate
`data/layer_palette.yaml` (run the generator) as part of materialisation, so an opt-in
blog boots with a ready palette. Blogs without layers materialise no palette (neutral cards).

### 6. Skill / doc updates

- The bootstrap / blog-post skill docs note the `series_index.style` knob and the layer
  opt-in (declare `series_index.layers` → colour-coded cards; regenerate the palette with
  `gen-layer-palette.py` when the layer set changes).

## Testing

blog-craft's `tests/unit` + smoke suite (Hugo build over fixtures):

- **Style switch:** bootstrap a fixture blog and assert `cards` (default) renders
  `<div class="series-index">` cards; `style: table` renders `<table class="series-index">`;
  `style: none` renders no index.
- **Card parity:** cards list exactly the series' posts (fs-derived), weight order,
  host page self-excluded.
- **Layer colouring opt-in:** a fixture with `series_index.layers` + `layer:` frontmatter
  + generated palette → cards carry `layer-<code>` classes, the palette colour, and the
  full-name tag; a fixture WITHOUT layers → neutral cards, no `tag-layer`.
- **Generator:** registry (codes+names) → deterministic `layer_palette.yaml` with names;
  21 unique colours; `gen-layer-palette.py` output reproducible (drift guard).
- **Config validation:** `series_index.style` accepts the three values, rejects others;
  `layers` shape checked.
- **roadmap palette:** with a palette, `roadmap` uses it (no `rm-accent`); without, neutral.
- Full `hugo --minify` clean build over each fixture.

## Rollout

Single blog-craft PR (its own review). No blog deploys from blog-craft (plugin repo,
CI tests only) — no post-merge Test Plan. Follow-ups (separate): re-sync frank to the
standardised card shortcode + registry-driven generator; stoa picks up `cards` on its
next build.

## Implementation Plans

| Plan | Repo | Scope |
|------|------|-------|
| _TBD_ | derio-net/blog-craft | config knob + card/table/none shortcode + generalised palette generator + roadmap adoption + bootstrap + tests + docs |
