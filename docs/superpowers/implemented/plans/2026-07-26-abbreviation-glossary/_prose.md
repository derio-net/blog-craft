# Abbreviation glossary — implementation plan

Spec: `docs/superpowers/specs/2026-07-26-abbreviation-glossary-design.md`
Journal: `docs/superpowers/journals/specs/2026-07-26-abbreviation-glossary.md`

## What ships

An opt-in `features.glossary` capability: a blog-wide `data/glossary.yaml`
registry, an `{{< abbr >}}` shortcode rendering a native-Popover click panel
with **zero JavaScript**, a `{{< glossary-index >}}` shortcode, a `/glossary`
authoring skill that scans one post / one series / a whole blog, and a CI
validator mirrored into every blog's `scripts/`.

## Shape of the work

The build order follows a single constraint: **the exclusion logic must exist
before anything that depends on it.** Deciding "is this token in prose, or is it
inside a code fence / heading / link / frontmatter?" is the one genuinely fiddly
piece, and three separate consumers need the same answer — the scanner that
proposes terms, the applier that inserts markers, and the validator that finds
existing markers. Implementing it three times would guarantee they disagree, and
the failure mode of disagreement is a corrupted post.

So phase 2 builds `excluded_spans()` as a public library function and phases 3
and 4 import it. That is why phase 3 depends on phase 2 rather than running
beside it.

Phases 1 and 5 (config validation, Hugo surface) are independent of that chain —
they touch config and templates, not markdown. Phase 6 is the join: the skill
that orchestrates the tools, the OpenCode mirror, the CI step and the wizard
question all need everything under them to exist. Phase 7 is documentation,
versioning and the acceptance-matrix flips. Phase 8 is the manual work.

## A pre-existing flake gets fixed on the way past

Baseline on the branch point was **395 passed, 1 failed** —
`test_explainers_hugo.py::test_explainers_hugo_build`, red before any of this
work started.

The cause is time-of-day, not this branch. `scaffold-explainer.sh` stamps
`date:` from the **local** date; Hugo parses a bare `date: YYYY-MM-DD` as
midnight in the **site's** timezone. Between local midnight and UTC midnight
(two hours a day at CEST) a freshly scaffolded post is therefore future-dated,
and Hugo silently omits future content — the build still exits 0, which is
exactly why the test's returncode assertion passes and only the file-existence
glob fails. `--buildFuture` renders it: 22 pages become 23.

This is fixed in phase 5 task 1 rather than left alone, because every Hugo
render test this plan adds (GL-2, GL-7) scaffolds content the same way and would
inherit the identical flake. The fix makes the failure deterministic first
(stamping a post a day ahead), then green. Full details in the spec journal entry
`disc1-hugo-future-flake`.

## Deliberate non-changes

- **No config schema bump.** `features` passes through `.blog-craft.yaml.tmpl`
  via `toYaml`, so v5 stays v5 and no migration is written.
- **No `templates/manifest.yaml` change.** `assets/css/**` is already `merged`,
  which is the correct treatment for the new stylesheet: `add` on first update,
  3-way merge afterwards, so an operator's colour tweak survives. Narrowing the
  glob was considered during spec review and rejected — it would change
  `/update` behaviour for every existing blog's CSS to buy nothing this feature
  needs.
- **The validator mirror is unconditional.** `validate_glossary.py` ships to
  every blog's `scripts/` like `validate_mermaid.py` does; only the CI *step*
  that runs it is feature-gated. This keeps the `scripts/**` framework rule and
  the reproduction harness untouched.

## Verification

Every phase ends in a VERIFY step running the real suite. Phase 7 runs the
full gate — unit, `smoke-bootstrap.sh`, `smoke-update.sh`, the OpenCode drift
check, `fr acceptance check` and `validate-plans.sh` — and its output is what
the PR body quotes.

GL-3 (keyboard, Esc, touch dismissal) and GL-8 (the `/update` adoption path)
cannot be proven by any unit test. They are the entirety of phase 8, back-loaded
as `[manual]` so nothing agentic waits on them: the PR ships with that phase
unimplemented and the operator pushes the result to the same PR.
