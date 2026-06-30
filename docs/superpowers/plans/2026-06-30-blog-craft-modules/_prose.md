# Modules — Papers content-type + Theme/CSS params (Group 2, P3+P4)

Second of three grouped plans. Builds on Group 1 (config v2 + image engine).
Adds the two remaining feature surfaces frank needs that stoa does not: the
**papers opt-in content-type** and the **theme/layout/CSS parameterization**.
Both are config-gated so stoa (papers off, simpler features) is unaffected — the
Group 1 stoa smoke and the Group 3 stoa golden test are the regression guards.

## Phase 1 — Papers content-type (opt-in)

The single heaviest feature, packaged as `templates/content-type-papers/` +
`tools/` validators + a `papers` skill, all materialized only when a series
declares `content_type: papers`. Templates (paper bundle skeleton, dossier),
three config-driven validators (dossier gate thresholds, frontmatter/weight,
dossier→data sync), the six shortcodes + cross-link partials, and the ported
skill. `smoke-papers` is the gate: scaffold → dossier (pass + fail cases) →
validators → Hugo build → and an assertion that the stoa config materializes
none of it.

## Phase 2 — Theme / layout / CSS params

Makes frank's remaining theme surface config-driven without baking frank
specifics into blog-craft: `custom.css` split into a shipped structural base +
a config-injected palette; `read-tracker.js` and goatcounter analytics gated by
`features`; the roadmap as a **data-driven** shortcode (frank's ~24KB of
specifics live in `data/roadmap.yaml`, a content path); per-series banners; and
the weight-zero hookify guard shipped so every blog inherits the Hextra
sidebar-trap protection.

## TDD discipline & gates

Every task is test-first. P1 gate: `smoke-papers` green + stoa materializes
nothing. P2 gate: per-feature smoke + `hugo --buildDrafts` clean with features
on and off.

## Sequencing

Depends on Group 1 (config v2, manifest, image engine) — this PR is stacked on
`feat/blog-craft-foundation`, re-targeted to `main` once Group 1 merges.
Group 3 (reproduction harness + updater) follows. frank's P7 is a separate run.
