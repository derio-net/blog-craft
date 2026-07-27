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

## The path manifest answers two different questions

`templates/manifest.yaml` is consulted by the reproduction harness and `/update`.
It carries two independent classifications of every materialized path, and they
are easy to conflate:

- **Class** — *who owns this file?* `framework` (shipped, overwritten),
  `merged` (config-templated, 3-way merged), `content` (operator's, never
  touched). Guard: `tests/unit/test_path_manifest.py`.
- **Root** — *who defines this path's location?* `site` (Hugo's layout — lands
  under `site_dir`) or `repo` (a contract outside Hugo — never prefixed).
  Guard: `tests/unit/test_path_roots.py`.

The root model exists because getting it wrong is **silent**. A workflow at
`<site_dir>/.github/workflows/` is not an error and not a skipped run — it is an
inert YAML document that looks exactly like a workflow, and blog-craft shipped
one to every `site_dir` blog until #61. The deciding question is never "is this a
dotfile": `.gitignore` is site-rooted (nested gitignores govern their own
subtree) while `.github/**` is not.

Both guards require **exactly one** match per materialized path, so a new
template file cannot merge without a reviewer answering both questions. At
runtime an undeclared root falls back to `site`, so a missed declaration is a
failing test, never a broken blog.

A third section, `legacy_dests:`, records where earlier releases put a path that
has since moved. `/update` uses it to relocate the operator's copy instead of
adding a fresh one beside it — without it, `plan_update` reads an absent managed
path as `add` and re-creates the dead file on every run.

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
   ── consume identity/series/voice/image
```

The single discovery contract: a directory is "a blog-craft blog" iff it contains `.blog-craft.yaml`.

## Why Hugo + Hextra only

Frank's blog uses this stack and it's battle-tested. Adding pluggable SSGs would 3x the surface area (per-SSG renderers, per-SSG frontmatter dialects, per-SSG path conventions) for v1. If demand for Astro/Eleventy/etc. ever materialises, fork the renderer or add a second template subdirectory; don't try to abstract over SSGs.

## The educational-writing methodology + quality gate

The `educational-writing` skill (`skills/educational-writing/`) is not a
scaffolder — it's the shared **methodology** the authoring skills consume. It
encodes, self-contained and citing provenance, three things: reader-first
structure ([Diátaxis](https://diataxis.fr/) — tutorial / how-to / reference /
explanation), evidence-grounding (no claim without a citable artifact), and a
thin-persona rule (the character frames, it doesn't carry the teaching). It exists
because the default failure mode of a drafted post is *prose about the session
that made it* — witty, in-character, useless to a reader who needs to
build/operate/fix the thing.

Data flow:

- `/blog-post` and `/post-rewrite` **load** `educational-writing/SKILL.md` + its `references/` to shape drafts, and dispatch the read-only `post-researcher` agent (`agents/post-researcher.md`) to gather evidence from a source repo — the narrative/operational analogue of `explainer-researcher`.
- Two frontmatter fields carry the discipline onto every `content_type: posts` post: `reader_goal` (what the reader can *do* afterward) and `diataxis` (the mode).
- The structural **gate** is `tools/validate_educational.py` — it can't judge prose, only the *presence* of evidence (reader_goal, diataxis, a command block, an actionable section). It's config-driven via the optional top-level `quality` block (§7 of CONFIG.md), deliberately **not** a content-type: it applies to all regular posts, and skips papers/explainers (which have their own validators).
- Materialization mirrors the papers convention: the validator ships byte-identical at both `tools/validate_educational.py` (skills call it) and `templates/hugo-hextra/scripts/validate_educational.py` (framework-class per the manifest — copied into every blog so a plain-python CI runs the gate without the plugin). A unit test guards against drift.

Why self-contained rather than vendoring an external writing skill: blog-craft's
core value is portability. The strongest available external skills are either
SEO/AI-citation-oriented (wrong goal for a teaching blog) or a different domain
(academic). Diátaxis is the established framework; we adopt it and cite it rather
than reinvent or take a heavyweight dependency.

## What blog-craft does not own

- Deploy pipelines (each blog picks its own host)
- Theme customisation beyond Hextra defaults (each blog edits its own `hugo.toml` and CSS)
- Image-generation backend (Gemini hardcoded in v1; the `image.provider` field is reserved for future backends but enforces `gemini` today)

## The glossary's scan → author → apply split

`/glossary` is three helpers and one model step, in that order, and the
boundaries matter:

1. `tools/glossary_scan.py` — finds candidate tokens. Pure text, fully tested.
2. **the skill writes the definitions** — the only step that needs a model.
3. `tools/glossary_apply.py` — inserts the markers. Pure text, fully tested.
4. `tools/validate_glossary.py` — the CI gate. Pure text, fully tested.

The split exists because "what does NUT stand for, and why does a reader of
*this post* care?" is genuinely a judgement call, while "is this token inside a
code fence?" is not. Putting the second kind of question in prose instructions
means an agent re-improvises it every run, and the failure mode — a marker
written into a code sample — is a corrupted post.

**One exclusion scanner, three consumers.** `glossary_scan.excluded_spans()` is
public and imported by both the applier and the validator rather than
reimplemented. If propose and apply ever disagreed about what counts as prose,
the applier would write markers the scanner would never have proposed. There is
also a deliberately narrower `code_spans()` — fences, indented code, inline
code, frontmatter, but *not* headings — used by the validator, because a post
that documents `{{< abbr >}}` inside a fence must not be gated on its own
example, while a marker in a heading really does execute and really must be
validated.

`excluded_spans()` also covers the **body** of any shortcode in
`OPAQUE_BODY_SHORTCODES` — currently just `papers/landscape`, whose `.Inner`
Hugo wraps in `<pre class="mermaid">`. That body is renderer source, not prose:
a marker there expands to a `<button popovertarget>` tree inside a chart axis
and the diagram fails to parse. The criterion is deliberately *the body is
handed to a renderer*, not *the shortcode has a body* — `papers/pullquote` and
`papers/scar` take prose bodies that must stay markable, and excluding every
shortcode body would silently drop legitimate markers.

`misplaced_markers()` is the fourth consumer. It reports markers an earlier
sweep already wrote into such a body, which `excluded_spans()` alone cannot
reach: the applier is idempotent, so it never removes what it would no longer
add. It subtracts `code_spans()` for exactly the reason above — a post
documenting the shortcode inside a fence must not be failed by its own example,
and two functions disagreeing about what counts as a marker is precisely the
drift this shared scanner exists to prevent.

That import is why `glossary_scan.py` is mirrored into
`templates/hugo-hextra/scripts/` alongside `validate_glossary.py`: a
materialized blog runs its CI with plain python and no plugin on `sys.path`, so
the companion has to travel with it. Both pairs are guarded by
`tests/unit/test_mirrors.py`.
