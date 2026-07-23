---
name: blog-craft-educational-writing
description: The methodology blog-craft uses to write genuinely educational teaching posts — reader-first structure (Diátaxis), evidence-grounding, and a thin-persona rule that keeps the character from crowding out the substance. Loaded by /blog-post and /post-rewrite; invoke directly ("apply the educational-writing methodology", "is this post actually useful?") to diagnose or shape a post. Not a scaffolder — it is the shared brain those skills consume.
user-invocable: true
disable-model-invocation: false
---

# Educational writing — the methodology

This is the standard blog-craft holds every teaching post to. It exists because
the easy failure mode of an AI-drafted post is **prose about the session that
generated it** — witty, in-character, "you had to be there" — which reads fine
and teaches nothing. A reader did not come for the story of how you built it.
They came to build it, operate it, or fix it.

The `/blog-post` and `/post-rewrite` skills load this file. You can also invoke
it directly to diagnose a post or shape a draft.

## The one test

> **A reader lands on this post at 2am with 10 minutes to fix something that is
> actively breaking. Does the post give them what they need, fast?**

If the honest answer is "they'd have to read a narrative and infer the commands,"
the post has failed regardless of how good the prose is. This is the bar. The
graceful-shutdown post whose reader's UPS is draining *right now* is the archetype.

## 1. Pick the mode before you write (Diátaxis)

Most useless technical posts are useless because they blend four incompatible
jobs into one voice. [Diátaxis](https://diataxis.fr/) names them: **tutorial,
how-to guide, reference, explanation**. A post should commit to one primary
mode (a second is fine if clearly sectioned) and be honest about which.

The compass — ask two questions:

| | **Action** (practical steps) | **Cognition** (knowledge) |
|---|---|---|
| **Acquisition** (learning/study) | **Tutorial** — teach a beginner by doing | **Explanation** — the *why*, the design, the tradeoffs |
| **Application** (working/doing) | **How-to guide** — a competent reader's goal, achieved | **Reference** — facts to look up: flags, values, paths |

Full compass, per-mode quality tests, and the failure signatures are in
`references/diataxis.md`. **Read it before drafting.** The single most common
fix is: *a post written as narrative-explanation should have been a how-to guide
plus a reference block.* That was the graceful-shutdown mistake exactly.

## 2. Ground every claim in evidence

No claim without a citable artifact. "It shuts down gracefully" is worthless;
`upsmon` config lines, the `systemctl` output, the log line at the moment of
cutover, and the runbook step are worth everything. Evidence a post can carry:

- **Real commands and their real output** in fenced blocks — copy-pasteable, not paraphrased.
- **`file:line` references** and **commit SHAs** into the source repo.
- **Test names** that prove the behaviour, and how to run them.
- **Config values** with the file they live in and why that value.
- **An incident/failure timeline** with timestamps when the post chronicles one.
- **Screenshots / asciinema** (via `/media`) only where a picture genuinely advances understanding.

How to *gather* this evidence — and the `post-researcher` subagent that does it
from a source repo so heavy exploration stays out of the drafting context — is in
`references/evidence.md`.

## 2a. Orient the reader before the first step

A how-to that opens on `Step 1` leaves the reader lost: *why am I building this,
what does it solve, why this shape?* Every post earns its steps with a short
**set-the-stage** opening — three beats, tight, no lecturing:

1. **Motivation** — the concrete problem. Not "we added observability" but "I
   wanted to know how many people read Paper 15 this week, and the answer was a
   shrug." A reader should feel the itch.
2. **What it solves** — what's true after, that wasn't before.
3. **Why this shape** — the one load-bearing design choice, stated in a sentence
   (the deep rationale goes in the labelled Explanation section later; here it's
   just orientation).

Then **name the foundation the reader builds on.** They almost certainly won't
build your exact thing — so give them the ground to stand on: "To follow this you
need A, B, and C. Given all that, here's what we did." Where A/B/C were built in
earlier posts, **link them** rather than re-explaining — a redirect orients
without bloating. This turns a copy-this-exactly recipe into a foundation others
can build their own thing on.

## Config seeding pattern

Before using any optional `.blog-craft.yaml` key, ensure it exists in the blog's
config. If missing, seed it with its default value and an explanatory comment:

```
python3 <plugin_root>/tools/seed_config.py --config <blog_root>/.blog-craft.yaml \
    --key <key> --default <value> \
    --comment "<description>" --values "<comma-separated options>"
```

This pattern applies to every optional parameter — add new ones the same way.

## 3. Persona is a thin frame — but how thick is a dial

The persona frames; it never carries the teaching. **How much** it frames is
configurable via `voice_level` (`dry` / `balanced` / `rich`, default `balanced`)
— see `references/voice.md`. **Seed it if missing**:

```
python3 <plugin_root>/tools/seed_config.py --config <blog_root>/.blog-craft.yaml \
    --key voice_level --default balanced \
    --comment "How thick the persona frame is." \
    --values "dry,balanced,rich"
```

The dial changes orientation warmth, aside frequency, and how the *why* is
voiced; it never changes the evidence, the mode discipline, or the gate.

blog-craft blogs have a beloved persona and cover art. Keep them — but the
persona is a **thin frame**: a short in-character intro that sets the stakes, an
outro, and the occasional aside that *aids memory* (a named metaphor a reader
will recall at 2am). The body between them is evidence-grounded teaching. The
rule:

> Wit is allowed only where it makes the material easier to remember or apply.
> Wit that substitutes for substance, or that only lands if "you were there,"
> gets cut.

If you deleted every in-character sentence and the post still taught the reader
how to build/operate/fix the thing, the frame is thin enough. If deleting them
leaves holes, the persona was carrying load it shouldn't.

## 4. The failure signatures — cut these on sight

- **Session narrative.** "We then tried… turns out… eventually it worked." The reader doesn't need your path; they need theirs.
- **In-jokes / "you had to be there."** Zero value to someone who wasn't.
- **Explanation crowding out how-to.** Pages of *why* before a single runnable step. Lead with the steps; move the *why* into a clearly-labelled Explanation section (or a companion post).
- **Assertions without artifacts.** "It's fast / safe / graceful" with nothing to run or verify.
- **No recovery path.** An operational post with no "when it breaks, do this."
- **Buried commands.** The one command that matters, hidden mid-paragraph instead of in a copy-pasteable block.
- **Drafting-artifact meta-commentary.** "NOT the-key-I-first-invented", "the spec hallucinated this", corrections aimed at the model's own path to the answer. State the correct thing; a reader doesn't need the draft's wrong turns. (A *real engineering* misstep during the build — a human design decision that was wrong and taught something — is different: it goes in the missteps table with its context. The test: was it a wrong turn in *building the system*, or in *writing the post*? Only the first is worth keeping.)

## Diagrams: prefer Mermaid over hand-drawn ASCII

Use fenced ` ```mermaid ` diagrams, not hand-drawn ASCII boxes. Mermaid renders
natively in Hextra and in the standalone explainer renderer, is themed by
blog-craft's shipped default (and any `features.css.mermaid_palette` rebrand), and
stays aligned at any width. ASCII boxes drift out of alignment across fonts and
zoom, carry no theming, and are painful to edit. Reserve a code block for a
diagram only when it's genuinely not a graph (a directory tree, a byte layout).

**Keep the layout clean.** Mermaid's default engine (dagre) routes badly when a
diagram does too much — a long edge details *under* an unrelated box, an edge
label gets crushed against a cluster boundary. Fixes, in order of leverage:

- **Split a busy diagram.** The strongest fix. If one diagram has many
  long-range or crossing edges (e.g. a data plane *and* an alert plane), it's two
  diagrams. Each should make one point.
- **Order nodes and edges to flow one way.** Declare nodes in the order the flow
  visits them and write edges front-to-back; every back-edge is a crossing dagre
  has to route around. Chain where you can (`a --> b --> c`).
- **Keep edge labels short** (`logs`, `crit`) or drop them when the direction is
  obvious — long labels near a subgraph border are what gets cramped. Put a
  far-right sink (e.g. a `Telegram` node) *outside* the subgraphs.
- **Match direction to shape** — `TD` for tiers/pipelines, `LR` for a left-to-right
  flow; try both, keep the one that crosses less.
- **ELK for the hard ones** — if the blog's Mermaid bundle ships the ELK layout,
  `%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%` routes orthogonally and
  places labels far better. Confirm it renders in the target theme before relying
  on it (Hextra's bundled Mermaid may not include ELK).

If a diagram still looks tangled after this, that's the diagram telling you it's
carrying too much — split it.

## 5. The gate

Before publish, a `posts` post must pass the structural gate — the mechanical
floor under the methodology (it can't judge prose, only presence of evidence):

```bash
python <blog-craft>/tools/validate_educational.py --config .blog-craft.yaml \
    content/docs/<series>/<NN>-<slug>/index.md
```

It enforces: a `reader_goal` in frontmatter (what the reader can DO after
reading), a declared `diataxis:` mode, at least one command/output block, and at
least one actionable section (Reproduce / Runbook / Steps / Verify / Recover).
Thresholds live in the `quality.gate` block of `.blog-craft.yaml`; the full
human checklist (including the fuzzy things the validator can't see) is
`references/checklist.md`. Papers and explainers have their own validators and
are skipped by this one. A genuinely non-teaching post (a pure announcement) may
set `quality_exempt: <reason>` — use it rarely.

## Frontmatter this methodology adds

Two fields, on every `content_type: posts` post:

```yaml
reader_goal: "Configure NUT so the homelab shuts down cleanly before the UPS battery dies."
diataxis: [how-to, reference]   # one or more of: tutorial, how-to, reference, explanation
```

`reader_goal` is the discipline in one line: if you can't state what the reader
can *do* afterward, the post has no job yet. `diataxis` forces the mode choice
from §1.

## How the other skills use this

- **`/blog-post`** loads §1–§4 to shape the draft, sets `reader_goal` + `diataxis`, and runs the §5 gate before finishing.
- **`/post-rewrite`** diagnoses an existing post against §4, gathers missing evidence via `post-researcher`, re-shapes it by §1–§3, and re-runs the gate.
