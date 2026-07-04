# blog-craft image optimization (WebP pipeline) — plan

Add a Hugo build-time image-optimization pipeline to blog-craft, so materialized
blogs serve WebP derivatives (responsive `srcset`, width-capped) instead of raw
full-resolution PNGs — while the PNG masters stay untouched. Opt-in via a
`.blog-craft.yaml` `image.optimize` knob, mirroring the series-index `style` knob.

Spec: `docs/superpowers/specs/2026-07-04--image-optimization--webp-pipeline-design.md`
(cross-repo; frank adoption is a sibling plan/PR, gated on this merge).

## Grounded in measurement

- frank's live blog: 90.9 MB, 152 files, 100% PNG, no optimization; empirical
  WebP wins 77–99% (≈ 90 MB → ~10–20 MB).
- Hugo Extended (local v0.162.1+extended) required for WebP encode — CI must be
  verified extended (Phase 3).
- Three image classes, three code paths: covers (`.Resources.GetMatch`, bundle),
  inline (`screenshot` + markdown `![]()`, bundle), banners (`static/images/…`,
  NOT processable → relocate to `assets/`).

## Shape — three agentic TDD phases

1. **Config knob.** Validate an optional `image.optimize` sub-block
   (enabled/format/quality/max_width/banner_max_width) and thread it into
   `[params.imageOptimize]`.
2. **Core partial + wiring.** A reusable `opt-image.html` partial (webp primary
   ≤ max-width + responsive `srcset` + explicit width/height; passthrough when
   disabled / nil / svg-gif), wired into the markdown render hook, the
   `screenshot` shortcode, `docs/list.html` covers, and `site-banner.html`
   (switched to an `assets/` resource, with the `assets/images/` convention
   shipped as `.gitkeep`).
3. **Docs + verification.** CONFIG.md; a Hugo-Extended CI guard; full unit +
   smoke suite building the image fixtures (optimize on → webp+srcset; off →
   raw-PNG passthrough).

## Why this shape

- **Partial-first, then wiring** — every consumer (render hook, shortcode, cover,
  banner) routes through one `opt-image` partial, so the optimization logic lives
  in exactly one place and each wiring step is a thin adapter.
- **Opt-in, passthrough-safe** — `enabled: false`/absent, remote URLs, and
  SVG/GIF all fall through to a raw `<img>`, so the pipeline is inert until a
  blog opts in and never breaks a non-raster or remote image.
- **Banners are the hard path** — `static/` isn't Hugo-processable, so this is
  the one place that needs an `assets/` relocation convention; kept nil-safe so a
  bannerless blog renders nothing.
- **No deploy** — blog-craft is a plugin repo; CI/smoke only. frank's adoption
  (sibling PR) carries the live Test Plan.

## Out of scope

AVIF (WebP-only). Shrinking the committed PNG masters. Changing the gemini
image-generation pipeline. Frank's adoption lives in the sibling frank plan/PR.
