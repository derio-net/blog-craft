# Abbreviation glossary — design

**Status:** design
**Date:** 2026-07-26
**Branch:** `feat/abbreviation-glossary`
**Journal:** `docs/superpowers/journals/specs/2026-07-26-abbreviation-glossary.md`

## Problem

A teaching blog leans on abbreviations — NUT, SLO, CDP, OKLCH, CRD — because
spelling each one out every time would wreck the prose. The cost lands on the
reader who does not already know the term: they leave the page to search, or
they guess. Neither is what a teaching blog is for.

blog-craft has no mechanism for this today. An author either expands the term
inline (noisy, and only helps the first reader to arrive at that paragraph) or
leaves it bare.

## Goal

An opt-in `glossary` feature that lets an author scan one post, one series, or a
whole blog, curate a registry of abbreviations, and have each marked occurrence
render as a clickable element that opens the proper name and a one-or-two
sentence description — without leaving the page.

**Reader-facing acceptance:** a reader who does not know "NUT" clicks it in the
running prose and sees "Network UPS Tools — daemon suite that monitors a UPS and
triggers a clean shutdown before the battery dies", then dismisses it and keeps
reading. On a phone, with a keyboard, and with a screen reader.

## Non-goals

- Translating or localising definitions.
- Auto-generating definitions from an external source (Wikipedia, an LLM with
  web access). Definitions are authored, grounded in the post that uses the term.
- Retro-fitting the three consumer blogs (frank, gondor-blog, stoa-blog). They
  adopt this through `/update` after release, matching the v0.10.0 rollout.
- A per-post glossary. The registry is blog-wide by design — a series that
  explains NUT in post 3 should not redefine it in post 7.

## Decisions

Recorded in the spec journal (`fr journal render --scope spec --slug
2026-07-26-abbreviation-glossary`). Summarised:

| # | Decision | Why |
|---|----------|-----|
| d1 | **Authored shortcode**, not runtime DOM annotation | Deterministic rendered HTML, reviewable in the diff, verifiable in CI. A teaching blog cannot ship false-positive matches inside prose. |
| d2 | **Native HTML Popover API**, zero JavaScript | Click/tap, Esc, click-away, keyboard focus and top-layer positioning are all native. No JS asset, no hand-written focus management, no mobile hover special-case. |
| d3 | **Acronyms/initialisms only** are auto-proposed; manual adds render identically | Lowercase tool names (systemd, kubectl) would flood the proposal list. The registry stays open for hand-added terms. |
| d4 | **`{{< glossary-index >}}` shortcode only**, no auto-created page | Bootstrap writing a `content/glossary/_index.md` would put operator-class content on disk that `/update` can never manage. |
| d5 | **CSS anchor positioning**, one anchor name per trigger, derived from the panel id and set inline (#49) | The Popover API places nothing; without an anchor the panel lands in the viewport corner. A shared anchor name would collapse every panel onto one trigger, and a stylesheet cannot address a single shortcode instance — so the name is per-pair and inline. See §5a. |
| d6 | **Bottom-centred dock** where anchor positioning is unsupported (#49) | Anchor positioning is not yet universal. The fallback must still be usable and must not cover the heading; a bottom sheet is the conventional shape and is thumb-reachable on a phone. The corner is never an acceptable outcome. |

## Architecture

Six pieces, each independently testable.

```
   .blog-craft.yaml                    data/glossary.yaml
   features.glossary.enabled           (content class — operator-owned,
        │                               never overwritten by /update)
        │                                        │
        ▼                                        ▼
   tools/bootstrap-render.sh  ──renders──▶  layouts/shortcodes/abbr.html
   [3f] gated block                        layouts/shortcodes/glossary-index.html
        │                                  assets/css/glossary.css
        │                                        │
        │                                        ▼
        │                              partials/custom/head-end.html
        │                              (loads glossary.css if materialized)
        ▼
   /glossary skill ──▶ tools/glossary_scan.py   (candidates, deterministic)
                   ──▶ [author writes definitions]
                   ──▶ tools/glossary_apply.py  (insert markers, deterministic)
                   ──▶ tools/validate_glossary.py (CI gate + scripts/ mirror)
```

### 1. Config surface — `features.glossary`

```yaml
features:
  glossary:
    enabled: true
    first_occurrence_only: true   # optional, default true
```

`features` is passed through `.blog-craft.yaml.tmpl` wholesale via
`{{ toYaml .features | indent 2 }}`, so **no config-schema version bump and no
migration are needed** — v5 stays v5.

`tools/validate_config.py` gains a small shape check (the `features` block is
unvalidated today): when `features.glossary` is present it must be a mapping,
`enabled` and `first_occurrence_only` must be booleans. Without this a typo
(`enable: true`) silently disables the whole feature with no signal.

`first_occurrence_only` is an *authoring* knob — it governs where
`glossary_apply.py` inserts markers, not how they render. `false` marks every
occurrence in a post.

### 2. The registry — `data/glossary.yaml`

```yaml
NUT:
  name: Network UPS Tools
  description: >-
    Daemon suite that monitors a UPS over USB or the network and triggers a
    clean shutdown before the battery dies.
  url: https://networkupstools.org      # optional
SLO:
  name: Service Level Objective
  description: >-
    The numeric reliability target a service commits to — the line an error
    budget is measured against.
```

- Keyed by the literal token as it appears in prose. Case-sensitive.
- `name` and `description` are required; `url` is optional and renders as a
  "Read more" link inside the panel.
- Lives under `data/` so Hugo exposes it as `site.Data.glossary` with no build
  step. Classified **`content`** by `templates/manifest.yaml` (`data/**`), so
  `/update` never touches an operator's curated definitions.
- Sorted alphabetically by key when written by the skill. Hand-edits are free
  to be unsorted; the validator warns, never fails, on ordering.

### 3. `{{< abbr >}}` shortcode

```
I wired {{< abbr "NUT" >}} into the rack.
The {{< abbr "SLO" "SLOs" >}} we agreed on were generous.
```

- Positional arg 0 is the **registry key**. An optional second **positional**
  arg overrides the displayed string — this is how plurals and possessives work
  (`SLOs` displays, `SLO` looks up) without polluting the registry with
  inflected forms. *(Implementation correction: this was specified as a named
  `text=` parameter. Hugo refuses to mix positional and named parameters in one
  shortcode call, and making the common case `{{< abbr term="NUT" >}}` was the
  worse trade — see the plan journal, `p5-hugo-named-params`.)*
- Missing registry key → `errorf`, which **fails the Hugo build**. A dangling
  term is a broken promise to the reader; the validator catches it earlier, and
  the build is the backstop.

Rendered markup:

```html
<button type="button" class="abbr-trigger" popovertarget="abbr-nut-3"
        aria-label="Expand abbreviation: NUT">
  <abbr title="Network UPS Tools">NUT</abbr>
</button>
<span popover id="abbr-nut-3" class="abbr-panel">
  <strong class="abbr-name">Network UPS Tools</strong>
  <span class="abbr-desc">Daemon suite that monitors a UPS …</span>
  <a class="abbr-link" href="https://networkupstools.org">Read more</a>
</span>
```

- The id is `abbr-{{ anchorize $key }}-{{ .Ordinal }}` — `.Ordinal` is the
  shortcode's position on the page, so the same term marked twice still yields
  unique ids.
- The inner `<abbr title>` is deliberate: it carries the expansion for screen
  readers and gives a native hover tooltip, so the element still communicates
  something in the (baseline-supported, but not universal) case where the
  Popover API is unavailable.
- No JavaScript. `popovertarget` + `popover` handle open, Esc, click-away,
  focus and top-layer stacking natively.

### 4. `{{< glossary-index >}}` shortcode

Renders the whole registry as an alphabetical `<dl>`: term, proper name,
description, optional link. Emits nothing (not an error) when the registry is
absent or empty, so dropping it on a page before curating anything is safe. The
operator creates the page; blog-craft does not.

### 5. Styling — `assets/css/glossary.css`

Ships **only when the feature is enabled**, from
`templates/features/glossary/assets/css/glossary.css`, and is loaded from
`layouts/partials/custom/head-end.html` with the same defensive idiom
read-tracker already uses:

```go-html-template
{{- with resources.Get "css/glossary.css" }}
<link rel="stylesheet" href="{{ (. | minify | fingerprint).RelPermalink }}">
{{- end }}
```

A blog that never opted in materializes no file and emits no `<link>`.

The link is emitted **before** the `custom.css` link, so a blog's own
`custom.css` can override feature styling at equal specificity.

Visual contract: the trigger is inline, inherits the surrounding font, and is
marked with a dotted underline (never a full button chrome — it sits mid-sentence).
The panel is a small card with the blog's existing surface/border tokens, themed
for dark mode through the `:is(html.dark)` selector already used by
`.read-marker` in `custom.css`.

#### 5a. Placement contract (#49)

**A `[popover]` is not positioned for you.** The top layer decides *stacking*,
not *coordinates*: with no author positioning the UA default (`inset: 0` plus
`margin: auto` semantics) lands the panel in the viewport's block-start /
inline-start corner, hundreds of pixels from the term and on top of the page
`<h1>`. §3's "top-layer positioning" was read as a placement guarantee and never
specified *where* the panel goes; that omission is the whole of #49.

The contract, now explicit:

> **The panel opens adjacent to the abbreviation it defines** — below it by
> preference, above it when there is no room below — and never covers the page
> heading.

Delivered by **CSS anchor positioning**, one anchor per trigger:

- The shortcode already computes a unique panel id, `abbr-<anchorized key>-<ordinal>`.
  The **anchor name is derived from that same id**: `--abbr-<anchorized key>-<ordinal>`,
  emitted as an inline `style` on the trigger (`anchor-name`) and on the panel
  (`position-anchor`). A single shared name would anchor every panel on the page
  to whichever trigger the browser resolved first, so the name must be per-pair.
  Inline `style` is the only surface available — a stylesheet cannot address one
  shortcode instance, and both properties are dropped harmlessly by browsers
  that do not support them.
- The anchored rules live under `@supports (anchor-name: --x)` and set
  `position-area: block-end span-inline-end` with
  `position-try-fallbacks: block-start span-inline-end, block-end span-inline-start`,
  so the panel flips above the term near the viewport foot and flips its inline
  side near the viewport edge.
- **Non-supporting browsers get a bottom-centred dock**, not the UA corner:
  `position: fixed` pinned to the viewport's block end, inline-centred, width
  clamped to the viewport. It is not adjacent to the term, but it is the
  conventional "definition sheet" placement, it is reachable on a phone, and —
  the point — it does not cover the heading. The corner is the one placement
  that must never be the outcome of any path.

Two constraints the CSS must respect explicitly: `.abbr-trigger` sets
`all: unset`, so the inline `anchor-name` is what survives; and the UA
`[popover]` sheet supplies `inset: 0` / `margin: auto`, which the anchored rule
must reset (`inset: auto`, an explicit `margin`) or the panel stretches to fill
its position area.

**No manifest change.** `templates/manifest.yaml` already classifies
`assets/css/**` as `merged`, which is the correct treatment: on first `/update`
after enabling the feature the file does not exist locally, so `plan_update`
emits `add`; on later updates it is 3-way merged, so a blog that tweaked the
panel colours keeps its tweak. This mirrors how `read-tracker.js` — also shipped
from `templates/features/` — is covered by the existing `assets/js/**` rule.
Narrowing the glob to give the file `framework` treatment was considered and
rejected: it would change `/update` behaviour for every existing blog's
operator-authored CSS to buy nothing this feature needs.

### 6. The `/glossary` skill

`skills/glossary/SKILL.md`, user-invocable, mirrored to OpenCode as
`blog-craft-glossary` by `scripts/sync-opencode.py`.

**Discovery contract** (identical to `/media`): walk up from CWD for
`.blog-craft.yaml`; refuse if absent. If `features.glossary.enabled` is not
true, offer to set it and stop.

**Target resolution** from the single optional argument:

| Argument | Scope |
|---|---|
| *(none)* | every post in the blog |
| `<series-key>` | every post in that series |
| `<series>/<NN>-<slug>` | one post |

**Procedure:**

1. `tools/glossary_scan.py --config … <paths…>` → JSON of candidate tokens with
   the sentence each was found in and its file:line. Deterministic, tested, no
   LLM.
2. The skill writes `name` + `description` for each candidate, grounded in the
   post context the scanner returned. Candidates it cannot expand with
   confidence are dropped, not guessed — a wrong expansion is worse than none.
3. The proposed additions are shown to the operator as a diff of
   `data/glossary.yaml` before writing. Existing entries are never rewritten
   without being called out.
4. `tools/glossary_apply.py --config … <paths…>` inserts the markers.
5. The skill reports what it marked and reminds the operator to run the
   validator / a local `hugo` build.

**Why the split.** Candidate extraction and marker insertion are pure text
transformations with exact expected outputs — they belong in tested Python, not
in prose instructions an agent re-improvises each run. Only the definition
writing genuinely needs a model. This is the same division `/media` already
uses with `tools/media-fill.py`.

#### `tools/glossary_scan.py`

Candidate = a token of **2–10 characters, all uppercase letters or digits,
beginning with a letter**, optionally carrying a lowercase inflection (`SLOs`,
`SLO's`) that is recorded as the *display* form while the bare token is the
registry key. A candidate must survive every exclusion:

- inside a fenced code block, an indented code block, or inline `` `code` ``
- inside YAML frontmatter
- inside a URL, a link target, or an image path
- inside an existing `{{< … >}}` shortcode or an HTML tag
- inside a heading line (`#`-prefixed)
- already marked with `{{< abbr … >}}` anywhere in the file
- already present in `data/glossary.yaml` **and** already marked in this file
- present in a shipped stoplist of capitalized tokens that are never technical
  abbreviations worth defining (`OK`, `TODO`, `FIXME`, `NOTE`, `WARNING`,
  `AM`, `PM`, `USD`, `EUR`, …)

Output is JSON so the skill consumes it without re-parsing prose:
`[{term, display, file, line, sentence, occurrences}]`.

#### `tools/glossary_apply.py`

Inserts `{{< abbr "KEY" >}}` (or `{{< abbr "KEY" text="KEYs" >}}` for an
inflected display form) at the first occurrence per file — or every occurrence
when `first_occurrence_only: false`.

- Honours every exclusion above: never rewrites inside code, frontmatter,
  headings, link text, URLs, or an existing shortcode.
- **Idempotent.** Running it twice changes nothing; a term already marked is
  skipped.
- Only writes files it actually changed, and reports each edit as `file:line`.

#### `tools/validate_glossary.py`

CI gate. Mirrored byte-identically to
`templates/hugo-hextra/scripts/validate_glossary.py` and enrolled in
`tests/unit/test_mirrors.py`, per the convention `validate_educational.py`
and the papers validators already follow, so a blog's plain-python CI runs it
without the plugin installed. **`glossary_scan.py` is mirrored alongside it** —
the validator imports its marker and code-span helpers rather than re-deriving
them, and a materialized blog has no plugin on `sys.path`
(see the plan journal, `p4-two-mirrors`).

| Check | Severity |
|---|---|
| every `{{< abbr "X" >}}` in content has a registry entry | **error** |
| every registry entry has non-empty `name` and `description` | **error** |
| `url`, when present, is an absolute http(s) URL | **error** |
| duplicate registry keys differing only in case | **error** |
| a registry entry no post references | warning |
| registry not alphabetically sorted | warning |

Wired into `templates/hugo-hextra/.github/workflows/blog-ci.yml.tmpl` behind
`{{- with .features }}{{- with .glossary }}{{- if .enabled }}`, mirroring the
papers and quality-gate steps.

### Bootstrap and update paths

**Bootstrap.** `tools/bootstrap-render.sh` gains a `[3f] glossary` block after
the analytics block, gated on `features.glossary.enabled` via the renderer's
`--get-bool`, rendering `templates/features/glossary/` into the target. The
`/bootstrap-blog` wizard gains one question ("Mark technical abbreviations with
click-to-expand definitions?", default no).

**Update.** An existing blog opts in by setting `features.glossary.enabled: true`
and running `/update`: the shortcodes (`layouts/**`) and `glossary.css` are
`framework`-class, so they are added; `data/glossary.yaml` does not exist yet
and is `content`-class, so the operator creates it by running `/glossary`. No
migration, no schema bump.

## Testing

Unit tests, following existing patterns:

- `test_glossary_gating.py` — the shortcodes and CSS materialize iff
  `features.glossary.enabled` is true (mirrors `test_features_gating.py`,
  bootstrapping a fixture config both ways).
- `test_glossary_scan.py` — candidates found; every exclusion honoured
  (fences, inline code, frontmatter, URLs, headings, existing markers,
  stoplist); plural detection.
- `test_glossary_apply.py` — first-occurrence-only vs all; idempotence; no
  rewrite inside excluded regions; unchanged files untouched.
- `test_glossary_validator.py` — each error and warning row above.
- `test_glossary_hugo.py` — a real `hugo` build of a bootstrapped fixture blog
  emits the button/popover pair, unique ids for a twice-marked term, the
  positional display override, the index shortcode, and fails on an unknown key
  (mirrors `test_papers_hugo.py` / `test_explainers_hugo.py`).
- `test_mirrors.py` — extended with the `validate_glossary.py` pair.
- `test_config_schema.py` — `features.glossary` shape validation.
- `test_opencode_sync.py` / `--check` in CI — the `blog-craft-glossary` mirror
  exists and matches.

## Docs

- `docs/CONFIG.md` §9 — `features.glossary`, the registry format, both
  shortcodes, the CI gate.
- `README.md` — `/glossary` in the skill list.
- `docs/ARCHITECTURE.md` — the scan/author/apply split and why only the middle
  step needs a model.
- `docs/USING-ON-A-HOST.md` — enabling the feature on an existing blog.
- `CHANGELOG.md` — under `[Unreleased]`, with a minor version bump
  (`0.12.0` → `0.13.0`; new feature, backward compatible).

`/glossary` is blog-craft's **tenth** skill. Acceptance rows `OC-1` and `OC-2`
currently assert "all **9** blog-craft skills" and would go stale the moment
this merges; the same PR restates them count-free ("every blog-craft skill"), so
the next skill added does not silently falsify them.

## Test Plan

Post-merge, operator-driven. Verifies the reader-facing acceptance that unit
tests cannot: that the thing is actually clickable and readable.

1. **Bootstrap a throwaway blog with the feature on.** In a temp dir, run
   `/bootstrap-blog` answering yes to the abbreviations question. Confirm
   `layouts/shortcodes/abbr.html`, `layouts/shortcodes/glossary-index.html` and
   `assets/css/glossary.css` exist, and that a blog bootstrapped with the answer
   *no* has none of them.
2. **Scan and mark.** Write (or paste) a post using NUT, SLO and CDP, including
   at least one occurrence inside a fenced code block and one in a heading. Run
   `/glossary <series>/<post>`. Confirm the proposed definitions are sensible,
   the code-block and heading occurrences were left alone, and only the first
   prose occurrence of each term was marked.
3. **Render and click.** `bash scripts/hugo-serve.sh`, open the post, and click
   a marked abbreviation. Confirm the panel opens with the proper name and
   description, Esc closes it, clicking outside closes it, and Tab reaches the
   trigger and Enter opens it.
3a. **Placement (#49).** With the panel open, confirm it sits **adjacent to the
   term** — directly below it, left edge near the term's — and that it covers no
   part of the page `<h1>` or the sidebar. Click a term in the *last* line of the
   post and confirm the panel flips **above** it rather than running off the
   viewport foot; click one near the right edge and confirm it flips its inline
   side. Then click two different terms in turn and confirm each panel anchors to
   **its own** trigger, not to the first one on the page. In a browser without
   CSS anchor positioning (or with it disabled), confirm the panel docks
   bottom-centred and readable — never in the top-left corner.
4. **Phone and dark mode.** Load the same page on a phone (or a narrow
   viewport), tap the abbreviation, confirm the panel is readable and
   dismissible. Toggle dark mode and confirm the panel is legible in both.
5. **Index page.** Create a page containing `{{< glossary-index >}}`, confirm
   every registered term appears alphabetically with its description.
6. **CI gate bites.** Add `{{< abbr "XYZ" >}}` for a term not in the registry;
   confirm `python3 scripts/validate_glossary.py` fails and `hugo` fails.
   Remove it and confirm both pass.
7. **Idempotence.** Re-run `/glossary` on the same post; confirm no file changes.
8. **Update path against a real blog's config.** In a **scratch clone** of
   frank's blog (or gondor-blog) — adopting the feature for real is explicitly
   out of scope — set `features.glossary.enabled: true`, run `/update`, and
   confirm the shortcodes and CSS arrive as `add` actions with no conflicts and
   no unrelated diff. Discard the clone.

## Implementation Plans

| Plan | Repo | File | Depends on |
|---|---|---|---|
| 2026-07-26-abbreviation-glossary | `derio-net/blog-craft` | `2026-07-26-abbreviation-glossary` | — |
| 2026-07-26-glossary-panel-placement | `derio-net/blog-craft` | `2026-07-26-glossary-panel-placement` | — |
