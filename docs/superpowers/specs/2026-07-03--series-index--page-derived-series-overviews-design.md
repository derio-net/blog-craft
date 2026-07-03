# Page-derived series overviews (`series-index` shortcode)

**Date:** 2026-07-03
**Status:** draft
**Repos:** derio-net/blog-craft (mechanism), derio-net/frank (adoption)

## Problem

A blog-craft series overview (`<series>/00-overview`) lists its posts two ways
today, both **push**-model:

1. `blog-post-create.sh` appends a line to a `## Series Index` list at an HTML
   marker, and a row to a `## Topic / Evolution Map` table at another marker.
2. frank #604 wired the same markers into its (combined) building overview.

The push model drifts: it only updates when `/blog-craft:blog-post` runs, a
hand-edit or an out-of-band post creation silently desyncs the index, and it
forced frank's operating series to stay a manual edit (its index lives inside
the *combined* `building/00-overview`, which the per-series helper can't reach).

Papers already solves the freshness problem with a **pull** model
(`papers-roadmap.html` regenerates the roster at Hugo build time). But papers
ranges a *data roster* (`data/papers.yaml`) enriched with page status, because
papers track planned/deferred entries that have no page yet.

**Building and operating have no such need — every post is a page.** So they can
be *purely* page-derived: no data file, no markers, no sync, no drift.

## Goals

- A generic `{{< series-index >}}` shortcode that renders a series' index from
  its actual pages at build time, sorted, always in sync.
- Retire the Series-Index / Topic-Evolution-Map marker-append from the template
  and `blog-post-create.sh`.
- frank adopts it: split the combined overview so **building** and **operating**
  each get their own auto-updating landing page.

## Non-goals

- **Papers is unchanged.** Its roster+status model is correct for planned/deferred
  entries; this feature does not touch `papers-roadmap.html`.
- frank's cluster-wide **Technology → Capability Map** stays a hand-curated table
  on the building overview — it is a tech inventory, not a per-series index, and
  does not map 1:1 to posts. Out of scope.
- No prev/next nav, no cover regeneration changes.

## Design

### Mechanism — `templates/hugo-hextra/layouts/shortcodes/series-index.html`

Generic (ships to every blog, not papers-specific). Placed on a
`<series>/00-overview` page with no arguments; it infers the series from the
host page.

Behaviour:

- **Series:** the host page's own `series` param (`$.Page.Params.series`). If the
  page declares more than one, use the first; a `{{< series-index "key" >}}`
  positional arg overrides.
- **Pages:** `where site.Pages "Params.series" "intersect" (slice $series)`,
  **excluding the host overview page itself** (compare `.RelPermalink`), sorted
  by `weight` ascending. Drafts follow Hugo's normal rule (excluded unless
  `--buildDrafts`), so no special handling.
- **Render:** a Markdown-styled table

  ```
  | # | Post | Takeaway |
  |---|------|----------|
  ```

  per page:
  - **`#`** — the numeric prefix of the page bundle name (`.File.ContentBaseName`,
    e.g. `01-introduction` → `01`); blank if the name has no `NN-` prefix.
  - **Post** — `.LinkTitle` (falls back to `.Title`), linked to `.RelPermalink`.
  - **Takeaway** — `.Params.summary` (the one-line card summary every post already
    carries in its frontmatter), `""` if absent.
- **Empty series:** render nothing (or a muted "No posts yet") rather than an
  empty table.

No data file. No markers. The table is recomputed every build from whatever pages
exist.

### Retire the push machinery (blog-craft)

- `templates/per-series-overview/00-overview/index.md.tmpl`: replace the
  `## Series Index` + entries-marker and the `## Topic / Evolution Map` + table +
  rows-marker with a single `## Series Index` + `{{< series-index >}}`.
- `tools/blog-post-create.sh`: **remove the overview-append step** (steps that read
  `features.series_overview_posts`, resolve the overview path, and run
  `insert-before-marker.py`). The cover/prompts/image-gen steps are unchanged.
  `insert-before-marker.py` may be retired if nothing else uses it (check first).
- Tests: the `blog-post` scaffold test no longer asserts an appended overview
  entry; a new `test_series_index` asserts the shortcode renders the correct rows
  (number/title/takeaway, weight order, self-excluded) from fixture pages at a
  real `hugo` build.

### Adoption (frank)

- **Split the combined overview.** `building/00-overview` keeps *About*, the
  curated *Technology → Capability Map*, and gains `{{< series-index >}}` in place
  of the hand-list; the `## Operating on Frank — Series Index` section moves to a
  new `operating/00-overview` (*About operating* + `{{< series-index >}}`).
- **Drop the #604 markers** (`<!-- /blog-post auto-appends … -->`) — redundant.
- **Re-touch `agents/rules/repo-workflows.md` step 5:** `/blog-craft:blog-post`
  scaffolds the post and the overview auto-lists it (no manual/append step);
  still add the roadmap layer to `data/roadmap.yaml`. Operating now has its own
  overview.
- **Verify:** both overviews `hugo --minify` clean; the rendered building index
  matches the current hand-list (same posts, order, links); operating index lists
  all operating posts. (`summary` present on frank's posts per `repo-blog.md`; a
  post lacking one shows a blank takeaway — acceptable, flag any in review.)

## Testing

- **blog-craft:** `test_series_index` (Hugo build over fixture pages: correct
  rows, weight-sorted, host page excluded, `#` from slug, takeaway from summary,
  empty-series case); updated `test_scaffold_paper` / overview-template tests
  (no markers, no append); full suite green.
- **frank:** `hugo --minify` on the split overviews; a render check that the new
  building series-index lists the same posts as the retired hand-list.

## Rollout

blog-craft mechanism merges first; frank adopts after (its overview split
consumes the shipped shortcode). No user-facing content change beyond the index
becoming self-maintaining and operating gaining a landing page.

## Implementation Plans

| Plan | Repo | Scope |
|------|------|-------|
| _TBD_ | derio-net/blog-craft | `series-index` shortcode + template/scaffold retirement + tests |
| _TBD_ | derio-net/frank | split building/operating overviews, drop #604 markers, re-touch workflow, verify |
