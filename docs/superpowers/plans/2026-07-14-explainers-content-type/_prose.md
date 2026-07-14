# Explainers content-type — implementation plan

Spec: `docs/superpowers/specs/2026-07-14--explainers--content-type-design.md`

## Why this shape

blog-craft already extends itself once, via `papers`: an opt-in
content-type gated on `content_types.papers.enabled`, with its own scaffold
script, its own validator, and shared assets that materialize into a
bootstrapped blog's `scripts/` and `layouts/` only when that flag is on. This
plan builds a second instance of that same extension point — `explainers` —
for technical deep-dive posts, deliberately lighter than `papers` (no
dossier gate, no new shortcodes) per the operator's brainstorm decisions.

Three phases, strictly sequential (each depends on the last):

1. **Core mechanics** — config gating, the scaffold script, the validator,
   and a Hugo smoke check. This is the only phase with real runtime
   behavior, so it's where all the TDD happens (four tasks, each red→green).
2. **Skill surface** — the `explainers` skill that drives the lifecycle, a
   references doc for the five guidance-only archetypes, and the
   `explainer-researcher` subagent that does the content-gathering legwork.
   No automated tests here (matches `papers`' own SKILL.md, which has none)
   — these are reviewed by re-reading against the spec.
3. **Docs + verification** — README/CONFIG.md updates, then a full-suite run
   and a plan self-review before handoff.

## Deliberately out of scope (see spec's Non-goals)

No dossier/citation gate, no new Hugo shortcodes (Mermaid + Hextra's
built-ins cover it), no web research in the subagent, no structural
scaffolding for the five guidance-only archetypes — they get a recipe in
`skills/explainers/references/archetypes.md`, not their own scaffold/validate
pair. If any of those turn out to be needed later, that's a rework plan
against real usage, not a v1 guess.

## Mirror-pair discipline

Two files are canonical in `tools/` and mirrored byte-identical into
`templates/content-type-explainers/shared/scripts/` (same pattern as the
four `papers` scripts): `scaffold-explainer.sh` and `validate_explainers.py`.
Both pairs get added to `tests/unit/test_mirrors.py`'s `MIRRORS` list in the
same task that creates them — never as an afterthought.

## Naming note

Frontmatter uses `post_number` (not `paper_number`) and drops `layer` /
`publish_order` / `status` — those three are specific to papers' richer
editorial/image-layer workflow and have no equivalent need here. Keep
`archetype` as the one explainers-specific field, recording which recipe
(feature-deep-dive today; the five guidance-only names later) produced the
post.
