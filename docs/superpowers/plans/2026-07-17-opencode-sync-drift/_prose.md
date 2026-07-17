# OpenCode-mirror + uv.lock sync drift — implementation

Stop `install.sh` from dirtying the tree on every run, and make the two drifts
that caused it fail CI instead of rotting silently.

Spec: `docs/superpowers/specs/2026-07-17-opencode-sync-drift-design.md`.

## Two independent drifts, two phases

1. **`.opencode/` mirror drift** — committed `.opencode/skills/*/SKILL.md` lag
   canonical `skills/` (broadsheet #22, archetype-modes #35 never re-synced).
   Phase 1: a unit test shells `sync-opencode.py --check` (RED on the current
   drift), then regenerate + commit the mirrors (GREEN). No script logic change.

2. **`uv.lock` project-version drift** — the lockfile pins blog-craft at 0.4.0
   while pyproject is 0.7.0; bumps never touched it, so `uv run` reconciles it
   and dirties the tree. Phase 2: teach `bump_version.py` to keep `uv.lock`'s
   blog-craft `version` in lockstep (name-anchored regex — never the line-1
   schema `version = 1`) and to include it in `--check`; then bump 0.7.0 → 0.8.0
   so the lockfile lands reconciled, written by the new code (dogfooded).

Phase 3 verifies the matrix and the clean-tree sanity that motivated the fix.

## Why unit tests, not a new workflow

The repo already runs its unit suite in CI and already has a version
self-consistency tripwire (`test_committed_repo_is_self_consistent`). Extending
`versions()` to include `uv.lock` makes that tripwire guard the lockfile for
free; a small `test_opencode_sync.py` guards the mirrors. Both ride existing CI
and are catchable locally — matching the `test_mirrors.py` idiom.

## Invariants

- `sync-opencode.py` and `install.sh` are **not modified** — only invoked.
  Once mirrors + `uv.lock` are in lockstep, a fresh install produces a clean
  tree.
- `bump_version.py` stays minimal-diff; `uv.lock` support is **absent-safe**
  (a materialized blog / the `_mk_repo` fixture has no lockfile).
- Editing `tools/bump_version.py` trips the #18 bump-guard → the 0.8.0 bump is
  required, not incidental.
- **No deployment** → no post-merge Test Plan.

## Sequencing

Phases 1 and 2 are independent (`depends_on: []`); phase 3 fans in on both.
One worktree, one PR, executed locally via fr-execute.
