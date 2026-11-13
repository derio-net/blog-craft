# Writing standards — implementation plan

Spec: `docs/superpowers/specs/2026-11-13-ste-writing-standard-design.md`.

Four agentic phases, one per ask of the spec:

1. **Checker core and `ste`** (skeleton). The registry of standards, prose extraction and
   sentence splitting, the `ste` kinds, and the CLI (resolution, severities, waivers, terms,
   output). R1–R11, R13.
2. **Two more standards.** The five remaining kinds, `elements-of-style.md`,
   `plain-language.md` and the standards README. R2, R22–R25.
3. **The rewrite.** `--preserve-from`, the `apply-writing-standard` skill and the
   `fact-keeper` agent, held by contract tests. R12, R14–R18.
4. **Blog integration.** Config keys, `docs/CONFIG.md` §15, the blog-post and post-rewrite
   wiring, materialized copies, batch-gate and the CI template, then the version bump and
   changelog. R19–R21.

## Test evidence

This container has no `hugo`, so 38 existing tests fail locally for reasons unrelated to
this feature. Every phase therefore runs its own tests locally
(`bash tests/run-unit.sh tests/unit/ -k writing_standard -q`) and uses CI's `test` job on
the pushed head as its recorded evidence (`tests: ci`, `.fr/ci.yaml`'s `gate_checks`).
The draft PR opens when implementation starts, because CI runs on pull requests.

## Conventions

- TDD per task: red, green, refactor.
- `tools/` is flat and on `sys.path` in tests (`tests/conftest.py`); the checker may import
  `_prose_lines` from `validate_educational`.
- The checker depends on stdlib and PyYAML only (R4).
- Each standard's own "after" examples must pass its own checker (P2.T2.S3), and the skill's
  text should meet `plain-language` (P3.T2.S3).
