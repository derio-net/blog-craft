# `explainers` content-type: technical deep-dive posts

**Status:** Draft
**Date:** 2026-07-14

## Problem

blog-craft ships three skills (`bootstrap-blog`, `blog-post`, `media`) plus
one opt-in content-type, `papers`, for research/decision documents backed by
a sourcing dossier. There is no first-class support for a different, more
common kind of post: a **technical explainer** — walking a reader through one
feature of a codebase, presenting a Claude Skill, comparing two similar
skills, or explaining a cross-cutting concern (testing pyramid, deployment
strategy, security posture) in a specific repo. Today an operator would have
to shoehorn this into a plain `/blog-post`, with no structural guidance, no
research support, and no validation tuned to "does this explanation actually
ground itself in the code."

## Goals

- A new opt-in content-type, `explainers`, mirroring the `papers` extension
  pattern (own skill, own `content_types.explainers` config block, own
  scaffold + validate scripts, own series `content_type` value) so it stays
  dormant in any blog that doesn't enable it.
- One fully-worked archetype for v1: **codebase feature deep-dive** — a
  scaffolded section outline, a validator, tests.
- The other five archetypes named in the original ask (presenting a Claude
  Skill, comparing two skills, testing pyramid, deployment strategy,
  security posture) get a short recipe each in a references doc the skill
  points to — guidance, not structural scaffolding, in this pass.
- A dedicated research subagent (`explainer-researcher`) that reads the
  target codebase/skill and returns a structured brief (key files with
  line references, architecture summary, notable tradeoffs it can find in
  code/comments/history), so the drafting step in the main session works
  from grounded material instead of re-deriving it inline.
- Visuals via Mermaid code fences (Hextra renders these natively; blog-craft
  already validates Mermaid and ships a `mermaid_palette` config) plus
  Hextra's built-in `cards` / `tabs` / `callout` / `steps` shortcodes.
- Standard frontmatter + weight validation only, matching ordinary posts —
  no dossier-style sourcing gate.

## Non-goals

- No dossier/citation gate (that rigor stays specific to `papers`).
- No new Hugo shortcodes — Mermaid + Hextra's existing shortcode set covers
  diagrams, comparisons, and callouts for the v1 archetype.
- No structural scaffolding for the five guidance-only archetypes — they are
  documented recipes the skill/operator follow by hand, not templated
  section skeletons with their own validators.
- No external web research — the researcher subagent reads local
  files/git history only (`Glob`, `Grep`, `Read`); no `WebSearch`/`WebFetch`.
- No changes to `papers`, `blog-post`, or `media`'s existing behavior beyond
  the new config-gated materialization hook in `bootstrap-render.sh`.

## Design

### Config (`content_types.explainers` in `.blog-craft.yaml`)

```yaml
content_types:
  explainers:
    enabled: true
    weight_offset: 1   # weight = post_number + weight_offset, mirrors papers
```

A series opts in via `content_type: explainers` on its `series[]` entry,
exactly like `content_type: papers` does today.

### New skill: `skills/explainers/SKILL.md`

Dormant unless `content_types.explainers.enabled`. Arguments: `series`,
`number`, `slug`, `title`, `archetype` (default/only-fully-supported value
`feature-deep-dive`; the other five archetype names are accepted and route
to the references doc instead of a specialized scaffold).

Lifecycle (mirrors `papers`' shape, minus the dossier gate):

1. **Find + validate the blog** — walk up for `.blog-craft.yaml`; validate
   `series` is configured with `content_type: explainers` (same pattern as
   `blog-post` Steps 1–3).
2. **Research** — dispatch the `explainer-researcher` subagent at the target
   path/topic; it returns a structured markdown brief (key files with
   `file:line` references, an architecture summary, tradeoffs it can find).
   This keeps heavy exploration out of the drafting session's context.
3. **Scaffold** —
   ```bash
   bash <blog-craft>/tools/scaffold-explainer.sh --config .blog-craft.yaml <NN> <slug>
   ```
   writes the page bundle at `content/docs/<series>/<NN>-<slug>/index.md`
   with `weight = NN + weight_offset` and the feature-deep-dive section
   skeleton (below).
4. **Draft** — fill every section using the research brief. Feature-deep-dive
   skeleton: Overview, Why it exists, How it works (≥1 Mermaid diagram),
   Code walkthrough (`file:line` references), Tradeoffs & alternatives, Try
   it yourself.
5. **Visuals** — Mermaid fences for diagrams/flows; Hextra `cards`/`tabs` for
   side-by-side structure where an archetype needs it (e.g. a comparison);
   no new shortcode.
6. **Media + cover** — run `/media` for any `<!-- MEDIA: -->` placeholders;
   generate a cover via `/blog-post`'s existing image flow.
7. **Validate + publish** —
   ```bash
   python <blog-craft>/tools/validate_explainers.py --config .blog-craft.yaml \
       content/docs/<series>/<NN>-<slug>/index.md
   ```
   frontmatter + weight invariant only (no dossier fields). Flip
   `draft: false` when ready.

Reference doc `skills/explainers/references/archetypes.md` gives a short
recipe (what to cover, no scaffolding) for each of: presenting a Claude
Skill, comparing two similar skills, testing pyramid, deployment strategy,
security posture.

### New subagent: `agents/explainer-researcher.md`

Read-only (`Glob`, `Grep`, `Read`) subagent. Input: a target path or topic
(e.g. a skill directory, a package, a feature name). Output: a structured
brief, not prose — file list with line references, an architecture summary,
and any tradeoffs/decisions it can surface from code, comments, or commit
messages. Scoped to the local repo only, consistent with the internal-only
decision already made for this feature (no web research).

### Scripts (mirror pairs, like `papers`)

- `tools/scaffold-explainer.sh` ↔
  `templates/content-type-explainers/shared/scripts/scaffold-explainer.sh`
- `tools/validate_explainers.py` ↔
  `templates/content-type-explainers/shared/scripts/validate_explainers.py`

Both pairs added to `tests/unit/test_mirrors.py`'s `MIRRORS` list so they're
enforced byte-identical, same as the `papers` scripts today.

### `bootstrap-render.sh` wiring

Add an `explainers` gating block alongside the existing `papers` block
(`tools/bootstrap-render.sh` ~L50–57): read
`content_types.explainers.enabled` via the Go render-template's
`--get-bool`, and materialize `templates/content-type-explainers/shared`
into the target blog only when true — otherwise nothing under
`content-type-explainers` leaks into a blog that never opted in.

### Docs

- `README.md` — add `explainers` to the skill list (four skills total).
- `docs/CONFIG.md` — document `content_types.explainers`.
- `docs/ARCHITECTURE.md` — no structural change; `explainers` is a second
  instance of the content-type extension pattern already described there.

## Testing

TDD, mirroring the existing `papers` test suite:

- `test_explainers_gating.py` — `content_types.explainers.enabled` gates
  materialization of `templates/content-type-explainers/shared` (mirrors
  `test_papers_gating.py`).
- `test_scaffold_explainer.py` — scaffold produces the expected bundle path,
  weight invariant, and section skeleton (mirrors `test_scaffold_paper.py`).
- `test_explainers_validators.py` — frontmatter + weight validation, no
  dossier fields (mirrors `test_papers_validators.py`).
- `test_mirrors.py` — extend `MIRRORS` with the two new script pairs.

No acceptance matrix exists in blog-craft (unlike super-fr) — not applicable
here.

## Rollout

Pure plugin code (new skill, subagent, scaffold/validate scripts, config
schema, docs) — no deploy surface, no post-merge Test Plan.
