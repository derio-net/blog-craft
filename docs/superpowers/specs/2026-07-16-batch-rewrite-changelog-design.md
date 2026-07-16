# Changelog pattern for batch educational rewrites

- **Issue:** derio-net/blog-craft#28
- **Branch:** `feat/batch-rewrite-changelog`
- **Date:** 2026-07-16
- **Type:** feature (methodology reference + assembler tool + tests)
- **Reference:** derio-net/frank `docs/blog/rewrite-{Building,Operating}-changelog.md`.

## Goal

When a series undergoes a batch educational rewrite (#26), produce a durable
per-post **changelog**: a deduplicated "Conventions Applied to Every Post" table
plus per-post tables of only the post-specific changes. Distinct from #26's
*ephemeral per-post summary* (spot-check before approval) — this is the
committed diff record of the whole campaign.

## Operator decisions (batched Q&A, 2026-07-16)

1. **Doc + assemble helper.** A `references/changelog.md` documents the format;
   `tools/assemble_changelog.py` mechanizes the error-prone part — hoisting the
   items common to *every* per-post table into the "Conventions" table.
2. **Committed file in the blog repo** — written to the blog (frank's
   `docs/blog/rewrite-<Series>-changelog.md` pattern), a reviewable record.

## Design

### `tools/assemble_changelog.py` (plugin-side; no mirror)

Invoked during a campaign; not part of blog CI, so it lives in `tools/` only
(like `update.py`). Library + CLI:

- Input: a YAML of per-post change entries the agent fills as it rewrites:
  ```yaml
  title: "Building Series Rewrite — Per-Post Changelog"
  intro: "All 34 building posts rewritten with the educational methodology…"
  posts:
    - slug: "01-introduction"
      added:    ["Mermaid diagram (operator → Talos → …)", "Missteps table (real git history)"]
      removed:  ["ASCII art state machine (→ Mermaid)"]
      modified: ["Restructured from day-by-day log to Architecture → …"]
  ```
- `split_items(items)` — an item containing `; ` splits into separate rows
  (the issue's "each item becomes its own row").
- `hoist_conventions(posts)` — for each category (Added/Removed/Modified),
  Conventions = the exact-string items present in **every** post; each post's
  table keeps only its residual (post-specific) items. Recurring items
  (frontmatter, Missteps table, Recovery Path) are phrased identically by the
  agent so they hoist.
- `render_changelog(title, intro, conventions, per_post)` — emits the markdown:
  `# title` · intro · `## Conventions Applied to Every Post` table (category in
  the first row of its group, blank cell after) · `### <slug>` per-post tables.
  **No batch section headers** ("Batch 1 — Posts 00–03").
- CLI: `assemble_changelog.py <entries.yaml> [-o <out.md>]` (default stdout).

### `skills/educational-writing/references/changelog.md`

Documents the format, when to produce it (any batch/campaign rewrite), the YAML
input shape, and the `assemble_changelog.py` invocation. Linked from the
methodology.

### `skills/post-rewrite/SKILL.md` — batch-mode pointer

A step in the "Batch / campaign mode" section: after the final batch, collect
the per-post entries and run `assemble_changelog.py` to write
`docs/blog/rewrite-<Series>-changelog.md` in the blog repo. References
`educational-writing/references/changelog.md`.

## Version bump

Touches `skills/` + adds a `tools/` script → the #18 bump-guard requires a
bump. New capability → **minor** (`tools/bump_version.py minor`), with a
CHANGELOG `Unreleased`→ entry.

## Test Plan

Tooling + docs, **no deployment** → no post-merge Test Plan. Verification is the
unit suite (`tests/unit/test_assemble_changelog.py`, new):

- `split_items`: `["a; b", "c"]` → `["a", "b", "c"]`.
- `hoist_conventions`: an item in every post's Added → Conventions; removed from
  each per-post table; a post-specific item stays put.
- `render_changelog`: Conventions table has the category in the first row and a
  blank cell after; each post gets a `### <slug>` section; **no** "Batch" header
  anywhere in the output.
- a post whose items are all common → its `### <slug>` section notes "no
  post-specific changes" rather than an empty table.
- CLI round-trip on a 2-post fixture → exit 0, output contains the Conventions
  table + both slugs.

## Acceptance rows (matrix backfill — same PR)

- **CHG-1** — "assemble_changelog hoists items common to every post into the
  Conventions table and leaves per-post residuals" —
  `unit=blog-craft:tests/unit/test_assemble_changelog.py`, ci.
- **CHG-2** — "the assembled changelog carries no batch section headers" —
  `unit=blog-craft:tests/unit/test_assemble_changelog.py`, ci.

## Out of scope

- Auto-deriving the change entries from a git diff (the *what changed* is an
  editorial judgment the agent makes; the tool only assembles/dedups).
- Enforcing the changelog exists (it's an operator deliverable, not a CI gate).
