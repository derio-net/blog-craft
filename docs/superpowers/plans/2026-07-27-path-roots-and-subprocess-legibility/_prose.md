# Materialized-path roots + legible renderer failures

Fixes derio-net/blog-craft#59 and #61. Spec:
`docs/superpowers/specs/2026-07-27-path-roots-and-subprocess-legibility-design.md`.

Both issues are the same failure: **a path resolved against the wrong root, with
nothing saying so.** The operator asked for the general fix in each case, so the
plan fixes the cause where it lives and audits for the rest of the family
instead of patching the two reported instances.

## What "general" means here, concretely

- **#59 is fixed in `bootstrap-render.sh`**, because that is where the `cd`
  is — which fixes every caller at once, including a human running the renderer
  by hand to diagnose it (exactly what the issue says diagnosing costs today).
  Resolution at the Python API boundary is belt-and-braces on top. The audit
  found **four** broken sites, not one: `reproduce.py`'s own `--config` and
  `--scratch` carry the identical break and are not mentioned in the issue.
- **#59's second half becomes `tools/proc.py`**, and all four
  `check=True, capture_output=True` sites that discard their streams move to
  it — including `git archive <blog_craft_version>`, whose failure is the one
  `/update`'s own guardrail ("keep `blog_craft_version` accurate") warns about.
- **#61 gets a declared root model, not a longer allowlist.** The manifest
  already answers "who owns this path?" (framework/merged/content) with a
  completeness guard. It gains a parallel section answering "**who defines this
  path's location** — Hugo, or a tool that reads it from the repository root?",
  with the same shape and the same guard. `map_dest` consults it.
- **The audit found the flagged path is worse than flagged.** #61 asked for
  `.hookify.warn-hextra-weight-zero.md` to be *verified*, not assumed. Verified
  against hookify's loader: it globs `.claude/hookify.*.local.md` from the
  project root, so the shipped file matches neither the directory nor the
  filename and has **never loaded for any blog** — `site_dir` or not. And its
  own `file_path` pattern is site-relative, so the file itself has to become a
  template.
- **Relocation, so it self-heals.** #61's sharpest point is that the fix alone
  does not settle: the next `/update` re-adds the dead file. One
  manifest-declared `legacy_dests:` table covers both axes — a root change *and*
  a rename — and the planner moves the operator's file rather than adding a
  blank one beside it.

## Phase ordering

Phases 1, 2 and 5 are independent and touch disjoint files. Phase 3 needs the
root model (2). Phase 4 needs both a correct destination (2) and the hookify
rename (3), because it migrates both. Phase 6 lands docs, acceptance rows, the
version bump and full verification once the behaviour is settled.

Every phase is agentic and TDD-shaped: a `[RED]` step that writes the failing
test and names the expected failure, then a `[GREEN]` step that implements.

## The one thing to watch

`map_dest` is on the hot path of every `/update` for every existing blog. The
regression guard is that `site_dir: .` blogs must see **byte-identical**
behaviour except for the deliberate hookify relocation — `test_update_flow.py`,
`test_update_mapping.py` and `smoke-update.sh` all encode that, and phase 5
asserts the rendered CI file is unchanged for a blog with no `site_dir`.
Runtime is fail-safe by construction: an undeclared path defaults to `site`,
which is exactly today's behaviour. The enforcement is a test, not a crash.
