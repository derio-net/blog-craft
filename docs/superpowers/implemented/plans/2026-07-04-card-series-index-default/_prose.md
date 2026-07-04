# blog-craft — card series-index default + opt-in palette — plan

Make the card `series-index` blog-craft's default (frank #605's design, standardised),
with `table`/`none` fallbacks via a `series_index.style` config knob, and generalise
frank's layer palette (generator + `layer_palette.yaml` data convention + `layer:`
frontmatter) as an opt-in that also colours `roadmap.html`.

See the spec: `docs/superpowers/specs/2026-07-04--series-index--card-default-and-palette-design.md`.

## Shape

Three agentic phases, TDD red → green:

1. **Style switch.** A `series_index.style` config (cards default / table / none), validated
   and threaded to `site.Params.seriesIndex.style`; the shortcode branches — table (preserved),
   none (empty), cards (frank's timeline, neutral colour for now).
2. **Opt-in palette.** Generalise `gen-layer-palette.py` to be registry-driven (reads
   `series_index.layers` codes+names, writes names into the palette data); wire the cards to
   colour + name-tag from `site.Data.layer_palette` (neutral when absent); rework `roadmap.html`
   onto the same palette (retire `--rm-accent`).
3. **Bootstrap + docs + verify.** Bootstrap generates the palette when layers are declared;
   docs cover the knob + opt-in; full unit/smoke + `hugo --minify` over the style fixtures.

## Why this shape

- **frank untouched** — it already ships its own card copy; re-sync is a later step.
- **papers-roadmap out of scope** — frank-specific (roster + status).
- **stoa needs no edit** — it adopts `cards` on its next build (operator decision).
- **No blog deploy** — blog-craft is a plugin repo; CI tests only, no post-merge Test Plan.
- The generalised generator differs from frank's (registry-driven + names-in-data) so any
  blog can opt in; frank re-syncs to it later.
