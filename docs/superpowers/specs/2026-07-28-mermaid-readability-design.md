# Mermaid readability — natural-size rendering, a framed scroller, and a blocking width gate

- **Branch:** `feat/mermaid-diagram-zoom`
- **Date:** 2026-07-28
- **Type:** feature (template feature module + validator + config + docs)

## Problem

Mermaid diagrams in blog-craft blogs are frequently unreadable. Mermaid renders
with `useMaxWidth: true`, which scales the SVG down to fit its container. Hextra
caps the content column at ~672px, so a diagram whose natural width is 2139px
renders at **31% scale** — label text authored at 14px paints at 4.4px.

This is not a wide-screen problem. The Hextra shell caps at `80rem` regardless
of display, so the content column is 672px on a 1440px laptop and on a 3840px
4K panel alike. Every reader gets the same 31%.

A second, independent failure sits behind it: **the diagram gates are not
running.** In frank, `quality.mermaid_syntax: false` disables the syntax gate,
and the CI step that invokes it prints `mermaid syntax check disabled` and exits
`0` — indistinguishable from a pass in an Actions log. That flag was set for a
documented reason (a 50-finding backlog, frank `77e68e37`), but the effect is
that diagram defects ship unreported.

## Measurements (frank, 2026-07-28)

All 182 ` ```mermaid ` blocks in frank were rendered headless with the site's own
mermaid bundle and their natural widths measured. **0 render failures.**

| n | min | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|---|
| 182 | 183px | 632px | 873px | 1246px | 1622px | 2394px |

Content column for comparison: **672px**. Median diagram is 1.3× the column;
p90 is 2.4×; the widest is 3.6×.

Orientation correlates with width but does not determine it — every sampled `LR`
diagram overflowed (4/4, median 1644px), while `TD` overflowed in 3/5 with one
`TD` diagram at 1895px. Direction is a strong signal, not a rule.

## Goal

Every diagram renders at its authored size, so its text is legible on every
viewport, with a visible affordance when it does not fit; and diagrams too wide
to follow by scrolling fail the build.

## Non-goals

- **No layout/column-width changes.** Widening the shell was prototyped and
  rejected — see Decisions.
- **No click-to-zoom / pan overlay.** Natural-size rendering solves the
  legibility problem without JS, without CSP surface, and without colliding with
  `mermaid-csp-init`'s `MutationObserver`.
- **No mechanical `LR` → `TD` rewrite** of existing diagrams.
- **No baseline / allowlist** for the width gate.

## Decisions (operator, 2026-07-27/28)

1. **Fix the container, not the diagram scale.** Diagrams render at natural size
   inside a horizontally scrollable, framed container — "like tables do."
2. **No per-page column width.** Widening the shell on diagram pages (via
   `:has(.mermaid)`) was prototyped and measured: it takes the diagram to 100%
   scale on a 4K, but the sidebar and TOC then shift 320–736px whenever the
   reader navigates between a diagram page and a prose page. Rejected: *"I don't
   want the column width to change from one page to the next."* Global widening
   was also rejected — measured on a diagram-free page it moves prose 736px left
   and detaches centred components (`roadmap`, `series-index`) from their
   headings.
3. **Default on, opt-out available.** `features.mermaid_view` defaults `true`;
   a blog sets it `false` to keep the current behaviour.
4. **The width gate blocks from day one. No baseline.** Explicitly chosen to
   *"force a focused effort to fix them."* Landing red is intended.
5. **The gate measures, it does not guess.** Width is read from a real render,
   not inferred from direction and node counts.

## Architecture

### 1. Config surface

`.blog-craft.yaml` gains two keys and the schema goes to **v6**:

```yaml
version: 6
features:
  mermaid_view: true          # default true; false restores pre-feature rendering
quality:
  mermaid_max_width: 1400     # px; 0 disables the gate
```

`tools/validate_config.py` extends `ACCEPTED_VERSIONS` to `2..6` and type-checks
both keys. `migrations/005_to_006.py` bumps `version` and writes
`features.mermaid_view: true`, so existing blogs adopt the fix through `/update`
rather than by hand-editing.

**Budget derivation.** `1400` is ~2× the 672px content column: a diagram needing
more than two column-widths of scrolling cannot be held in the reader's head.
Against frank this blocks **35 of 182 (19%)** on day one. The number is
config-visible precisely so it can be argued with; the day-one impact at other
budgets is 1200px → 46, 1600px → 20, 1800px → 9.

### 2. Feature module — `templates/features/mermaid-view/`

Packaged as a feature module rather than an addition to `custom.css.tmpl`.
`custom.css` is a merge-class file and frank has already rewritten blog-craft's
`.content .mermaid` block as `& .mermaid` nesting (76 rules, 174 lines divergent
— frank `77e68e37`); a new file is a clean add through `/update`'s 3-way merge
instead of a guaranteed conflict across three blogs.

```
templates/features/mermaid-view/
  assets/css/mermaid-view.css
  layouts/_markup/render-codeblock-mermaid.html
```

#### `mermaid-view.css`

```css
.content .mermaid { overflow-x: auto; /* frame + affordances */ }
.content .mermaid svg { width: 200rem; }
```

The one-line trick that makes this self-scaling: mermaid writes
`style="max-width: <natural>px"` **inline** on the SVG. Inline styles beat
stylesheet rules and `max-width` always beats `width`, so `width: 200rem`
resolves to `min(200rem, natural)`. Every diagram renders at exactly its
authored size and never larger — a 428px diagram stays 428px and never scrolls;
a 2139px one renders full-size in the scroller. No per-diagram tuning, and
because it is CSS it survives the dark/light re-render that
`mermaid-init.js:48-61` performs by resetting `innerHTML`.

Frame: 1px border, 8px radius, padding and a background tint, all derived with
`color-mix(in srgb, currentColor …)` so one rule serves both themes.

**Scroll affordances (two, because one is not enough).**

- *Persistent scrollbar.* macOS defaults to overlay scrollbars, which paint
  nothing at rest — measured `offsetHeight - clientHeight == 0`, i.e. the
  diagram is silently truncated with no cue. Only `-webkit-appearance: none` on
  `::-webkit-scrollbar` opts out; sizing alone does not. Verified: the same
  measurement becomes `9px` once set.
- *Scroll shadows.* `background-attachment: local, local, scroll, scroll` —
  cover gradients in the frame colour scroll with the content and uncover
  edge shadows pinned to the scroller. Self-cancelling at both ends, no JS.

`scrollbar-width`/`scrollbar-color` are gated behind
`@supports not selector(::-webkit-scrollbar)`. Set alongside the WebKit
pseudo-elements they **win and disable them**, silently restoring the invisible
overlay bar — the failure is quiet, so the feature query is load-bearing, not
tidiness.

#### `render-codeblock-mermaid.html`

Overrides Hextra's hook to add `tabindex="0"` to the scroll container, without
which the diagram is unreachable by keyboard (WCAG 2.1). Must reproduce the
theme hook's `role="img"`, its `aria-label`, and its
`.Page.Store.Set "hasMermaid" true` — the theme's own scripts partial depends on
that store. blog-craft already overrides `_markup/render-image.html`, so this is
an established pattern; it does pin the feature to the theme hook's shape and
needs re-checking on a Hextra bump.

#### Wiring

- `head-end.html`: `{{- with resources.Get "css/mermaid-view.css" }}` before
  `custom.css`, so a blog can still override the frame in its own stylesheet.
- `bootstrap-render.sh`: a `[3h]` block gated on `features.mermaid_view` — the
  next free label after `[3c]` read-tracker, `[3d]` analytics, `[3e]`
  layer-palette, `[3f]` glossary, `[3g]` mermaid-csp-init.

### 3. The width gate — `scripts/validate_mermaid_layout.mjs`

Runs **after** `hugo build`, against `public/`.

- **Source of truth is built HTML, not markdown.** Extracting from
  `public/**/*.html` covers diagrams emitted by shortcodes (e.g.
  `papers/landscape` quadrantCharts) — precisely where frank's real breakage was
  (`77e68e37`: abbr markers injected into quadrantChart source, missed by every
  markdown-level check). Findings are reported by page URL + block index rather
  than `file:line`, matching frank's existing rendered-output validator.
- **Renders with the site's own mermaid bundle** from `public/js/mermaid.*.js`,
  so measured widths are exactly what readers get. Measuring with a different
  mermaid build would measure a different site.
- **Width is read from the rendered SVG's inline `max-width`** — the same value
  the CSS rule keys off, so gate and renderer cannot disagree.
- Fails with a per-diagram report: page, index, measured width, budget, overage.
- Per-diagram opt-out: a `%% blog-craft: wide-ok — <reason>` comment in the
  mermaid source (`%%` is a mermaid comment), mirroring `diagram_exempt:`.

#### Why a real browser is required (verified, not assumed)

frank already ships a Node mermaid validator (`scripts/validate-mermaid.mjs`,
`mermaid.parse()` under jsdom) and the obvious move is to extend it. **That does
not work for width**, and the reason is structural rather than fixable:

| jsdom probe | Result |
|---|---|
| `SVGTextElement.getBBox` | **not present** |
| `getComputedTextLength` | **not present** |
| `getBoundingClientRect()` | `{width: 0, height: 0}` |
| `mermaid.render()` under jsdom | throws `ReferenceError: CSSStyleSheet is not defined` |

Mermaid derives every node's size from text measurement, so under jsdom each
node is zero-width and any resulting diagram width is meaningless. **Syntax
checking is legitimately a jsdom job — width measurement is not.** The two gates
therefore stay separate tools rather than merging.

#### Runner capabilities (verified against the ubuntu-24.04 image manifest)

| Requirement | `ubuntu-latest` |
|---|---|
| Google Chrome | 150.0.7871.128, preinstalled |
| Chromium | 150.0.7871.0, preinstalled |
| Node.js / npm | 22.23.1 / 10.9.8, preinstalled |
| `CHROME_BIN` | **not defined** — only `CHROMEWEBDRIVER`, `EDGEWEBDRIVER`, `GECKOWEBDRIVER` |

Every workflow involved already runs `ubuntu-latest` (blog-craft's own CI,
`blog-ci.yml.tmpl`, and frank's live workflow), and none uses `setup-node`.
So no browser download and no toolchain install is needed — but the Chrome
executable must be **discovered, not hardcoded**, since the image defines no
browser path variable and `ubuntu-latest` will roll to a newer image. Resolution
order: `$CHROME_BIN` → `google-chrome` → `google-chrome-stable` → `chromium` →
`chromium-browser`, failing with an actionable message naming what it looked
for. Headless Chrome on a runner needs `--no-sandbox --disable-dev-shm-usage`.

#### Zero-dependency implementation (recommended)

Because the gate loads **the built site's own mermaid bundle** from
`public/js/mermaid.*.js`, it needs no `mermaid` npm package. And Node 22 ships a
global `WebSocket`, so it can drive headless Chrome over CDP directly — meaning
the gate can be a **single dependency-free `.mjs`**: no `package.json`, no
`npm install` step, no supply-chain surface added to any consumer blog. This is
the same shape as the prototype that rendered all 182 of frank's diagrams with
zero failures, and it matches the repo's existing posture (vendored asciinema,
same-origin assets, no third parties in the request path).

The alternative is `puppeteer-core` (pure JS, no bundled browser) for less
hand-rolled CDP code, at the cost of a `package.json` + `npm install` in every
adopting blog's CI. **Recommendation: zero-dependency.** The plan should take
the CDP route first and fall back only if driving Chrome proves fiddly.

CI: a new step in `blog-ci.yml.tmpl` after the Hugo build, gated on
`quality.mermaid_max_width > 0`, so a blog that sets `0` invokes no browser at
all.

### 4. Disabled gates must be loud

`tools/validate_mermaid.py` (and the new layout gate) currently print a neutral
line and exit `0` when switched off. They will instead emit a clearly marked
`GATE DISABLED` warning **and the count of findings they would have reported**,
so a disabled gate advertises how far behind it is. frank's own commit states
the principle: *"a gate nobody runs reports nothing, including how far behind
you are."* Both the canonical tool and its
`templates/hugo-hextra/scripts/` mirror change together; `tests/unit/test_mirrors.py`
enforces the pair.

### 5. Authoring guidance

The writing skills gain a diagram-orientation rule: **default to `flowchart TD`;
reserve `LR` for short, genuinely left-to-right pipelines.** Grounded in the
measurements above, and stated as a strong default rather than a rule, because
the data shows direction predicts width without determining it.

No mechanical rewrite of existing diagrams: direction often carries meaning,
subgraph layout changes substantially under `TD`, and converting one is — per
frank `77e68e37` — "a judgement call about which node the edge should really
point at." The gate reports; authors fix.

### 6. Bootstrap and update paths

- New blog: `.blog-craft.yaml.tmpl` ships `version: 6` and
  `features.mermaid_view: true`; bootstrap materializes the module.
- Existing blog: `/update` runs `005_to_006.py`, which writes the flag; the
  module arrives as new files (clean adds, no merge conflict).
- Known interaction: blog-craft#61 — `.github/**` is materialized under
  `site_dir`, so every update re-adds an inert workflow copy at
  `<site_dir>/.github/workflows/`. The new CI step must land in the **repo-root**
  workflow, which is the only one GitHub executes.

## Testing

Unit (`tests/unit/`):
- `test_config_schema.py` — v6 accepted; both new keys type-checked; v5 config
  still valid.
- `test_migration_ladder.py` — `005_to_006.py` bumps version and sets the flag;
  idempotent; refuses a wrong `FROM_VERSION`.
- `test_mermaid_layout_gate.py` — over-budget diagram fails; at-budget passes;
  `wide-ok` comment waives; `mermaid_max_width: 0` disables; report format;
  browser discovery falls through the candidate list and fails with an
  actionable message when none is found.
- `test_mermaid_validator.py` — disabled gate prints `GATE DISABLED` **and** the
  would-be finding count, still exits 0.
- `test_mirrors.py` — new validator + its shipped mirror registered.
- `test_mermaid_view_hugo.py` — module materializes only when flagged;
  stylesheet is linked before `custom.css`; the render hook preserves
  `hasMermaid` and adds `tabindex="0"`.

CSS behaviour is asserted where it is falsifiable in a build (asset present,
link order, hook output). The rendered affordances were verified by measurement
during design (`offsetHeight - clientHeight`: 0 → 9px) and are re-verified in
the Test Plan.

## Docs

- `docs/CONFIG.md` — new **§12 Mermaid rendering (`features.mermaid_view`)** and
  a `quality.mermaid_max_width` row in §7, including the budget derivation and
  the `wide-ok` opt-out.
- `CHANGELOG.md` — feature entry plus an explicit note that the width gate lands
  **blocking with no baseline**, and that adopting blogs should expect red CI
  until their diagram backlog is worked down.

## Test Plan

Post-merge, on frank (operator-run, needs a real browser and a real deploy):

1. **Legibility.** Open `/docs/building/22-health-monitoring/` (natural width
   ≈2130px; 2139 measured in-page, 2132 measured headless — mermaid's text
   metrics vary slightly with the rendering context, which is why the gate
   renders with the site's own bundle). Diagram renders at authored size; every
   node label readable without zooming.
2. **Affordance.** On the same page, without touching the trackpad, a scrollbar
   is visible at the bottom of the frame and a shadow marks the right edge; the
   shadow disappears when scrolled fully right.
3. **Small diagrams unaffected.** Open `/docs/operating/09-multi-tenancy/`
   (428px). Diagram is not enlarged, the frame is present, no scrollbar appears.
4. **Keyboard.** Tab to the diagram container; left/right arrows scroll it.
5. **Theme survival.** Toggle dark/light on a diagram page; after mermaid
   re-renders, the frame, the natural size and the scrollbar all persist.
6. **Gate blocks.** With `quality.mermaid_max_width: 1400`, CI fails and names
   the 35 over-budget diagrams with measured widths.
7. **Gate waiver.** Add `%% blog-craft: wide-ok — …` to one of them; CI reports
   34.
8. **Disabled gate is loud.** Set `mermaid_max_width: 0`; the step exits 0 but
   prints `GATE DISABLED` and the count it would have reported.

## Acceptance rows (matrix backfill — same PR)

- **MMD-1** — "Every mermaid diagram renders at its authored size regardless of
  column width" — `unit=blog-craft:tests/unit/test_mermaid_view_hugo.py`.
- **MMD-2** — "A diagram wider than the column exposes a visible scroll
  affordance without user interaction" — Test Plan step 2, `manual`.
- **MMD-3** — "A diagram exceeding the width budget fails the build" —
  `unit=blog-craft:tests/unit/test_mermaid_layout_gate.py`.
- **MMD-4** — "A disabled diagram gate reports that it is disabled and what it
  would have found" — `unit=blog-craft:tests/unit/test_mermaid_validator.py`.
- **MMD-5** — "A blog can opt out of the framed scroller and keep prior
  rendering" — `unit=blog-craft:tests/unit/test_mermaid_view_hugo.py`.
- **MMD-6** — "A diagram container is scrollable by keyboard" — Test Plan
  step 4, `manual`.

## Out of scope

- Column/shell width changes of any kind (decision 2).
- Click-to-zoom, pan, or lightbox overlays.
- Auto-converting `LR` diagrams to `TD`.
- Clearing frank's 50-finding `mermaid_syntax` backlog, or flipping
  `quality.mermaid_syntax: true` — consumer-blog content work, tracked
  separately.
- The unimplemented `2026-07-16-diagram-quality-gate-design.md` (*requires* a
  diagram in how-to/tutorial posts) — adjacent, independent, untouched.
