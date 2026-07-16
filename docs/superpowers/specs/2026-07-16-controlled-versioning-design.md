# Controlled versioning on merge + version-aware clients

- **Issue:** derio-net/blog-craft#18
- **Branch:** `feat/controlled-versioning`
- **Date:** 2026-07-16
- **Type:** feature (version tooling + CI + client stamping + CHANGELOG)
- **Reference:** derio-net/super-fr's system (pyproject canonical + bump-guard +
  auto-tag), ported and simplified for blog-craft.

## Problem (live)

Four features (#25/#26/#22/#27) merged mutating `templates/` and `tools/`, but
the manifests are frozen at `0.4.0` and the only tag is `v0.2.0`. "Version"
means three unsynchronized things: two manifests' semver, rare manual tags, and
whatever string a client's `blog_craft_version` holds. `tools/update.py` needs
`blog_craft_version` to be a resolvable git ref (`git archive <ref>`), but
`bootstrap-render.sh` never stamps it.

## Operator decisions (batched Q&A, 2026-07-16)

1. **Design + implement now** — port super-fr's proven system to a working PR
   and cut the first real version covering the four merged features.
2. **Manual bump + CI guard + auto-tag** — author runs `bump_version.py
   <patch|minor|major>` in the PR; CI fails a behavior-changing PR that didn't
   bump; `auto-tag.yml` cuts `vX.Y.Z` + a GitHub Release on merge.
3. **Add `pyproject.toml`** as the single canonical source; both manifests sync
   from it (with a `--check` drift guard).
4. **Include client version-awareness now** — `bootstrap-render.sh` always
   stamps `blog_craft_version` = the current release tag; `update.py` resolves it.

## Design

### Canonical version — `pyproject.toml` (new)

Minimal `[project]` table with `name = "blog-craft"` and
`version = "0.5.0"`. The single source of truth.

### `tools/bump_version.py`

Ported/simplified from super-fr (no uv workspace, no entry-point probe):
- `bump_version.py <patch|minor|major|X.Y.Z>` — compute the new semver, write it
  to `pyproject.toml`, and sync `.claude-plugin/plugin.json` `version` +
  `.claude-plugin/marketplace.json` `plugins[].version` (preserving JSON
  formatting/indent).
- `bump_version.py --check` — print every version surface; exit 1 on drift.

### `tools/check_version_bump_needed.py` (CI guard)

`check_version_bump_needed.py <base-ref>` — if the PR's diff touches a
**version-required path** and `pyproject.toml`'s version equals the base's,
fail with the offending paths. Required paths (the shipped surface):
`templates/**`, `tools/**`, `skills/**`, `agents/**`, `.claude-plugin/**`.
Docs/tests/specs alone never require a bump.

### `.github/workflows/auto-tag.yml` (new)

On push to `main` changing `pyproject.toml`: read the canonical version, and if
`v<version>` doesn't already exist, cut an annotated tag + a GitHub Release with
auto-generated notes (idempotent). Closes the loop: bump in PR → merge → tag.

### CI guard wiring — `.github/workflows/ci.yml`

A PR-only step running `check_version_bump_needed.py` against the PR base, plus
`bump_version.py --check` in the test job (drift tripwire on every push).

### Client loop

- `tools/bootstrap-render.sh` reads the canonical version and injects
  `blog_craft_version: "v<version>"` into the render answers when the operator
  didn't set one — so every bootstrapped blog records a **resolvable tag**.
- `templates/hugo-hextra/.blog-craft.yaml.tmpl` already emits the field; it is
  now always populated at bootstrap.
- `tools/update.py` already resolves `blog_craft_version` via `git archive` — no
  change beyond a doc note that it is now reliably stamped.

### `CHANGELOG.md` (new)

Keep-a-Changelog style. The `0.5.0` entry records the four previously-unversioned
features (#25/#26/#22/#27) + this versioning system (#18).

### Cut the first version

Bump `0.4.0 → 0.5.0` (minor — features added) in this PR; the CHANGELOG's 0.5.0
section covers the backlog. On merge, `auto-tag.yml` cuts `v0.5.0`.

## Test Plan

Tooling + CI + a shell stamping change. **No deployment** → no post-merge Test
Plan. Verification is the unit suite + the bootstrap smoke test.

### Unit tests (`tests/unit/test_version.py`, new)

- `bump_version` patch/minor/major/explicit arithmetic.
- after a bump, `pyproject.toml`, `plugin.json`, `marketplace.json` all agree
  (round-trip on a temp copy); `--check` returns 0 when synced.
- `--check` returns 1 when a manifest is manually drifted.
- `check_version_bump_needed`: a diff touching `templates/x` without a version
  change → exit 1; with a version change → 0; a docs-only diff → 0.
- the shipped repo is self-consistent (`bump_version.py --check` == 0) —
  a tripwire that the committed manifests match `pyproject.toml`.

### Smoke (`tests/smoke-bootstrap.sh`, +assert)

- a bootstrapped blog's `.blog-craft.yaml` carries a `blog_craft_version:
  "vX.Y.Z"` line (stamped, resolvable).

## Acceptance rows (matrix backfill — same PR)

- **VER-1** — "bump_version.py --check fails on manifest/pyproject drift" —
  `unit=blog-craft:tests/unit/test_version.py`, ci.
- **VER-2** — "a PR changing templates/ or tools/ without a version bump fails
  CI" — `unit=blog-craft:tests/unit/test_version.py`, ci.
- **VER-3** — "bootstrap stamps a resolvable blog_craft_version tag" —
  `int=blog-craft:tests/smoke-bootstrap.sh`, ci.

## Out of scope

- "Client knows how far behind it is" (changelog-diff surfaced to the operator)
  — a nice follow-up once tags exist; this PR guarantees the resolvable ref.
- Retro-tagging historical commits (only `v0.2.0` exists; we start clean at
  `v0.5.0`).
