---
name: explainers
description: Write a technical deep-dive post (explainer) in a blog-craft blog whose config enables the explainers content-type. Triggers on "write an explainer", "deep-dive post", "explain this feature as a post". Walks a reader through one feature of a codebase, presents a Claude Skill, compares similar skills, or explains a cross-cutting concern. Dormant unless content_types.explainers.enabled in .blog-craft.yaml.
user-invocable: true
disable-model-invocation: false
arguments:
  - series
  - number
  - slug
  - title
  - archetype
---

# Explainers (opt-in content-type)

An **Explainer** is a technical deep-dive post — walking a reader through one
feature of a codebase, presenting a Claude Skill, comparing two similar skills,
or explaining a cross-cutting concern (testing pyramid, deployment strategy,
security posture). This skill is only relevant in a blog-craft blog whose
`.blog-craft.yaml` sets `content_types.explainers.enabled: true` and has a
series with `content_type: explainers`.

All thresholds, paths, and the weight offset come from
`content_types.explainers` in `.blog-craft.yaml` — nothing here is hardcoded.

## Archetypes

The `archetype` frontmatter field records which recipe produced the post.
The default (and only fully-scaffolded) archetype is `feature-deep-dive`.
Five additional guidance-only archetypes are documented in
`skills/explainers/references/archetypes.md` — no scaffold, no validator,
follow the same lifecycle using that recipe for section structure.

## Lifecycle

1. **Find + validate the blog** — walk up from the working directory for
   `.blog-craft.yaml`; confirm `series` has an entry with
   `content_type: explainers`. Stop if not found or not enabled.

2. **Research** — dispatch the `explainer-researcher` subagent at the target
   path/topic. It returns a structured markdown brief (key files with
   `file:line` references, an architecture summary, tradeoffs surfaced from
   code, comments, or commit history). This keeps heavy exploration out of the
   drafting session's context.

3. **Scaffold** — create the page bundle:
   ```bash
   bash <blog-craft>/tools/scaffold-explainer.sh --config .blog-craft.yaml <NN> <slug>
   ```
   Writes `content/docs/<series>/<NN>-<slug>/index.md` with
   `weight = NN + weight_offset` and the six-section skeleton (Overview, Why
   it exists, How it works, Code walkthrough, Tradeoffs & alternatives, Try it
   yourself).

4. **Draft** — fill every section using the research brief. For
   `feature-deep-dive`, follow the scaffolded section headings and their
   budget comments. For guidance-only archetypes, use the recipe in
   `references/archetypes.md` for section structure instead of the scaffolded
   headings.

5. **Visuals** — Mermaid fences for diagrams/flows (Hextra renders these
   natively); Hextra `cards`/`tabs`/`callout` shortcodes for side-by-side
   comparisons or callout boxes where an archetype needs them.

6. **Media + cover** — run `/media` for any `<!-- MEDIA: -->` placeholders;
   generate a cover via `/blog-post`'s existing image flow.

7. **Validate + publish** —
   ```bash
   python <blog-craft>/tools/validate_explainers.py --config .blog-craft.yaml \
       content/docs/<series>/<NN>-<slug>/index.md
   ```
   Frontmatter + weight invariant only (no dossier fields). Set
   `draft: false` when ready.

## Guardrails

- `weight = post_number + weight_offset` (Hextra sorts `weight: 0` last).
- `series` must be a **list** (`[<series-key>]`) — Hextra's opengraph needs it.
- No dossier — don't invent one. The explainers content-type is deliberately
  lighter than papers.
