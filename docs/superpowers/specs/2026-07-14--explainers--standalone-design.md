# Standalone mode for explainers content-type

**Status:** Draft
**Date:** 2026-07-14
**Depends on:** [`2026-07-14-explainers-content-type`](../implemented/plans/2026-07-14-explainers-content-type)

## Problem

The `explainers` content-type (shipped in the parent plan) requires a
Hugo+Hextra blog with a `.blog-craft.yaml` config. The scaffold writes
Hugo page bundles under `content/docs/<series>/`, and the skill lifecycle
expects a blog root. This prevents using the explainer workflow for
projects that don't use blog-craft — a common case when an operator wants
to explain a standalone codebase feature, present a skill, or document an
architecture decision without spinning up a full blog.

## Goals

- **Standalone mode** for the scaffold script: produces a plain markdown
  file instead of a Hugo page bundle. No `.blog-craft.yaml` required.
- **Render to self-contained HTML**: a tool that converts an explainer
  markdown file into a standalone `.html` file with all CSS inlined and
  Mermaid JS loaded from CDN. No Hugo, no server, no blog-craft setup.
- **Per-post style customization**: built-in visual themes and support for
  custom CSS, controllable per document via frontmatter or CLI flag.
- **No changes to blog mode**: the existing blog-craft lifecycle continues
  to work identically; standalone mode is an added `--standalone` flag, not
  a fork.

## Non-goals

- No dossier/citation gate in standalone mode (same as blog mode).
- No web research — the `explainer-researcher` subagent is already
  read-only local; standalone mode uses it the same way.
- No remote repo cloning — the operator provides a local path.
- No Hugo/Hugo-compatible output in standalone mode — the HTML is meant
  for direct browser consumption, not for deployment in an SSG pipeline.

## Design

### Scaffold script extension (`tools/scaffold-explainer.sh`)

New flags:

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--standalone` | flag | off | Enable standalone mode |
| `--output <dir>` | path | `.` | Output directory for the `.md` file |
| `--target <path>` | path | — | Path to the codebase being explained (recorded in frontmatter) |
| `--weight-offset <n>` | int | `1` | Weight offset for post ordering |

When `--standalone` is set:
- `--config` is NOT required (falls back to `weight_offset=1`,
  `series_key="explainers"`)
- Output is `<output>/<NN>-<slug>.md` (not a Hugo bundle)
- Frontmatter includes `standalone: true` and `target: <path>`
- `--output` defaults to `.` (current directory)

When `--standalone` is NOT set, behavior is identical to the parent plan's
scaffold (backwards compatible).

### Render script (`tools/render_explainer.py`) — NEW

Converts an explainer markdown file (with YAML frontmatter) to a self-contained
HTML page. Dependencies: `markdown` (Python library), `pyyaml` (already a
blog-craft dependency).

```bash
python tools/render_explainer.py <input.md> [--style <theme>] [-o <output.html>]
```

**Themes** (built-in):
- `light` (default) — white background, serif body, blue accent.
- `dark` — GitHub-dark background, light text, blue accent.
- `minimal` — system-ui sans-serif, no frills.

**Custom CSS**: `--style /path/to/custom.css` loads the file as the theme.

**Frontmatter override**: the field `standalone_style` in the explainer's YAML
frontmatter picks a theme per-document. CLI `--style` explicitly set wins over
frontmatter; if omitted, frontmatter's `standalone_style` is used.

**Output**: self-contained HTML — all CSS inlined as a `<style>` block.
Mermaid diagrams are detected in the content and load Mermaid JS from CDN
via a `<script>` tag. Nothing else is external.

### Skill lifecycle extension (`skills/explainers/SKILL.md`)

Add a "Standalone mode" lifecycle track parallel to the blog-mode lifecycle.
The research, draft, and visuals steps are shared. Only scaffold and
publish/render differ:

| Step | Blog mode | Standalone mode |
|------|-----------|----------------|
| Scaffold | `--config .blog-craft.yaml NN slug` | `--standalone --output <dir> --target <path> NN slug` |
| Output | Hugo page bundle `content/docs/.../index.md` | Markdown file `<dir>/<NN>-<slug>.md` |
| Publish | `validate_explainers.py --config ...` + `draft: false` | `render_explainer.py --style <theme> -o out.html` |
| Result | Hugo site | Self-contained HTML file |

## Testing

- `test_scaffold_explainer.py` — extend with `test_scaffold_standalone_creates_md`
  and `test_scaffold_standalone_refuses_duplicate`.
- `test_explainers_standalone.py` (NEW) — render script tests: produces valid
  HTML, respects `--style` flag, loads custom CSS, reads `standalone_style` from
  frontmatter, includes Mermaid JS when content has mermaid fences, returns
  graceful fallback when `markdown` library is absent.
- `test_mirrors.py` — add `render_explainer.py` mirror pair.

## Rollout

Pure plugin code (new tool, scaffold flag, docs) — no deploy surface, no
post-merge Test Plan. Bump patch version on merge.

## Implementation Plans

| Plan | Repo | File | Depends on |
|------|------|------|------------|
| 2026-07-14-explainers-standalone | `derio-net/blog-craft` | standalone mode | explainers-content-type |
