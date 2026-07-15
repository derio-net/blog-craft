# Educational-writing methodology, quality gate, and defaults — implementation plan

Spec: `docs/superpowers/specs/2026-07-15--quality--educational-writing-and-defaults-design.md`

## Retrospective note

This plan is written **after the fact**. The change was implemented directly
on branch `claude/blog-post-quality-improvement-kl1lcu` (commits from the
`feat: educational-writing methodology…` commit onward), because the cloud
environment it was authored in has no fr-isolation/Docker and so couldn't run
the normal fr-brainstorming → plan → isolated-run loop. The phases below map
to that work so it can be reviewed against the repo's convention, verified on
an fr-capable host, and extended. Steps are therefore phrased as
**deliverable + how to verify**; on a host you can run the plan to confirm
each (the code already exists) and tick state, or re-derive any phase cleanly
under isolation.

## Why this shape

The heart is a shared **methodology** (`skills/educational-writing/`) that the
authoring skills load, plus a **structural gate** that mechanically enforces
the evidence floor — mirroring how `papers` pairs a skill with a validator,
but applied to all `content_type: posts` posts rather than an opt-in type.
Everything else hangs off those two: a `/post-rewrite` skill + `post-researcher`
subagent that apply the methodology to existing posts, a `voice_level` dial
and register/orientation rules that fix *how* posts read, and default
Mermaid/last-updated improvements that fix *how* they look.

Four phases, roughly sequential (2–4 depend on 1's methodology + gate):

1. **Methodology + gate core** — the `educational-writing` skill + references,
   `validate_educational.py` (+ blog-side mirror), the optional `quality`
   config, the CI gate step, `blog-post-create.sh`'s two new frontmatter
   args, and their tests. This is the phase with real runtime behavior.
2. **Authoring surface** — `/post-rewrite`, the `post-researcher` agent, the
   `/blog-post` wiring, bootstrap's `voice_level` step, and the voice/register/
   orientation/missteps/no-reminiscing guidance. Reviewed against the spec
   (skills have no automated tests, matching `papers`/`explainers`).
3. **Defaults** — the global Mermaid theme in `custom.css.tmpl`, the
   standalone explainer render fix + Mermaid theming, the `{{< last-updated >}}`
   shortcode, and prefer-Mermaid guidance. Has real runtime behavior → tested.
4. **Docs + verification** — README/CONFIG/ARCHITECTURE, full-suite run, plan
   self-review.

## Mirror-pair discipline

`tools/validate_educational.py` is canonical and mirrored byte-identical into
`templates/hugo-hextra/scripts/validate_educational.py`. `test_educational_
materialization.py` asserts byte-equality — extend/keep it in the same task
that touches the validator, never as an afterthought.

## Deliberately out of scope (see spec's Non-goals)

No config-schema bump/migration (`quality`/`voice_level` are optional keys);
no gate content-sniffing; no change to the `papers` dossier gate or to
`media`; no external-skill vendoring; no broader theme work beyond Mermaid +
the last-updated stamp. Anything found during host verification that needs
more is a rework plan against real usage, not a v1 guess.
