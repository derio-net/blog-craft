---
name: blog-craft-papers
description: Write or continue a Paper in a blog-craft blog whose config enables the papers content-type. Enforces the dossier gate, scaffolds the bundle + dossier, and validates frontmatter + weight before publish. Use when creating or drafting a research/decision Paper. Dormant unless content_types.papers.enabled in .blog-craft.yaml.
---

# Papers (opt-in content-type)

A **Paper** is a research/decision document backed by a **dossier** that must
pass a gate before drafting. This skill is only relevant in a blog-craft blog
whose `.blog-craft.yaml` sets `content_types.papers.enabled: true` and has a
series with `content_type: papers`.

All thresholds, paths, and the weight offset come from
`content_types.papers` in `.blog-craft.yaml` — nothing here is hardcoded.

## Lifecycle

1. **Scaffold** — create the page bundle + dossier template:
   ```bash
   bash <blog-craft>/tools/scaffold-paper.sh --config .blog-craft.yaml <NN> <slug>
   ```
   Writes `content/docs/<papers-series>/<NN>-<slug>/index.md` (weight =
   `paper_number + weight_offset`) and `<dossier_dir>/<NN>-<slug>/dossier.md`
   (YAML-frontmatter dossier).

2. **Fill the dossier** — edit the dossier frontmatter until the gate passes:
   `vendors`, `primary_sources` (each with a `type`), `artefacts` (each with a
   `kind`), `gaps`, `counter_arguments`. Gate thresholds live in
   `content_types.papers.gate`.

3. **Gate check** (human review of gaps + counter-arguments first):
   ```bash
   python <blog-craft>/tools/validate_dossier.py --config .blog-craft.yaml \
       <dossier_dir>/<NN>-<slug>/dossier.md            # add --check-urls to verify sources
   ```
   Exit 0 = pass. Do not draft until the gate passes.

4. **Draft** — fill every `§` section of `index.md` (budgets are in the
   scaffold comments). Use the papers shortcodes: `{{< papers/landscape >}}`,
   `{{< papers/capability-matrix >}}`, `{{< papers/scar >}}`,
   `{{< papers/pullquote >}}`, `{{< papers/dossier-link >}}`. The
   `dossier-link`, forward/back cross-links, and prev/next nav are wired into
   `single.html` automatically for papers pages.

5. **Cross-link** — set `related_building` / `related_operating` (the
   `crosslink_fields`) in the paper frontmatter; the backlink chip renders on
   those posts automatically at Hugo build (no edits to those posts).

6. **Media** — run `/media` for any `<!-- MEDIA: -->` placeholders; generate a
   cover with `/blog-post`'s image flow (the paper's `series` selects the torso
   layer if the blog's image config defines one).

7. **Validate + publish** — frontmatter + weight invariant, then flip drafts:
   ```bash
   python <blog-craft>/tools/validate_papers.py --config .blog-craft.yaml \
       content/docs/<papers-series>/<NN>-<slug>/index.md
   python <blog-craft>/tools/sync_dossier_to_data.py --config .blog-craft.yaml
   ```
   Set `draft: false` and `status: published` when ready.

## Guardrails

- `weight = paper_number + weight_offset` (Hextra sorts `weight: 0` last).
- `series` must be a **list** (`[<papers-series>]`) — Hextra's opengraph needs it.
- The dossier gate is non-negotiable: no drafting before it passes.
