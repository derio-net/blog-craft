---
name: blog-craft-explainers
description: Write a technical deep-dive post (explainer) in a blog-craft blog whose config enables the explainers content-type. Triggers on "write an explainer", "deep-dive post", "explain this feature as a post". Walks a reader through one feature of a codebase, presents a Claude Skill, compares similar skills, or explains a cross-cutting concern. Dormant unless content_types.explainers.enabled in .blog-craft.yaml.
user-invocable: true
disable-model-invocation: false
arguments:
  - series
  - number
  - slug
  - title
  - archetype
---

# Explainers (opt-in content-type)

An **Explainer** is a technical deep-dive post — walking a reader through one
feature of a codebase, presenting a Claude Skill, comparing two similar skills,
or explaining a cross-cutting concern (testing pyramid, deployment strategy,
security posture). This skill is only relevant in a blog-craft blog whose
`.blog-craft.yaml` sets `content_types.explainers.enabled: true` and has a
series with `content_type: explainers`.

All thresholds, paths, and the weight offset come from
`content_types.explainers` in `.blog-craft.yaml` — nothing here is hardcoded.

## Archetypes

The `archetype` frontmatter field records which recipe produced the post, and
`scaffold-explainer.sh --archetype <id>` emits that archetype's section
structure. All six modes are scaffolded and validated:

| id | mode |
|---|---|
| `feature-deep-dive` (default) | Walking through one feature of a codebase |
| `skill-presentation` | Presenting a single Claude Skill |
| `skill-comparison` | Comparing two similar skills |
| `testing-pyramid` | The testing layers of a specific repo |
| `deployment-strategy` | How code gets from merge to production |
| `security-posture` | What's enforced, what's manual, the threat surface |

`feature-deep-dive`'s recipe is the scaffolded six-section skeleton; the other
five recipes (section structure + content guidance) live in
`skills/explainers/references/archetypes.md`. `validate_explainers.py` enforces
that a post's `##` sections match its declared archetype (every recipe heading,
in order; extra sections allowed) and rejects an unknown archetype. The check
counts only plain ATX `## ` headings — keep the scaffolded heading style (not
setext underlines or `## Foo ##`), and `## ` lines inside ``` / `~~~` code
fences are ignored.

## Lifecycle

1. **Find + validate the blog** — walk up from the working directory for
   `.blog-craft.yaml`; confirm `series` has an entry with
   `content_type: explainers`. Stop if not found or not enabled.

2. **Research** — dispatch the `explainer-researcher` subagent at the target
   path/topic. It returns a structured markdown brief (key files with
   `file:line` references, an architecture summary, tradeoffs surfaced from
   code, comments, or commit history). This keeps heavy exploration out of the
   drafting session's context.

3. **Scaffold** — create the page bundle:
   ```bash
   bash <blog-craft>/tools/scaffold-explainer.sh --config .blog-craft.yaml \
       [--archetype <id>] <NN> <slug>
   ```
   Writes `content/docs/<series>/<NN>-<slug>/index.md` with
   `weight = NN + weight_offset` and the selected archetype's section skeleton.
   `--archetype` defaults to `feature-deep-dive` (Overview, Why it exists, How
   it works, Code walkthrough, Tradeoffs & alternatives, Try it yourself); the
   other five ids emit their own recipe's sections.

4. **Draft** — fill every section using the research brief, following the
   scaffolded section headings and their budget comments. For the five
   non-`feature-deep-dive` archetypes, `references/archetypes.md` gives the
   fuller content guidance (what each section should contain, recommended
   visuals). **Keep the scaffolded `##` headings** — the validator enforces
   them per archetype (you may append extra sections).

5. **Visuals** — Mermaid fences for diagrams/flows (Hextra renders these
   natively); Hextra `cards`/`tabs`/`callout` shortcodes for side-by-side
   comparisons or callout boxes where an archetype needs them.

6. **Media + cover** — run `/media` for any `<!-- MEDIA: -->` placeholders;
   generate a cover via `/blog-post`'s existing image flow.

7. **Validate + publish** —
   ```bash
   python <blog-craft>/tools/validate_explainers.py --config .blog-craft.yaml \
       content/docs/<series>/<NN>-<slug>/index.md
   ```
   Frontmatter + weight invariant + archetype section structure (no dossier
   fields). Set `draft: false` when ready.

## Standalone mode

Use standalone mode when the target is **any codebase** — not necessarily a
blog-craft blog. No `.blog-craft.yaml` needed.

1. **Research** — same as above: dispatch `explainer-researcher` on the target
   path.

2. **Scaffold** — create a standalone markdown file:
   ```bash
   bash <blog-craft>/tools/scaffold-explainer.sh --standalone \
       --target <path-to-codebase> \
       --output <dir> \
       [--archetype <id>] \
       <NN> <slug>
   ```
   Writes `<dir>/<NN>-<slug>.md` with `standalone: true` and `target: <path>`
   in its frontmatter (and the selected archetype's sections). No Hugo bundle,
   no blog root.

3. **Draft** — fill every section same as blog mode.

4. **Render to HTML** — convert the markdown to a self-contained HTML page:
   ```bash
   python <blog-craft>/tools/render_explainer.py <dir>/<NN>-<slug>.md
       --style light     # light | dark | minimal | /path/to/custom.css
       -o out.html
   ```
   Produces a single `.html` file with all CSS inlined and Mermaid JS loaded
   from CDN. Open in any browser — no Hugo, no server, no blog-craft setup.

### Style customization

The `--style` argument controls the visual theme. Four built-in themes:
`light` (default), `dark` (code-friendly), `minimal` (bare-bones), and
`broadsheet` (a warm-dark editorial theme — display + body serif, a
two-accent brass/teal system, hairline rules). Each style themes its own
Mermaid diagrams. Any file path given as `--style` is loaded as custom CSS,
so each explainer can have its own look:

```bash
python <blog-craft>/tools/render-explainer.py post.md --style ./my-theme.css
```

**Self-contained fonts (`--embed-fonts`).** `broadsheet`'s distinctive type
needs web fonts. `--embed-fonts` inlines the bundled Fraunces + Newsreader
woff2 as base64 `@font-face` data URIs, so the page carries its fonts with no
external requests (offline-safe, Artifact-CSP-safe). Without it, broadsheet
falls back to system serifs.

```bash
python <blog-craft>/tools/render-explainer.py post.md --style broadsheet --embed-fonts
```

The bundled fonts (latin + latin-ext, ~744K, SIL OFL 1.1) live under
`templates/content-type-explainers/shared/fonts/broadsheet/`; regenerate them
with `tools/fetch_broadsheet_fonts.py`. For archetypes where Mermaid's
auto-layout fights the content, see `references/schematics.md` for CSS-only
schematic primitives.

The frontmatter field `standalone_style` lets the *document itself* declare
its preferred theme — overrides the CLI default, but CLI `--style` still
wins when set explicitly:

```yaml
standalone_style: dark
```

- `weight = post_number + weight_offset` (Hextra sorts `weight: 0` last).
- `series` must be a **list** (`[<series-key>]`) — Hextra's opengraph needs it.
- No dossier — don't invent one. The explainers content-type is deliberately
  lighter than papers.
