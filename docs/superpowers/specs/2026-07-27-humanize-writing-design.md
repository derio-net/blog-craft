# Humanize the writing pipeline — reader-arc discipline, AI-tells catalog, cold-reader editor

**Date:** 2026-07-27 · **Branch:** `feat/humanize-writing` · **Status:** approved design

## Problem

Posts produced by `/blog-post` and `/post-rewrite` pass the educational-writing
gate and still read as recognizably machine-written. The operator's diagnosis,
confirmed against the live corpus (frank `building/36-metrics-api` vs its
`operating/29-metrics-api` companion): the failure is **structural, not just
lexical**.

1. **Session-skeleton posts.** A building chronicle's outline mirrors the
   session's timeline (the fork faced → the flag set → the proof run → the
   detour hit → the lesson). Sections are events in the work's chronology, not
   stops in a reader's arc. The post is narrow: no broad-picture landscape, no
   thought given to what a reader keeps beyond this cluster/repo.
2. **Under-sized beginnings.** When the meat is deeply technical or
   idiosyncratic, the beginning must grow — the current methodology actively
   caps it (§2a "three beats, tight, no lecturing") and treats
   explanation-before-steps as a failure signature, so the conceptual landscape
   a human expert would open with never gets written.
3. **Surface tells.** AI vocabulary, rule-of-three, negative parallelisms,
   em-dash overuse, cliché conclusions. No prose instruction or mechanical
   check currently addresses them.

Root cause of (1): the drafting context *lived* the session. The chronology
feels self-evidently important from inside, and single-pass drafting means the
same context writes and judges the draft. Instructions alone decay under that
gravity — the current methodology already forbids session narrative, and the
posts passed anyway.

## Decision (operator-approved)

Approach **A+B**: strengthen the methodology (A) *and* add a blind cold-reader
editor pass (B). The outline-first inversion (drafting the landscape before
consulting the evidence brief) was considered and **not** adopted.

Constraints fixed during brainstorm:

- **Steps-first survives.** The 2am reader outranks the learning reader. The
  bigger beginning is mode-conditional; operating how-to/reference posts keep
  the tight three-beat orientation unchanged.
- **The tells catalog is vendored**, not referenced from a user-level skill —
  blog-craft ships to multiple blogs and runs under OpenCode; an install-local
  dependency would be silently absent elsewhere.
- **Lint is warnings-first.** Only egregious cases (AI-vocabulary hits) fail
  the gate; density metrics warn. Prose must not be written to a regex.

## Design

### 1. `skills/educational-writing/references/reader-arc.md` (new)

The organizing rule:

> A post is organized around the **reader's arc** — beginning, middle, end —
> never the session's chronology. The chronology is raw material; the arc is
> the outline.

- **Beginning — the lay of the land.** The conceptual landscape from general
  knowledge: the problem space, its standard shapes and names, where the
  post's topic sits. Sized **proportionally to how idiosyncratic/deep the meat
  is**. Mode-conditional: building/tutorial/explanation posts carry a real,
  labelled landscape section; operating how-to/reference posts keep the
  existing three-beat orientation (steps-first absolute).
- **Middle — the meat.** Evidence discipline unchanged (§2). Steps lead within
  their sections. Decisions are presented as the space of options a reader
  would face, with the session's choice as the worked instance — not as a
  timeline event.
- **End — what transfers.** A closing section stating what the reader keeps
  beyond this repo: the general rule, the portable decision heuristic, the
  gotcha that generalizes. Explicitly not a recap of what was done.

Amendments to existing prose:

- `SKILL.md` §2a gains the mode-conditional carve-out (landscape replaces the
  three-beat cap for building/tutorial/explanation posts).
- `SKILL.md` §4 failure signatures gain **"Session-skeleton"**: headings that
  are events in the work's timeline rather than stops in the reader's arc.
- `references/checklist.md` gains judgment items for landscape presence/size
  and a what-transfers ending.

### 2. `skills/educational-writing/references/ai-tells.md` (new, vendored)

The humanizer pattern catalog adapted for technical blog prose. Credited to
@blader's humanizer skill and Wikipedia's WikiProject AI Cleanup ("Signs of AI
writing"). Patterns: AI vocabulary, rule-of-three, negative parallelisms
("not X, but Y"), em-dash overuse, inflated symbolism, promotional language,
superficial "-ing" analyses, vague attributions, conjunctive-phrase excess,
cliché conclusions.

Dual use, single source: the drafting skills apply it as a mandatory
self-revision instruction; the validator's lint word/pattern lists derive from
this file so prose and mechanics cannot drift apart.

### 3. `agents/cold-reader.md` (new agent)

A blind editor, sibling of `post-researcher.md` (same shipping mechanism to
consumer harnesses). Read-only tools (Read, Grep, Glob). The dispatch prompt
passes **only** the draft path and the methodology reference paths — never the
session context, the evidence brief, or the source repo. The blindness is the
design: it cannot find the session's chronology meaningful because it never
saw the session.

Structured critique, five parts:

1. **Takeaway mirror** — what it understood and would retain, in its own
   words; the drafter diffs this against the intended `reader_goal`.
2. **Lost points** — where it needed context the post assumes but never gives.
3. **Session residue** — passages only meaningful to someone who was there.
4. **Arc assessment** — beginning sized to the meat's idiosyncrasy; ending
   transfers vs recaps.
5. **AI-tell instances** — concrete hits against `ai-tells.md`.

### 4. Pipeline wiring

- **`/blog-post` Step 4** gains a sub-step: compose → dispatch cold-reader →
  revise against the critique → then show the draft to the operator, with a
  one-paragraph summary of what the critique changed. The existing `regen`
  loop re-dispatches naturally. One critique round by default.
- **`/post-rewrite`** gets the identical sub-step after its re-shape.
- Both skills load `reader-arc.md` and `ai-tells.md` alongside the existing
  references.

### 5. Validator lint layer (`tools/validate_educational.py`)

New lint checks, run with the existing gate, warnings-first:

| Check | Default severity |
|---|---|
| AI-vocabulary hits (word list from `ai-tells.md`) | fail |
| Em-dash density above threshold (per 1000 words) | warn |
| Negative-parallelism / rule-of-three density | warn |
| Cliché conclusion openers | warn |
| Missing what-transfers-style closing section on building/tutorial posts | warn |

Warnings print with counts and line numbers, exit 0. Existing hard-gate items
untouched. Thresholds and per-check severity live in a new **`quality.lint`**
block in `.blog-craft.yaml`, seeded via the existing `seed_config.py` pattern
(defaults + explanatory comment) so consumer blogs adopt it without manual
edits.

## Testing

### Test Plan

- **Unit (lint):** each lint check exercised against two new fixtures — one
  clean post, one deliberately tell-laden — through the existing `tests/`
  harness. Severity config honored (fail vs warn), thresholds read from
  `quality.lint`, exit codes correct.
- **Unit (config seeding):** `quality.lint` seeded when absent; untouched when
  present.
- **Integration (skill contract):** `agents/cold-reader.md` exists, declares
  read-only tools, and both drafting skills' SKILL.md reference the dispatch
  sub-step and the two new reference files (grep-level checks, same style as
  existing skill-contract tests).
- **Manual/acceptance:** a real `/blog-post` run on a consumer blog produces a
  draft whose critique round ran, whose building-post beginning carries a
  landscape section, and whose lint output is clean. Prose quality itself is
  operator judgment; the matrix rows pin the mechanical envelope around it.

## Out of scope

- Batch retrofit of frank's back catalog (~30 posts) — an operator-initiated
  `/post-rewrite` campaign after this ships.
- Custom per-blog voice fingerprinting from operator writing samples.
- The outline-first inversion (blind teach-first outline, evidence merged
  after) — rejected this round; revisit only if A+B proves insufficient.
