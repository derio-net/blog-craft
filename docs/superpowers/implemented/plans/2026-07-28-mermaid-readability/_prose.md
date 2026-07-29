# Mermaid readability — implementation plan

Spec: `docs/superpowers/specs/2026-07-28-mermaid-readability-design.md`

## What we are building, in one paragraph

Diagrams currently render at 31% scale because mermaid's `useMaxWidth` shrinks
the SVG to Hextra's 672px content column. Two changes fix it and keep it fixed:
a CSS feature module that renders every diagram at its authored size inside a
framed horizontal scroller, and a blocking CI gate that measures a real render
and fails the build on diagrams too wide to follow by scrolling. No layout or
column-width change — that was prototyped, measured, and rejected.

## Why the phases are ordered this way

Phase 1 (config) is the root because everything else keys off
`features.mermaid_view` and `quality.mermaid_max_width`. Phase 4 (loud disabled
gates) deliberately declares `depends_on: []` — it touches a different file from
everything else and can land in parallel; making it wait on the CSS work would
be false sequencing. Phase 5 (the width gate) needs only the config, not the
stylesheet: the gate measures what mermaid produces, which is independent of how
the page displays it. Phase 6 waits on 5 because a CI step referencing a
non-existent script is worse than no step. Phase 7 is last because its prose
quotes numbers the earlier phases must have made real.

## The one mechanism worth understanding before editing anything

Mermaid writes `style="max-width: <natural>px"` **inline** on each rendered SVG,
where `<natural>` is the diagram's authored width. Inline styles beat stylesheet
rules, and `max-width` always beats `width` regardless of origin. So a stylesheet
rule of `width: 200rem` resolves to `min(200rem, natural)`:

- a 428px diagram stays 428px and never scrolls,
- a 2139px diagram renders full-size inside the scroller,
- nothing is ever enlarged beyond its authored size.

One rule, self-scaling across every diagram in the blog, no per-diagram tuning.
**Do not add a `max-width` to the SVG in this stylesheet** — it would override
the inline value and destroy the whole mechanism. Phase 2's test asserts its
absence for exactly this reason.

It is also why this is CSS rather than JavaScript: `mermaid-init.js:48-61`
re-renders every diagram on the dark/light toggle by resetting `innerHTML`,
which would destroy any JS-attached wrapper or handler. CSS re-applies for free.

## The affordance trap

The scroll affordance is not decoration. Without it the diagram is **silently
truncated**: macOS defaults to overlay scrollbars, which paint nothing at rest,
so a reader sees a diagram that looks complete and never learns the right-hand
third exists.

Two mechanisms are needed and they are **mutually exclusive**, which is the trap:

- `::-webkit-scrollbar { -webkit-appearance: none; height: … }` is the only way
  to opt out of overlay behaviour in Chrome/Safari. Sizing alone does nothing.
- `scrollbar-width` / `scrollbar-color` are the standard properties Firefox
  needs — but when set alongside the WebKit pseudo-elements they **win and
  disable them**, restoring the invisible bar with no error anywhere.

Hence `@supports not selector(::-webkit-scrollbar)` around the standard
properties. The measurement that proves it: `offsetHeight - clientHeight` is
`0` with the naive version and `9px` once `-webkit-appearance: none` is set.

Scroll shadows (`background-attachment: local, local, scroll, scroll`) are the
second cue, and they self-cancel at both ends. Their colour must invert with the
theme — a black shadow is invisible against a `#111` frame.

## The gate measures; it does not guess

A blocking gate built on a heuristic is a gate that gets switched off. The
evidence for that is in this repo's own history: frank sets
`quality.mermaid_syntax: false` because the syntax gate arrived on top of a
50-finding backlog, and the CI step then printed a neutral line and exited 0 —
"a gate nobody runs reports nothing, including how far behind you are."

So Phase 5 renders each diagram for real and reads its width. Two consequences
that are easy to get wrong:

- **jsdom cannot do this.** Probed: no `getBBox`, no `getComputedTextLength`,
  `getBoundingClientRect()` returns `0×0`, and `mermaid.render()` throws
  `CSSStyleSheet is not defined`. Mermaid sizes nodes from text metrics, so
  jsdom widths would be fabricated. Syntax checking on jsdom is fine (frank's
  existing validator); width is not.
- **Extract from built HTML, not markdown.** Diagrams emitted by shortcodes
  (`papers/landscape` quadrantCharts) never appear as fenced blocks, and that is
  precisely where frank's real breakage lived.

Because the gate loads the built site's own mermaid bundle and Node 22 ships a
global `WebSocket`, it needs **no npm dependencies at all** — no `package.json`,
no `npm install`, no supply-chain surface added to any consumer blog. The
ubuntu-24.04 runner ships Chrome 150 and Node 22.23.1 preinstalled, but defines
no `CHROME_BIN`, so the browser is discovered through a candidate list.

## Two defaults that are asymmetric — read this before Phase 3

`features.mermaid_view` is **default true**. The renderer's `--get-bool` returns
`false` for an absent key, so a blog that has not yet run the migration would
silently lose the fix if the bootstrap block were copied verbatim from
`[3g]`. Phase 3 handles absent-means-true explicitly and tests it.

Likewise the migration uses setdefault semantics: a blog that has deliberately
set `features.mermaid_view: false` must **keep** false. A migration that
re-enables an operator's opt-out is a bug, and Phase 1 tests for it.

## Landing red is the point

The width gate ships blocking with **no baseline**, by explicit operator
decision, to force a focused effort on the backlog. Against frank, a 1400px
budget blocks 35 of 182 diagrams on day one. That is intended, and the CHANGELOG
says so plainly so an adopting blog is not surprised.

The budget is derived, not guessed: ~2× the 672px content column, on the
reasoning that a diagram needing more than two column-widths of scrolling cannot
be held in the reader's head. Day-one impact at alternatives — 1200px → 46
blocked, 1600px → 20, 1800px → 9 — is recorded in the spec so the number can be
argued with rather than merely obeyed.

## What this plan does not do

Nothing in it touches a consumer blog's content. frank's 50-finding
`mermaid_syntax` backlog and the flip of that flag are separate content work,
explicitly out of scope. The two manual acceptance rows (MMD-2 visible scroll
affordance, MMD-6 keyboard scrolling) are browser-observable and stay
`not-implemented` until the post-merge Test Plan verifies them.
