# Architecture

Internal notes for maintainers. Not user-facing.

## Plugin manifest schema (verified 2026-05-05)

context7 was unavailable at implementation time; schema reverse-engineered from on-disk plugin manifests in `~/.claude/plugins/cache/`. Cross-checked against:

- `claude-plugins-official/superpowers/5.0.7/.claude-plugin/plugin.json`
- `derio-net/superpowers-for-vk/1.4.5/.claude-plugin/plugin.json`
- `claude-plugins-official/code-simplifier/1.0.0/.claude-plugin/plugin.json`

**Findings:**

- File location is hard-coded: `.claude-plugin/plugin.json`.
- Required fields: `name`, `version`, `description`.
- `author` is an **object** with `name` (and optional `email`), not a string. Common gotcha.
- Optional fields seen across plugins: `homepage`, `repository`, `license`, `keywords`.
- **Skills are auto-discovered from `skills/<name>/SKILL.md`**. There is no `skills` array in any of the three sampled `plugin.json` files. Do **not** enumerate skills in the manifest — the loader walks `skills/` directly.
- Each skill's `SKILL.md` carries its own frontmatter: `name`, `description`, `user-invocable` (bool), `disable-model-invocation` (bool), and optional `arguments` (list).

If the loader ever changes — symptom would be skills failing to register after install — re-verify the schema against a fresh plugin install and update this note.

## The plugin/template duality

This repo is two artifacts at once:

1. **A Claude Code plugin.** Installed via `/plugin install …`, registers three skills.
2. **A blog template source.** The `bootstrap-blog` skill renders `templates/hugo-hextra/` into a target directory.

Implication: the repo has zero runtime state. Each bootstrapped blog is an independent Git repo elsewhere on disk; this repo only ships the *recipes* (templates + skills).

## File convention: `.tmpl` vs verbatim

Inside `templates/hugo-hextra/`:

- Files ending in `.tmpl` are rendered with Go `text/template` using wizard answers, then `.tmpl` is stripped on write. (Why Go and not Python: Hugo itself uses Go templates, so the rendering semantics match exactly.)
- Files **without** `.tmpl` are copied verbatim. Used for blog-agnostic shortcodes (`screenshot.html`, `asciinema.html`) and any file where templating would corrupt the output (e.g. files that contain literal `{{ }}` Hugo shortcode examples).

The renderer at `tools/render-template/main.go` enforces this convention.

## Wizard → config → skill data flow

```
bootstrap-blog wizard
        │
        ▼
  collected answers (in-memory YAML map)
        │
        ▼
  tools/render-template/main.go
   ── reads templates/hugo-hextra/
   ── writes <target_dir>/...
        │
        ▼
  <target_dir>/.blog-craft.yaml   ◄────────┐
  + Hugo site files                        │
        │                                  │
        ▼                                  │
  later: blog-post / media skills    ──────┘
   ── walk up from CWD to find .blog-craft.yaml
   ── consume identity/series/voice/image_gen
```

The single discovery contract: a directory is "a blog-craft blog" iff it contains `.blog-craft.yaml`.

## Why Hugo + Hextra only

Frank's blog uses this stack and it's battle-tested. Adding pluggable SSGs would 3x the surface area (per-SSG renderers, per-SSG frontmatter dialects, per-SSG path conventions) for v1. If demand for Astro/Eleventy/etc. ever materialises, fork the renderer or add a second template subdirectory; don't try to abstract over SSGs.

## What blog-craft does not own

- Deploy pipelines (each blog picks its own host)
- Theme customisation beyond Hextra defaults (each blog edits its own `hugo.toml` and CSS)
- Image-generation backend (Gemini hardcoded in v1; the `image_gen.provider` field is reserved for future backends but enforces `gemini` today)
- Multi-character "lore bibles" (single persona + visual constants only)
