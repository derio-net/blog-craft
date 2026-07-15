# Educational-writing methodology, quality gate, and better defaults

**Status:** Retrospective (implemented directly on branch
`claude/blog-post-quality-improvement-kl1lcu`; this spec + its plan document
the change in the repo's convention so it can be reviewed, verified, and
extended from an fr-capable host).
**Date:** 2026-07-15

## Problem

blog-craft scaffolds and authors teaching blogs, but the default authoring
path (`/blog-post`) reliably produced posts whose *technical substance was
fine and whose voice was useless*: prose about the session that generated the
post — witty, in-character, "you had to be there" — instead of something a
reader can build, operate, or fix from. The operator's own example: two
graceful-shutdown posts with working code, tests, and runbooks, whose prose
was narrative-with-jokes and gave a reader with 10 minutes to debug a live
outage almost nothing.

Three narrower problems compounded it:

- **No structural discipline.** Nothing pushed a post toward a reader-goal, a
  documentation mode, real evidence, or an actionable/recovery section — and
  nothing could flag a post that lacked them.
- **No rewrite path.** An existing bad post had no tool to diagnose and
  re-shape it against a methodology while preserving the persona and cover.
- **Weak defaults for diagrams and style.** Papers rendered themed Mermaid
  diagrams; ordinary posts used hand-drawn ASCII boxes that misalign across
  fonts/zoom — because the Mermaid CSS was gated on `papers.enabled` and
  scoped to `.paper-post`. A non-papers blog (or an `/explainers` render) got
  Hextra's muted default or, in the standalone renderer, a Mermaid fence that
  rendered as a *code block* because codehilite mangled it.

## Goals

- A shared, self-contained **educational-writing methodology** (a skill + a
  references set) that the authoring skills load: reader-first structure
  ([Diátaxis](https://diataxis.fr/), adopted and cited, not reinvented),
  evidence-grounding (no claim without a citable artifact — real command +
  output, `file:line`, commit, test, config value), and a thin-persona rule.
- A **structural gate** (`validate_educational.py`) that mechanically enforces
  the evidence floor (a `reader_goal`, a declared `diataxis` mode, ≥1
  command/output block, an actionable section), scoped to `content_type: posts`
  and skipping papers/explainers (they have their own validators). Config via
  an optional top-level `quality` block; wired into the shipped blog CI when
  `quality.enabled`.
- A **`/post-rewrite`** skill that diagnoses an existing post against the
  methodology, gathers the evidence it omitted, and re-shapes it — keeping the
  persona a thin frame and the cover untouched, non-destructively (`.bak` +
  approval + re-gate).
- A read-only **`post-researcher`** subagent that gathers evidence from a
  source repo: the *actual code* (not inferred), the design substrate
  (`docs/superpowers/{specs,plans}` and the `implemented/` trees), and the
  divergence between intended design and shipped code — the reader's most
  likely walls.
- **Better authored voice**: an orientation ("set the stage") requirement; a
  configurable `voice_level` dial (`dry`/`balanced`/`rich`); a chronicle
  register (report what *we* did, past tense, over bare imperatives);
  verbose/multi-line snippets; runnable Verify steps; a missteps table
  pattern; a "no drafting-artifact meta-commentary" rule.
- **Better defaults**: a global Mermaid theme (every post/content-type, light
  + dark); prefer-Mermaid-over-ASCII guidance; a fixed + themed standalone
  explainer Mermaid render; a `{{< last-updated >}}` stamp for posts that
  mirror code state.

## Non-goals

- No change to the enforcement philosophy of `papers` (its dossier gate stays
  papers-specific) or to `media`.
- No content-sniffing in the gate — it checks structure/evidence *presence*,
  never prose quality (which no validator can judge).
- No new config schema version / migration: `quality` and `voice_level` are
  optional keys (like `content_types`), rendered only when present; golden
  fixtures unchanged.
- No vendoring of an external writing skill — surveyed options were SEO- or
  academic-oriented; Diátaxis is adopted and cited instead.
- No Hugo theme overhaul beyond the Mermaid default + the last-updated
  shortcode.

## Design

### New skill: `skills/educational-writing/`

Model- and user-invocable methodology (the shared brain the authoring skills
load): `SKILL.md` + `references/{diataxis,evidence,checklist,voice}.md`.
Encodes the one test ("2am, 10 minutes to fix — does the post give them what
they need?"), the Diátaxis compass, evidence-grounding, orientation (§2a),
the thin-persona rule, the failure signatures (incl. drafting-artifact
meta-commentary), and the pre-publish checklist.

### Gate: `tools/validate_educational.py` (+ blog-side mirror)

`validate_post(fm, body, gate) -> list[str]`; CLI reads `quality.gate` from
`.blog-craft.yaml` (defaults built in). Checks: `reader_goal` present;
`diataxis` present and valid (tutorial|how-to|reference|explanation, with
aliases); ≥ `min_command_blocks` fenced blocks (mermaid excluded); an
actionable heading (Reproduce/Runbook/Steps/Verify/Recover/…). Skips posts
whose series `content_type != posts`, and honors `quality_exempt`. Mirrored
byte-identical to `templates/hugo-hextra/scripts/validate_educational.py`
(framework-class, materialized into every blog) so a plain-python CI runs it
without the plugin; a unit test guards the mirror.

### Config: optional top-level `quality` + `voice_level`

```yaml
quality:
  enabled: true                       # bootstrap default; wires the CI gate step
  gate:
    require_reader_goal: true
    require_diataxis_mode: true
    min_command_blocks: 1
    require_actionable_section: true
voice_level: balanced                 # dry | balanced | rich
```

Both optional and passthrough-rendered in `.blog-craft.yaml.tmpl`; the CI
template adds the gate step under `{{ with .quality }}{{ if .enabled }}`.
Seeded series-overview pages carry `quality_exempt` so a fresh blog stays
green.

### `/post-rewrite` + `agents/post-researcher.md`

Rewrite skill: locate → diagnose (failure signatures + gate) → dispatch
`post-researcher` (reads real code + specs/plans, cross-checks intent vs
shipped) → set `reader_goal`/`diataxis` → re-shape at the resolved
`voice_level` (orientation, foundation-with-redirects, lead-with-how-to,
reference block, missteps table, recovery path, labelled explanation,
verbose snippets, Mermaid diagrams, `last_updated` stamp) → side-by-side
approval → `.bak` + write → `/media` → re-gate. Subagent is read-only
(Glob/Grep/Read) and returns a structured evidence brief incl. a
"design-intent vs. what shipped" section.

### Frontmatter additions (on `content_type: posts`)

`reader_goal` (what the reader can DO), `diataxis` (mode[s]); and, for posts
that mirror code state, `last_updated` + `last_updated_commit`.

### Default Mermaid theme + explainer render + last-updated shortcode

Move the Mermaid SVG styling out of the papers gate and `.paper-post` scope
into an always-present `.content .mermaid` block (light + dark) in
`custom.css.tmpl`; the `features.css.mermaid_palette` override becomes global
and wins everywhere via `!important`. `render_explainer.py`: stash Mermaid
fences before markdown (codehilite was rendering them as code blocks) and
initialize Mermaid with a `theme:'base'` palette matching the page.
`layouts/shortcodes/last-updated.html` renders a dated, sha-linked stamp from
frontmatter.

## Mirror-pair discipline

`tools/validate_educational.py` is canonical and mirrored byte-identical into
`templates/hugo-hextra/scripts/validate_educational.py` (same pattern as the
papers/explainers validators). A unit test asserts byte-equality.

## Testing

- `test_educational_validator.py` — `validate_post` + CLI routing (skip
  papers/explainers, `quality_exempt`, exit codes).
- `test_educational_ci_gate.py` — CI step renders iff `quality.enabled`.
- `test_educational_materialization.py` — the two validator copies are
  byte-identical.
- `test_css_split.py` — global Mermaid theme present without papers; global
  palette override without papers.
- `test_explainers_standalone.py` — Mermaid fence becomes a real
  `<pre class="mermaid">`, themed with `theme:'base'`.
- Backward-compat: `blog-post-create.sh` 8-arg contract preserved
  (`smoke-blog-post.sh`); optional args 9/10 emit `reader_goal`/`diataxis`.
