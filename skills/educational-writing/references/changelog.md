# Batch-rewrite changelog

When a whole series is rewritten to the educational methodology (a **batch /
campaign rewrite** — see `post-rewrite` "Batch / campaign mode"), produce a
durable **per-post changelog** as the campaign's diff record. It is *not* the
ephemeral per-post summary shown before each approval round — it is a committed
file (frank keeps `docs/blog/rewrite-<Series>-changelog.md`).

## Format

- A **"Conventions Applied to Every Post"** table lists the changes made to
  *every* post (frontmatter fields, Missteps table, Recovery Path, Mermaid
  diagrams…), deduplicated out of the per-post tables.
- **Per-post tables** (`### NN-slug`) list only that post's *specific* changes —
  no convention boilerplate (it's already above).
- Categories: **Added / Removed / Modified**. The category label appears once
  per group; subsequent items use a blank category cell.
- Each item is its own row (a `; `-joined item splits into rows).
- **No batch section headers** ("Batch 1 — Posts 00–03").

## Don't dedup by hand — assemble it

The "Conventions" table is exactly the items common to *every* per-post table —
a set-intersection that is error-prone across dozens of posts. Fill a YAML of
per-post entries as you rewrite, then let `tools/assemble_changelog.py` hoist
the common items and render the file:

```yaml
# rewrite-Building-entries.yaml
title: "Building Series Rewrite — Per-Post Changelog"
intro: "All 34 building posts rewritten with the educational methodology…"
posts:
  - slug: "01-introduction"
    added:    ["reader_goal, diataxis frontmatter", "Missteps table (real git history)",
               "Mermaid diagram (operator → Talos → Omni)"]
    removed:  ["ASCII art state machine (→ Mermaid)"]
    modified: ["Restructured day-by-day log → Architecture → Network → Boot"]
  - slug: "02-foundation"
    added:    ["reader_goal, diataxis frontmatter", "Missteps table (real git history)",
               "Mermaid diagram (3 Cilium LB examples)"]
    removed:  ["{{< relref >}} to 01-introduction"]
    modified: ["Restructured chronological bootstrap → OS → GitOps → Storage"]
```

Phrase a recurring change **identically** across posts so it hoists (e.g. always
`"Missteps table (real git history)"`). Then:

```bash
python <blog-craft>/tools/assemble_changelog.py rewrite-Building-entries.yaml \
    -o docs/blog/rewrite-Building-changelog.md
```

`"reader_goal, diataxis frontmatter"` and `"Missteps table (real git history)"`
appear in both posts above, so they land in the Conventions table and drop out
of the per-post tables; the Mermaid-diagram lines differ per post, so they stay.

## When to produce it

Any batch/campaign rewrite. For a single-post rewrite the changelog is
overkill — the `.bak` diff already tells the story.
