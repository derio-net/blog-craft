# OpenCode-mirror + uv.lock sync drift — design

- **Date:** 2026-07-17
- **Branch:** `fix/opencode-sync-drift`
- **Issue:** none (operator-reported: `scripts/install.sh` leaves the working tree dirty every run)
- **Status:** design → plan

## Problem

Running `scripts/install.sh` (or `sync-opencode.py`, or any `uv run`) on a
fresh `main` dirties three tracked files every time:

```
 M .opencode/skills/explainers/SKILL.md
 M .opencode/skills/post-rewrite/SKILL.md
 M uv.lock
```

Two independent drifts, both silent (no CI gate):

1. **`.opencode/` mirror drift.** `.opencode/skills/<name>/SKILL.md` are
   generated from canonical `skills/<name>/SKILL.md` by
   `scripts/sync-opencode.py` (install runs it at `install.sh:176` via
   `uv run`). The committed mirrors on `main` are **stale** — the broadsheet
   section (#22) and the archetype-modes edits (#35) never got re-synced into
   them. `sync-opencode.py --check` confirms:
   `explainers`/`post-rewrite`: content differs from canonical.

2. **`uv.lock` project-version drift.** `uv.lock` pins the blog-craft package's
   own `version = "0.4.0"`, but `pyproject.toml` is at `0.7.0`. Every version
   bump (#18→0.5.0, #28→0.6.0, #35→0.7.0) updated pyproject + both plugin
   manifests via `tools/bump_version.py` but **never touched `uv.lock`**, so
   its project-version line has lagged since 0.4.0. `uv run` reconciles it to
   `0.7.0`, dirtying the file. Note: `uv lock --check` **passes** — it
   validates dependency *resolution*, not the local project-version line — so
   it cannot catch this.

Nothing fails CI on either drift, so the mirrors rot and every operator install
produces a confusing dirty tree.

## Goal

1. **Resync** the committed `.opencode/` mirrors to canonical.
2. **Reconcile** `uv.lock` to the current version, and make bumps keep it in
   lockstep so it never re-drifts.
3. **Enforce** both with unit tests (riding existing CI) so future drift fails
   loudly instead of rotting.

Pure code + tooling + CI-adjacent tests. **No deployment → no post-merge Test
Plan.**

## Decisions (operator Q&A, 2026-07-17)

| Decision | Choice |
|---|---|
| uv.lock fix | **Lockstep in `bump_version.py`** — rewrite `uv.lock`'s blog-craft `version` + include it in `--check`; commit `uv.lock` at the current version now |
| Enforcement | **Unit tests** (ride the existing CI unit run; match the `test_mirrors.py` idiom) — no new workflow |

## Design

### 1. Resync `.opencode/` mirrors
Run `python scripts/sync-opencode.py` (no `--check`) and commit the result —
regenerates `.opencode/skills/{explainers,post-rewrite}/SKILL.md` from
canonical. Deterministic; no logic change to the sync script.

### 2. `uv.lock` lockstep in `tools/bump_version.py`
`uv.lock` is TOML; the project's own entry is the `[[package]]` block:
```
[[package]]
name = "blog-craft"
version = "0.7.0"
```
(`version = 1` on line 1 is the **lockfile schema** version — must NOT be
touched.)

- Add `_uvlock(root)` and target the blog-craft block with a **name-anchored**
  regex `(?m)^(name = "blog-craft"\nversion = ")[^"]*(")` — matches only the
  blog-craft package's version, never line 1's schema version and never other
  packages' versions.
- `versions(root)`: if `uv.lock` exists **and** contains the blog-craft block,
  add `out["uv.lock"] = <that version>`. Absent lockfile → skip (so
  `bump_version.py` still works in a materialized blog / the `_mk_repo` test
  fixture that has no `uv.lock`).
- `write_all(root, new)`: if `uv.lock` exists, rewrite the blog-craft version
  (minimal-diff, `count=1`).
- `check()` / `bump()` output strings: mention `uv.lock` when present.

The existing `test_committed_repo_is_self_consistent()` tripwire
(`bv.check(ROOT) == 0`) then **automatically** guards `uv.lock` too.

Commit `uv.lock` at the current version now; since this PR also bumps
0.7.0 → 0.8.0 (below), the committed `uv.lock` lands at **0.8.0**, written by
the new lockstep code itself (dogfooded).

### 3. Enforcement — unit tests
- **`tests/unit/test_opencode_sync.py`** (new): assert
  `scripts/sync-opencode.py --check` reports no drift. Use `subprocess`
  (the filename is hyphenated → not importable) with `sys.executable`; assert
  returncode 0. A committed-mirror drift then fails the unit suite (hence CI).
- **`tests/unit/test_version.py`** (extend): add a case that `versions()`
  includes `uv.lock` and that `bv.check` fails when the lockfile's blog-craft
  version is manually drifted; and that `bv.bump` updates `uv.lock`. Fixture
  gains an optional `uv.lock`. The existing self-consistency tripwire needs no
  change — it starts covering `uv.lock` for free.

### 4. Version bump (#18 guard)
Editing `tools/bump_version.py` trips `check_version_bump_needed.requires_bump`
(`tools/`). New synced surface + enforcement → **minor, 0.7.0 → 0.8.0**
(`bump_version.py minor`) + CHANGELOG. `auto-tag.yml` cuts `v0.8.0` on merge.

## Out of scope / non-changes

- **`install.sh` unchanged.** Once the committed mirrors + `uv.lock` are in
  lockstep, a fresh install regenerates byte-identical files → clean tree. The
  install-time `uv run … sync-opencode.py` behavior is correct as-is.
- **`sync-opencode.py` logic unchanged** — only invoked, not modified.
- **OC-1/OC-2 acceptance rows stay `not-implemented`.** They assert OpenCode
  *discovers* skills/commands (manual: run `opencode`). This fix is a
  prerequisite (mirrors now correct) but does not itself verify discovery, so
  it does not flip them. It is noted as advancing them.
- **Not gitignoring `uv.lock`** — the operator chose to keep it tracked for
  dependency-resolution reproducibility.

## Test Plan

Pure code + tooling, **no deployment → no post-merge Test Plan.** Verification
is the unit suite:

- `test_opencode_sync.py`: `sync-opencode.py --check` → exit 0 (mirrors match
  canonical). Fails if a committed mirror drifts.
- `test_version.py` (extended): `versions()` includes `uv.lock`; `check` fails
  on a drifted lockfile version; `bump` updates `uv.lock`; `bump_version.py`
  still works when `uv.lock` is absent; committed-repo tripwire green at 0.8.0.
- Full suite green in the dev container; `bump_version.py --check` agrees across
  pyproject + both manifests + `uv.lock` at 0.8.0.
- Manual sanity (not a post-merge Test Plan): after the branch is built,
  `uv run scripts/sync-opencode.py` + `uv run true` leave `git status` clean.

## Implementation Plans

| Plan | Repo | File | Depends on |
|------|------|------|------------|
| 2026-07-17-opencode-sync-drift | `derio-net/blog-craft` | `2026-07-17-opencode-sync-drift` | — |

## Acceptance rows (backfilled, same PR)

- `opencode-mirror-sync-enforced` (ci) — the committed `.opencode/` skill
  mirrors always match canonical `skills/` (unit-enforced). Advances OC-1/OC-2.
- `version-lockstep-covers-uvlock` (ci) — `uv.lock`'s project version stays in
  lockstep with `pyproject.toml`; `bump_version.py` syncs it and `--check`
  catches drift.
