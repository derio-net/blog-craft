# Humanize the writing pipeline — plan narrative

Spec: `docs/superpowers/specs/2026-07-27-humanize-writing-design.md` (operator-approved,
A+B: methodology amendments + blind cold-reader editor; outline-first inversion rejected).

## Shape of the work

Two independent roots feed two integration phases, then close-out:

- **Phase 1** (root) vendors the AI-tells catalog with its fenced machine-readable
  YAML block — the single source both the drafting prose and the validator lint
  consume. Everything mechanical downstream hangs off `load_lint_data()`.
- **Phase 2** builds the warnings-first lint layer in `validate_educational.py`
  (vocabulary fails; em-dash / negative-parallelism / triad densities,
  cliché conclusions, and the mode-conditional what-transfers check warn),
  the `quality.lint` config schema, CLI wiring, and CONFIG.md docs.
- **Phase 3** (root) writes the reader-arc methodology reference and amends
  educational-writing (§2a carve-out, §4 "Session-skeleton" failure signature,
  checklist items). Prose, contract-tested by greps.
- **Phase 4** authors the blind `agents/cold-reader.md` and wires the dispatch
  sub-step + reference loading + `quality.lint.enabled` seeding into
  `/blog-post` and `/post-rewrite`.
- **Phase 5** flips matrix rows with evidence refs, adds the CHANGELOG entry,
  bumps the plugin version.
- **Phase 6 [manual]** is the back-loaded live acceptance run on a consumer
  blog; the PR ships with it unimplemented and the operator pushes results to
  the same PR.

## Execution notes

- Work in the fr isolation worktree (`feat/humanize-writing`); run commands via
  `fr isolation exec --branch feat/humanize-writing -- ...`.
- Tests: `bash tests/run-unit.sh` (creates/reuses a venv; on the host Mac set
  `BLOG_CRAFT_TEST_VENV` to a non-/tmp path if output is empty — inside the
  devcontainer the default is fine).
- The lint deliberately EXCLUDES from its fail vocabulary words with legitimate
  technical uses (underscore, landscape, deep dive, robust, crucial, leverage).
  Do not "improve" the list by adding common tech words — false positives on
  real posts are worse than missed tells. The list lives only in ai-tells.md.
- All matching happens on prose only: fenced code blocks, inline code spans,
  and frontmatter are stripped first. A command that contains "delve" must
  never trip the lint (there is a test pinning this).
- The what-transfers / landscape mode conditions key off the `diataxis`
  frontmatter (tutorial/explanation), never series names — series names are
  per-blog.
- If changing/adding skills breaks `test_opencode_namespace.py`, run the repo's
  opencode sync tooling and commit the regenerated mirror — do not hand-edit
  `.opencode/`.

## Risks / guardrails

- **Metric gaming:** severities are warnings-first precisely so the drafting
  model isn't pushed to synonym-swap around a hard gate. Only the conservative
  vocabulary list fails.
- **Cold-reader blindness** is a prompt-level contract (the dispatch passes
  only the draft + methodology paths). The contract test pins the instruction
  text; the manual phase verifies the behavior live.

## Out of scope (from the spec)

Back-catalog retrofit campaign; per-blog voice fingerprinting; outline-first
inversion.
