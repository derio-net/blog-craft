# Design: Config-driven blog-craft as creator & updater (frank + stoa reproduction)

**Status:** Draft
**Date:** 2026-06-30
**Spec owner repo:** frank (`docs/superpowers/specs/2026-06-30--repo--blog-craft-config-migration-design.md`)
**This copy:** blog-craft (implementation repo for P1–P6)
**Implementation:** blog-craft (P1–P6), frank (P7, deferred)

> This is the implementation-side copy of the umbrella spec brainstormed in
> frank. blog-craft owns phases P1–P6; frank's P7 cutover is a separate,
> later run gated on P1–P6 merging + the reproduction harness going green.

---

## 1. Problem & Goal

Frank's blog tooling (skills, image system, papers/dossier framework,
validators, CI) lives **inline** in the frank repo. blog-craft (v0.1.0) already
exists and has been applied to **stoa-blog** via a `.blog-craft.yaml` config.

**Goal:** make *blog-craft + a per-repo `.blog-craft.yaml`* the single creator
**and updater** of both blogs. Applying it reproduces each blog's full
structure/functionality. frank is the hard target (papers, layered image
system, roadmap, read-tracker, CI); stoa is the easy target + regression guard.

### Acceptance bar

**Structural / tooling parity** — applying blog-craft + a repo's config to an
**empty** repo reproduces the full scaffold (theme, shortcodes, layouts, CSS,
image system, validators, CI). Existing authored posts/cover images are **not**
regenerated (operator-owned content). Acceptance = **structural diff** of the
generated scaffold vs the repo's current non-content files (§7).

### Operator decisions (locked)

1. Fidelity = **tooling/structure parity** (content excluded).
2. Posture = **parity first, migrate frank after** (P1–P6 never touch frank's blog; P7 = deliberate cutover).
3. Papers = **first-class opt-in content-type** (frank on, stoa off).
4. Decomposition = **umbrella spec → sequenced sub-plans** (3 grouped PRs: P1-P2 / P3-P4 / P5-P6).
5. Image composition = **Approach A: config-declared composition order** (§4).
6. Roadmap = **data-driven** (`data/roadmap.yaml`), not a baked template.
7. Schema = **v2 bump** + one-time mechanical stoa config migration.
8. CSS = **split** into shipped structural base + config-injected palette.
9. 3-way-merge base = **recovered by re-render** at the recorded version (no stored baseline).

### Non-goals

- Byte-for-byte reproduction of authored content or generated PNGs.
- A deploy pipeline beyond a validation-core CI template + a config-selected deploy tail.
- Abstracting over SSGs (Hugo+Hextra only) or image providers (Gemini only) — fields reserved, not implemented.

---

## 2. Current blog-craft (baseline to extend)

- Plugin `derio-net/blog-craft` v0.1.0; skills `bootstrap-blog`, `blog-post`, `media`, `media-screenshots`.
- Config `.blog-craft.yaml` v1: `project`, `metaphor{persona,visual_constants,base_style,reference_guidance,reference_image}`, `series[]`, `voice`, `image_gen`, `features{roadmap_shortcode,series_overview_posts}`.
- 3-pass template render (`tools/bootstrap-render.sh` + `tools/render-template/` Go renderer): `templates/hugo-hextra/` + `per-series-always/` + `per-series-overview/`.
- Helpers: `tools/blog-post-create.sh`, `tools/media-fill.py`, `scripts/generate-images.py` (single-prompt).
- Tests: `tests/smoke-{bootstrap,blog-post,media}.sh` + `fixtures/answers-frank-like.yaml`.
- Gap to frank-parity: layered image composition, papers content-type, roadmap/read-tracker/CSS params, validation/CI surface, and an **update** path (only one-time bootstrap exists today).

frank's `generate-all-images.py` is a strict superset of blog-craft's `generate-images.py`.

---

## 3. Architecture overview

Four config concerns → four implementation areas: **project**, **image** (Approach-A engine §4), **series + content_types** (§5), **features/ci** (§6). A single **path-ownership manifest** classifies every materialized path as `framework` (reproduce+overwrite), `content` (ignore+never-touch), or `merged` (reproduce-with-config + 3-way merge). It powers both the reproduction test (§7) and the updater (§8).

---

## 4. Config contract `.blog-craft.yaml` v2

`version: 2`; stoa's v1 migrated once (mechanical; guarded by stoa golden test).

```yaml
version: 2
blog_craft_version: "<release applied>"   # set by bootstrap/update; drives §8 deltas
project: { name, tagline, base_url, base_path, module_path }

image:
  provider: gemini
  model: gemini-3-pro-image-preview
  api_key_env: GEMINI_API_KEY
  output_dir: static/images
  prompts_file: prompt_for_images.yaml
  reference_pool: .reference-pool          # per-series masters + subjects/ anchors
  curation: { count_default: 1, archive_cap: 30, contact_sheet: true }
  composition_order: [base_character, base_atmosphere, reference_guidance, torso, mood, scene]
  layers:                                  # each layer: scalar | list | indexed-table
    base_character: |  ...                 # scalar → verbatim
    base_atmosphere: | ...
    reference_guidance: | ...
    visual_constants:  [ ... ]             # list → "- " bulleted lines (stoa)
    torso:                                 # indexed-table keyed by (entry.series, entry.torso_variant)
      building: [ "...", ... ]
      papers:   [ "...", ... ]
    mood:                                  # indexed-table keyed by entry.mood (name)
      focused: "..."
    # 'scene' reserved → per-image entry's `prompt`

series:
  - { key: building,  title: "...", description: "...", content_type: posts }
  - { key: papers,    title: "...", description: "...", content_type: papers }

content_types:
  papers:                                  # absent / enabled:false for stoa
    enabled: true
    dossier_dir: docs/papers-dossiers
    data_dir: blog/data/papers
    gate: { min_vendors: 3, min_sources: 5, min_source_types: 3,
            min_artefacts: 3, min_artefact_kinds: 2, min_gaps: 1, min_counterargs: 1 }
    source_types:   [vendor-docs, paper, postmortem, talk, benchmark]
    artefact_kinds: [grafana-screenshot, asciinema, yaml, commit, incident]
    shortcodes:     [landscape, capability-matrix, scar, pullquote, dossier-link, references-index]
    crosslink_fields: [related_building, related_operating]
    weight_offset: 1

features:
  series_overview_posts: true
  read_tracker: true
  banners:   { operator_generated: true }
  roadmap:   { enabled: true, data: data/roadmap.yaml }
  analytics: { provider: goatcounter, code_env: GOATCOUNTER_CODE }
  css:       { mermaid_palette: { node: "#1f3a5f", stroke: "#4dabf7", edge: "#51cf66", label: "#eaf2ff" } }

voice: | ...

ci:
  validators: [frontmatter, dossier, mermaid, hugo_build]   # pruned by content_types present
  deploy: { kind: container_pages }                          # container_pages | pages | none
```

### 4.1 Layer-resolution rule

For each name in `image.composition_order`, resolve from `image.layers`:
**scalar** → verbatim; **list** → `- ` bullets; **indexed-table** → select by the
per-image entry's field (`torso` ← `entry.torso_variant` within `entry.series`;
`mood` ← `entry.mood`); **`scene`** (reserved) → entry's `prompt`. Missing
selector skips the layer. The generator hardcodes no vocabulary/order; frank and
stoa ship different `composition_order` + `layers`. This is the only mechanism
reproducing both blogs' exact composed prompts.

---

## 5. Series, content types, papers module

`series.content_type` is `posts` (default) or `papers` (opt-in). `content_types.papers` (config-gated) materializes only when a series uses it:
- **Templates** (`templates/content-type-papers/`): paper bundle skeleton (TL;DR + §1–§7 budgets) + dossier template (`scaffold-paper` reads config).
- **Validators** (`tools/`): `validate-dossier.py` (thresholds from `gate`), `validate-papers.py` (frontmatter + `weight = paper_number + weight_offset`), `sync-dossier-to-data.py` (→ `data_dir`). No hardcoded thresholds.
- **Shortcodes/partials:** `landscape, capability-matrix, scar, pullquote, dossier-link, references-index` + cross-link partials (`papers-forwardlinks/backlink/prev-next`) + `single.html` injection.
- **Cross-linking:** bidirectional via `crosslink_fields`; paper frontmatter is the source of truth (Hugo build-time, zero retrofit).
- **Skill:** blog-craft `papers` skill (port of frank's), dormant unless enabled.
- stoa omits `content_types.papers` → none materializes.

---

## 6. Theme / layout / CSS parameterization

- **Banners** (`site-banner.html`): per-series path-detection partial ships; banner bytes are operator-generated content.
- **`custom.css`:** split into shipped structural base (`.post-cover`, `.screenshot`, `.asciinema-container`, `.site-track-banner`, `.blog-series-cards`, `.paper-post` family) + config-injected palette (`features.css.mermaid_palette`).
- **`read-tracker.js`:** ships, gated by `features.read_tracker`.
- **Roadmap:** scaffold shortcode ships; frank's specifics live in `data/roadmap.yaml` (a `content` path).
- **Analytics** (`goatcounter.html`): ships, gated by `features.analytics`, code from env.
- **Hookify weight-zero guard:** ships so every blog inherits the Hextra sidebar-trap protection.

---

## 7. Testing & reproduction harness (non-negotiable)

1. **Unit/contract:** layer-resolution rule, schema validator (replaces v1 parse-only), papers gate thresholds, each schema-migration transform.
2. **Per-feature smoke:** extend `smoke-{bootstrap,blog-post,media}`; **add** `smoke-papers` (scaffold → dossier → gate → validators → shortcode renders → Hugo builds) and `smoke-image-compose` (prompt-string equality).
3. **Integration reproduction** (rests on the §3 manifest):
   - **Frank golden:** apply blog-craft + frank config → scratch dir → diff `framework`/`merged` paths vs frank `blog/` → **zero structural drift**.
   - **Stoa golden:** same vs stoa-blog (regression guard).
   - **Image equality:** sampled entries → `generate --print-prompt` byte-identical to legacy generator (deterministic; no Gemini call) — proves Approach A.

---

## 8. Versioning & forward-migration (the updater)

Axes: `version:` (config schema) + `blog_craft_version:` (last-applied release).

- **Schema ladder:** ordered, pure, idempotent `migrations/00N-to-00M.py` (config-in → config-out), each with a golden fixture; `version:` selects which run; non-destructive (git + `.bak`).
- **Update flow** (`/blog-craft:update` / `bootstrap-render.sh --update`): render to a **staging tree**; classify via manifest (`framework`→replace, `content`→leave, `merged`→3-way merge); **base recovered by re-render** at recorded `blog_craft_version` (via blog-craft git tag), `diff3`, conflicts surfaced; emit **dry-run diff** for review; apply on approval; bump version.
- **Testability:** update smoke bootstraps at `vN`, evolves a fixture to `vN+1`, `update --dry-run` asserts golden diff, applies, asserts Hugo builds + reproduction passes. Ladder gets per-step fixtures.

---

## 9. CI

blog-craft ships a CI template materializing the **validation core** (frontmatter+dossier+mermaid+`hugo --minify`, pruned by content_types) + a smoke/reproduction job in blog-craft's own CI. **Deploy tail** via `ci.deploy.kind` (shipped template or operator-appended); stoa = `none`.

---

## 10. Phase sequencing (this repo unless noted)

| Phase | Repo | Deliverable | Gate | PR group |
|---|---|---|---|---|
| **P1 — Config v2 + manifest** | blog-craft | v2 schema, real schema validator, path-ownership manifest, stoa v1→v2 config migration | validator unit tests; stoa smoke green | 1 |
| **P2 — Image engine (Approach A)** | blog-craft | canonical generator as generic concatenator, composition_order/layers, reference-pool, curation | `smoke-image-compose` prompt-equality | 1 |
| **P3 — Papers content-type** | blog-craft | templates, validators, shortcodes, cross-linking, dossier flow, `papers` skill — opt-in | `smoke-papers`; stoa unaffected | 2 |
| **P4 — Theme/layout/CSS params** | blog-craft | banners, CSS split, read-tracker, roadmap-as-data, analytics, weight-zero guard | per-feature smoke + Hugo build | 2 |
| **P5 — Validation/CI + reproduction harness** | blog-craft | extended smoke suite, frank+stoa golden tests, CI template, blog-craft CI | **both golden tests green = parity proven** | 3 |
| **P6 — Updater** | blog-craft | schema ladder, 3-way-merge update flow, dry-run diff, update smoke | update smoke (vN→vN+1) green | 3 |
| **P7 — Migrate frank** | frank | author frank's `.blog-craft.yaml`, materialize, retire inline skills + diverged script | frank golden test green; stoa still green | (later run) |

P1–P6 never touch frank's blog. P7 = lowest-risk cutover, guarded by P5's harness.

---

## 11. Risks & open items

- **Generator port** (hardcoded order → config order) is the one non-mechanical change; de-risked by `smoke-image-compose`.
- **Manifest completeness:** unclassified path defaults to `content` (safe); add a "no unclassified materialized path" assertion so a missing `framework` path can't silently drop from the parity test.
- **Roadmap-as-data fidelity:** shortcode must render data to equivalent output (Hugo-build smoke, not pixel diff).
- **stoa config migration** must be byte-reviewed; stoa golden test is the backstop.

---

## 12. Acceptance criteria

1. blog-craft + frank config → scratch → **zero structural drift** vs frank `blog/`.
2. blog-craft + stoa config → scratch → **zero structural drift** vs stoa-blog.
3. `smoke-image-compose` prompt-string equality for frank + stoa.
4. `smoke-papers` green (papers on); stoa proves papers absent when off.
5. Update smoke proves non-destructive, reviewed v2→v3 path.
6. (P7, later) frank migrated: inline blog skills + `generate-all-images.py` retired; frank's blog produced/maintained by blog-craft + config; stoa still green.

---

## Implementation Plans

| Plan | Group / Phases | Status | Notes |
|------|----------------|--------|-------|
| 2026-06-30-blog-craft-foundation | `derio-net/blog-craft` | `2026-06-30-blog-craft-foundation` | — |
| 2026-06-30-blog-craft-modules | `derio-net/blog-craft` | `2026-06-30-blog-craft-modules` | — |
