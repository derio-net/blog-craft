# blog-craft image optimization (WebP pipeline) + frank adoption — design

**Date:** 2026-07-04
**Status:** Complete
**Repos:** derio-net/blog-craft (mechanism) + derio-net/frank (adoption)

## Problem

blog-craft-materialized blogs serve **raw full-resolution PNGs** — no
optimization pipeline exists (the build is `hugo --minify`, which does not touch
images). Measured on frank's live blog:

- **90.9 MB of images, 152 files, 100% PNG** — no WebP/AVIF/JPEG anywhere.
- Several wildly oversized: `banner-operating.png` 5088×832 / **7.0 MB**; an
  `awx-login` screenshot 3478×2018 / **2.1 MB**; **82 covers ~0.85 MB each =
  60.5 MB**.
- On a slow connection this dominates page load.

Empirical WebP conversion wins (`cwebp`): a cover **872 KB→200 KB (−77%)**; a
banner **7.1 MB→68 KB @≤1600px (−99%)**; a screenshot **2.1 MB→44 KB (−98%)**.
Site-wide ≈ **90 MB → ~10–20 MB**.

## Operator decisions (batched Q&A, 2026-07-04)

1. **Format → WebP only** (universal support; the measured wins are WebP; AVIF's
   marginal extra gain isn't worth `<picture>` complexity + slower builds).
2. **Scope → covers + inline + banners** — all three classes, including the
   banner `static`→`assets` relocation.
3. **Frank timing → same run (cross-repo)** — blog-craft mechanism AND frank
   adoption in this run: two PRs, frank's gated on the blog-craft merge.
4. **Test Plan → payload + visual on live blog** (per-page transfer drops sharply
   AND images still render crisply, light + dark).

## What is grounded (measured, not assumed)

- **Hugo Extended** (v0.162.1+extended locally) is required for WebP encode — a
  CI running non-extended Hugo would silently fail encoding. Verified locally;
  **must be re-verified in blog-craft CI + frank's `deploy-blog.yml`**.
- **Three image classes, three code paths** (measured in blog-craft's templates):
  - **Covers** — `docs/list.html` uses `.Resources.GetMatch "cover.*"` → a
    **page-bundle resource** (Hugo-processable).
  - **Inline** — the `screenshot.html` shortcode (`.Page.Resources.GetMatch`) +
    markdown `![]()` (no render hook today → raw `<img>`). Bundle resources.
  - **Banners** — `site-banner.html` loads `static/images/banner-<track>.png`
    via `relURL`. **`static/` is NOT Hugo-processable** — must become an `assets/`
    resource (`resources.Get`). blog-craft ships NO banner images (they are
    per-blog content), so relocation is a **frank-side** move.
- **Config schema:** `image` is a REQUIRED top-level block (generation config:
  `composition_order`, `layers`, …). An optional `image.optimize` sub-block is
  the clean home for the knob (validated like `series_index`).

## Design — blog-craft (the mechanism)

### 1. Config knob — `image.optimize`

Optional sub-block of the existing `image:` block in `.blog-craft.yaml`:

```yaml
image:
  # …existing generation config…
  optimize:
    enabled: true          # default false (opt-in; absent → passthrough)
    format: webp           # only webp accepted for now
    quality: 82            # 1–100
    max_width: 1600        # cap for covers + inline (px)
    banner_max_width: 2560 # banners are wide; separate cap
```

`tools/validate_config.py` gains optional validation: `optimize` (if present) is
a mapping; `enabled` bool; `format` ∈ {`webp`}; `quality` int 1–100; `max_width`
/ `banner_max_width` positive ints. Absent → valid (passthrough).

`hugo.toml.tmpl` threads it into `[params.imageOptimize]`
(`enabled`/`format`/`quality`/`maxWidth`/`bannerMaxWidth`), mirroring the
`seriesIndex` param wiring.

### 2. Core partial — `layouts/partials/opt-image.html`

The single reusable unit. Input dict:
`{resource, alt, class, loading, maxWidth, sizes}`. Behaviour:

- If `imageOptimize.enabled` is false/absent, or the resource is nil, or its
  media subtype is `svg`/`gif` (don't rasterize/animate) → **passthrough** raw
  `<img>` (RelPermalink or the original src), preserving `alt`/`loading`/`class`.
- Else, with a processable raster resource:
  - Emit a `format`-encoded primary at ≤`maxWidth` (`.Resize "<w>x webp qN"` when
    wider than the cap, else `.Process "webp qN"`).
  - Emit a responsive `srcset` at the subset of `{480, 960, maxWidth}` widths ≤
    the source width (each a `.Resize`), so small screens fetch small images.
  - Set explicit `width`/`height` (from the primary) to prevent layout shift,
    plus `loading` (default `lazy`) and `alt`.

### 3. Wiring (blog-craft templates)

- **Markdown inline** — NEW `layouts/_markup/render-image.html`: resolve
  `.Page.Resources.GetMatch .Destination`; a bundle resource → `opt-image`
  partial; a remote/absolute URL → passthrough `<img>`.
- **`screenshot.html`** — route the resolved `$img` through `opt-image` (keep the
  `<a href>` linking to the full-res original; the `<img>` becomes optimized).
- **`docs/list.html` cover** — route `$cover` through `opt-image`.
- **`site-banner.html`** — switch to `resources.Get (printf "images/banner-%s.png"
  $track)` (reads `assets/`); route through `opt-image` with `bannerMaxWidth` and
  `loading="eager"` (banners are above-the-fold). Nil resource → render nothing
  (graceful when a blog has no banner for a track).
- Ship `assets/images/.gitkeep` so the `assets/images/` convention exists.

### 4. Docs + tests

- `docs/CONFIG.md` — document `image.optimize` + the assets/-banner convention.
- Unit: validator schema cases; `hugo.toml` param render.
- Smoke: a fixture blog (cover + inline `![]()` + a `screenshot` + an
  `assets/images/banner-*.png`) with `image.optimize.enabled: true`, built with
  `hugo --minify`, asserting: WebP derivatives are generated under
  `resources/` / output `_gen`; the rendered `<img>` carries a `.webp` `src` +
  `srcset` + `width`/`height`; the primary is width-capped; and an
  `enabled: false` fixture renders raw-PNG passthrough (no `.webp`). A byte-size
  assertion (optimized < original) where practical.

## Design — frank (adoption, gated on blog-craft merge)

Frank is on blog-craft's tracked update flow (established in the series-index
re-sync). Adoption:

1. Add `image.optimize.enabled: true` (+ quality/max-width) to frank's
   `.blog-craft.yaml`; bump `blog_craft_version` to the blog-craft **merge SHA**.
2. Pull the new/changed templates via the curated update (framework replaces:
   `opt-image.html`, `_markup/render-image.html`, `screenshot.html`,
   `docs/list.html`, `site-banner.html`, `assets/images/.gitkeep`).
3. **Relocate banners** `static/images/banner-*.png` → `assets/images/` (frank
   content move) so Hugo can process them. Confirm frank's post-cover path (a
   frank `single.html`, if any) routes covers through `opt-image` too.
4. Verify: `hugo --minify` clean; WebP derivatives generated; the rendered
   per-page image payload drops sharply; masters (PNG) untouched.

**Cross-repo sequencing:** the frank PR cannot fully verify against
blog-craft `main` until blog-craft merges. It is built by vendoring the templates
from the blog-craft branch, delivered as a **draft gated on the blog-craft
merge**, and finalized (re-pin `blog_craft_version` to the merge SHA + re-run the
curated update) once blog-craft is on `main`.

## Test Plan (post-merge, operator-driven — frank)

Frank deploys a live blog (`blog.derio.net/frank` + GitHub Pages). After both
merge + deploy:

1. Load a representative **post** and a **section page**; in DevTools Network,
   confirm the per-page image transfer dropped sharply (PNG → WebP, smaller).
2. Confirm images still render **crisply — no visible quality loss** — in both
   light and dark; spot-check a cover, an inline screenshot, and a banner.
3. Confirm the committed PNG **masters are untouched** (Hugo generated the WebP
   derivatives at build; source unchanged).

## Non-goals

- AVIF (WebP-only per the Q&A).
- Shrinking/relocating the committed PNG **masters** (the 90 MB stays in-repo;
  Hugo processes at build). A repo-slimming pass is a separate follow-up.
- Any change to frank's gemini image-**generation** pipeline (it still emits PNG
  masters; optimization is purely a build-time output concern).

## Risks & mitigations

- **CI Hugo not Extended** → WebP encode silently no-ops/fails. Verify
  `hugo version` shows `+extended` in blog-craft CI and frank's `deploy-blog.yml`;
  pin/upgrade if not.
- **Banner relocation misses a reference** → a nil `resources.Get` renders no
  banner. `site-banner.html` handles nil gracefully; the frank move is verified
  by a build + visual check.
- **Render hook breaks remote/SVG images** → the hook passes through
  non-bundle/SVG/GIF sources unchanged; covered by a fixture case.
- **Build time / `resources/` cache growth** → WebP derivatives are cached in
  Hugo's `resources/`; first build is slower, incremental is cached.

## Implementation Plans

| Plan | Target repo | Status | Notes |
|------|-------------|--------|-------|
| 2026-07-04-image-optimization | `derio-net/blog-craft` | `2026-07-04-image-optimization` | — |
