# Changelog

All notable changes to blog-craft are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and blog-craft adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The canonical version lives in `pyproject.toml`; `tools/bump_version.py` keeps
the plugin manifests in lockstep, and `.github/workflows/auto-tag.yml` cuts the
matching `vX.Y.Z` tag on merge (#18).

## [Unreleased]

## [0.8.0] - 2026-07-17

### Fixed
- **OpenCode mirror + uv.lock sync drift:** `scripts/install.sh` no longer
  leaves the working tree dirty on every run. The committed `.opencode/` skill
  mirrors were stale (broadsheet #22 and archetype-modes #35 never re-synced);
  they are now regenerated to match canonical `skills/`, and
  `tests/unit/test_opencode_sync.py` fails CI on any future mirror drift.
  `uv.lock` pinned the project at 0.4.0 while `pyproject.toml` had moved on
  (bumps never touched the lockfile); `tools/bump_version.py` now keeps
  `uv.lock`'s blog-craft `version` in lockstep (name-anchored — the line-1
  `version = 1` schema is never touched) and `--check` (the committed-repo
  self-consistency tripwire) now covers it.

## [0.7.0] - 2026-07-17

### Added
- **Explainer archetype modes:** `scaffold-explainer.sh --archetype <id>` now
  scaffolds all six explainer modes (`feature-deep-dive`, `skill-presentation`,
  `skill-comparison`, `testing-pyramid`, `deployment-strategy`,
  `security-posture`), each emitting that mode's section structure — previously
  five were guidance-only prose with no scaffold. `validate_explainers.py`
  gained a structural check: a post's `##` sections must match its declared
  archetype's recipe (every heading, in order; extra sections allowed), and an
  unknown archetype is rejected. Both scripts mirror into
  `templates/content-type-explainers/shared/scripts/`; docs updated in
  `skills/explainers/SKILL.md` and `references/archetypes.md`.

## [0.6.0] - 2026-07-16

### Added
- **Batch-rewrite changelog (#28):** `tools/assemble_changelog.py` assembles a
  per-post campaign changelog from per-post change entries — hoisting the items
  common to every post into a "Conventions Applied to Every Post" table
  (set-intersection, no manual dedup) and rendering the frank format. Documented
  in `skills/educational-writing/references/changelog.md` and wired as the
  end-of-campaign step in `post-rewrite`'s batch mode.

## [0.5.0] - 2026-07-16

The first release under controlled versioning — it also establishes the scheme
itself and folds in four features that had merged without a version bump.

### Added
- **Controlled versioning (#18):** `pyproject.toml` is the single canonical
  version; `tools/bump_version.py` syncs both `.claude-plugin` manifests;
  `tools/check_version_bump_needed.py` fails a PR that changes the shipped
  surface (`templates/`, `tools/`, `skills/`, `agents/`, `.claude-plugin/`)
  without a bump; `.github/workflows/auto-tag.yml` cuts `vX.Y.Z` + a Release on
  merge. Bootstrapped blogs now stamp a resolvable `blog_craft_version` tag.
- **Diagram quality gate (#25):** how-to / tutorial posts must carry a
  `mermaid` diagram (`gate.require_diagram`, on by default; `diagram_exempt`
  opt-out).
- **Batch / campaign post-rewrite mode (#26):** a documented small-batch,
  in-place, live-preview workflow plus the reproducible `scripts/batch-gate.sh`.
- **Broadsheet explainer style (#22):** a warm-dark editorial `--style`,
  `--embed-fonts` self-contained web-font embedding, per-style Mermaid theming,
  and `references/schematics.md`.
- **Build-time Mermaid syntax validator (#27):** `tools/validate_mermaid.py`
  lints `mermaid` fences (subgraph-targeting edges, bare `<br>`, unbalanced
  brackets) across all content types; on by default, opt out with
  `quality.mermaid_syntax: false`.

### Fixed
- Registered the `validate_educational.py` and (now) `validate_mermaid.py`
  tool↔template mirror pairs in the byte-identity guard (#25/#27).

[Unreleased]: https://github.com/derio-net/blog-craft/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/derio-net/blog-craft/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/derio-net/blog-craft/releases/tag/v0.5.0
