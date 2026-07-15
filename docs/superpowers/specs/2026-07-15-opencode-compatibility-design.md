# OpenCode Compatibility for blog-craft

## Goal

Adapt blog-craft (a Claude Code plugin) so it works as an OpenCode project out
of the box: OpenCode discovers its skills, registers its slash commands, loads
its project instructions, and the installer handles both Claude Code and
OpenCode delivery in a single `scripts/install.sh` run.

## Motivation

blog-craft ships 9 skills (`skills/<name>/SKILL.md`) that are fully functional
under Claude Code's plugin system. OpenCode (github.com/anomalyco/opencode) has
no plugin concept — it discovers skills from `SKILL.md` files in well-known
directories (`~/.config/opencode/skills/`, `.opencode/skills/`) and slash
commands from `commands/<name>.md` files. Without adaptation, OpenCode users
cannot use `/blog-post`, `/bootstrap-blog`, etc.

The reference implementation is `derio-net/super-fr`, a Claude Code plugin that
was extended for OpenCode parity in June 2026 — it ships `opencode.json`,
`.opencode/` mirrors, `scripts/install.sh`, and `scripts/sync-opencode.py`.

## Design

### 1. `opencode.json` (repo root)

Tells OpenCode where to find project-level custom instructions.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": [".opencode/instructions/*.md"]
}
```

### 2. `.opencode/` directory structure

```
.opencode/
├── .gitignore        # Ignore generated artifacts (node_modules, etc.)
├── skills/           # Mirror of skills/<name>/SKILL.md (generated)
│   ├── blog-post/SKILL.md
│   ├── bootstrap-blog/SKILL.md
│   ├── educational-writing/SKILL.md
│   ├── explainers/SKILL.md
│   ├── media/SKILL.md
│   ├── media-screenshots/SKILL.md
│   ├── papers/SKILL.md
│   ├── post-rewrite/SKILL.md
│   └── update/SKILL.md
├── commands/         # Slash commands derived from skill frontmatter (generated)
│   ├── blog-post.md
│   ├── bootstrap-blog.md
│   ├── educational-writing.md
│   ├── explainers.md
│   ├── media.md
│   ├── media-screenshots.md
│   ├── papers.md
│   ├── post-rewrite.md
│   └── update.md
└── instructions/     # Markdown files loaded as project instructions (authored)
                      # Initially empty — can grow with blog-craft-specific rules.
```

#### 2a. Canonical vs mirror

`skills/<name>/SKILL.md` is the canonical source. `.opencode/skills/<name>/SKILL.md`
is a generated mirror — never hand-edited. `sync-opencode.py --check` detects drift.

#### 2b. Command format

Each command is `<name>.md` mirroring its matching skill, with frontmatter
description copied from the skill's `description` field:

```markdown
---
description: '<skill description>'
---
Use the `<name>` skill to handle this request.

$ARGUMENTS
```

This gives every skill a `/name` slash-command surface. Commands have no
canonical file of their own — they are derived entirely from skill frontmatter.

#### 2c. Instructions

blog-craft has no repo-wide agent rules akin to super-fr's
`fr-isolation-required.md` or `no-claude-p-batch.md`. The `.opencode/instructions/`
directory is created empty; the sync script manages it so future additions
are seamless.

### 3. `scripts/sync-opencode.py`

Python script that keeps `.opencode/` mirrors in sync with canonical sources.
Mirrors super-fr's `scripts/sync-opencode.py` design.

**Sources:**
- Skills: `skills/<name>/SKILL.md` (canonical) → `.opencode/skills/<name>/SKILL.md`
- Commands: Derived from skill frontmatter → `.opencode/commands/<name>.md`
- Instructions: Authored files → `.opencode/instructions/<name>.md`

**Modes:**
- Default (no flag): write/overwrite all mirrors to match canonical
- `--check`: exit non-zero on drift, make no writes (CI gate)

**Dependencies:** Python 3.11+, PyYAML, managed via uv. The sync script
imports `yaml` for frontmatter parsing and rendering (same as super-fr's).

A `pyproject.toml` is added at repo root declaring the project and its
dependencies (`pyyaml`), with dev-dependencies for tooling (pytest, ruff). The
standard way to run any Python script in this repo is `uv run <script>.py`.
The `install.sh` runs the sync script via `uv run scripts/sync-opencode.py`.
Existing shell-based test runners (`tests/run-unit.sh`, `tests/smoke-*.sh`)
are updated to use `uv run` where they invoke Python.

### 4. `scripts/install.sh`

Bash installer that sets up blog-craft for both Claude Code and OpenCode.

**Preflight:**
- Requires: `jq`, `rsync`, `git` (same as super-fr)
- Must run from a clean git checkout (same guard as super-fr)

**Claude Code delivery:**
1. Register `derio-net` marketplace in settings.json (`extraKnownMarketplaces`)
2. Register `derio-net` in `known_marketplaces.json`
3. Enable `blog-craft@derio-net` plugin in settings.json
4. Sync repo to marketplace cache dir (`~/.claude/plugins/marketplaces/derio-net/`)
5. Register plugin version in `installed_plugins.json`

**OpenCode delivery (always, since install.sh IS the OpenCode installation path):**
1. Run `scripts/sync-opencode.py` to refresh `.opencode/` mirrors
2. Copy skills to `~/.config/opencode/skills/<name>/SKILL.md`
3. Copy commands to `~/.config/opencode/commands/<name>.md`

**Uninstall (`--uninstall`):**
- Remove marketplace entries
- Remove plugin registration
- Remove OpenCode skills/commands

### 5. `.gitignore` updates

Add `.opencode/node_modules` (defensive — unused today, future-proof) and
`__pycache__/` entries for the `.opencode/` tree.

## Files changed (summary)

| File | Action |
|------|--------|
| `opencode.json` | **Create** — OpenCode config |
| `.opencode/.gitignore` | **Create** — ignore generated artifacts |
| `.opencode/skills/*/SKILL.md` | **Create** — mirrors (generated by sync script) |
| `.opencode/commands/*.md` | **Create** — slash commands (generated by sync script) |
| `.opencode/instructions/.gitkeep` | **Create** — empty instructions dir placeholder |
| `scripts/sync-opencode.py` | **Create** — mirror sync script |
| `scripts/install.sh` | **Create** — unified installer |
| `pyproject.toml` | **Create** — project metadata + uv dependency management |
| `tests/run-unit.sh` | **Update** — use `uv run` for Python invocation |
| `tests/smoke-*.sh` | **Update** — use `uv run` for Python invocation where applicable |
| `.gitignore` | **Update** — ignore `.opencode/` generated artifacts if any |

## Files NOT changed

- `skills/<name>/SKILL.md` — canonical, stays as-is
- `.claude-plugin/plugin.json` — Claude plugin manifest, unchanged
- `.claude-plugin/marketplace.json` — marketplace descriptor, unchanged
- All tools/, templates/, tests/, agents/ — untouched

## Test Plan

Post-merge, operator-driven:

1. **OpenCode skill discovery:** Run `opencode` in blog-craft root — confirm
   skills appear in the skill list (open schema).
2. **Slash commands:** Run `/blog-post` — confirm the skill loads.
3. **Instructions loaded:** Run with `--system-info` or observe agent behavior
   — confirm `.opencode/instructions/*.md` is loaded.
4. **Sync script:** Run `python3 scripts/sync-opencode.py --check` — exit 0.
   Run after editing a skill's description — exit non-zero.
5. **install.sh:** Run `bash scripts/install.sh` — confirm marketplace
   registration, plugin enablement, and OpenCode skills/commands are installed
   globally.
6. **Claude Code plugin:** Restart Claude Code — confirm `/blog-post` etc.
   still work (the Claude plugin path is not regressed).
