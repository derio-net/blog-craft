# Batch / campaign post-rewrite workflow + reproducible batch gate

- **Issue:** derio-net/blog-craft#26
- **Branch:** `feat/batch-rewrite-workflow`
- **Date:** 2026-07-16
- **Type:** feature (skill workflow section + operator script + tests)

## Goal

Capture the multi-post rewrite-campaign workflow discovered during a 51-post
rewrite: process posts in small batches (3-5/round), rewrite each in depth,
edit **in-place**, keep `hugo server` running for live preview, produce a
compact per-post summary before each approval round, and gate (validate +
hugo build) after each batch before committing. The earlier mechanical
"rewrite all 51 at once" attempt was rejected for producing shallow, templated
content — the working pattern is *guided* automation, not full automation.

## Operator decisions (batched Q&A, 2026-07-16)

1. **Home — a section in `skills/post-rewrite/SKILL.md`.** No new sibling
   skill. The batch loop reuses the existing per-post steps (diagnose →
   evidence → rewrite → gate) inline; one place maintains the rewrite craft.
2. **Safety — in-place, git is the net.** The batch loop overwrites each
   post's `index.md` directly (no `/tmp` draft, no `.bak`), exactly as the
   issue argues — `/tmp` copies caused "stale copies and confusion". Safety
   comes from git + `hugo server` live preview + the per-batch gate + the
   per-post summaries shown before approval.
3. **Deliverable — automate the mechanical parts as reproducible code.**
   Operator principle: "if it can be automated as code, it should — validation,
   gates, hooks." So the per-batch *gate* becomes a real script
   (`batch-gate.sh`), unit-tested; only the inherently-human parts (approval
   rounds, depth of rewrite) stay as documented prose.

## Design

### 1. `templates/hugo-hextra/scripts/batch-gate.sh` (new operator script)

Ships into every blog under `scripts/` (like `hugo-serve.sh`) — an operator
script, so **no `tools/` canonical and no `test_mirrors.py` entry** (that guard
is only for plugin-canonical duplicates).

Behavior — `batch-gate.sh <post-path> [<post-path> ...]`:
1. Resolve the blog root (walk up from the first post path, or `$PWD`, for
   `.blog-craft.yaml`).
2. **Validate:** run `python3 <script-dir>/validate_educational.py --config
   <blog-root>/.blog-craft.yaml <posts...>`. Fail-fast on non-zero.
3. **Build check:** run a Hugo build (`hugo --quiet` with the `GO_LOCATIONS`
   modern-Go dance copied from `hugo-serve.sh`, since Hextra is a Hugo Module).
   Skipped with a clear warning when `hugo` (or Go) is unavailable, or when
   `BATCH_GATE_SKIP_BUILD=1` — this is what makes the validate/orchestration
   path unit-testable without a Hugo toolchain.
4. Print `BATCH GATE PASS: N post(s)` / `BATCH GATE FAILED` and exit 0/1.

`set -euo pipefail`; errors to stderr; idempotent; read-only (never edits posts).

### 2. `skills/post-rewrite/SKILL.md` — new "Batch / campaign mode" section

Added after the single-post Procedure. Documents:
- **When:** rewriting a whole series / many posts (not a single post).
- **The loop** — for each batch of **3-5** posts:
  1. For each post, run the per-post **Steps 3-6** (diagnose → gather evidence
     via post-researcher → determine reader_goal/mode → rewrite to the
     methodology), but **write the result straight to `index.md` in-place** —
     skip the single-post `/tmp` draft + `.bak`. Git is the safety net.
  2. Keep `hugo server` running in a second terminal
     (`bash scripts/hugo-serve.sh --buildDrafts`); reload `localhost:1313`
     after each edit to verify structure, diagrams, formatting.
  3. Before the approval round, emit a **per-post summary** (see format below).
  4. Run the **batch gate**: `bash scripts/batch-gate.sh <the batch's posts>`
     — must pass (validate + hugo build, 0 errors) before committing.
  5. Commit the batch, then move to the next.
- **Depth over speed** — real git-history missteps, real command output, a
  Mermaid diagram per post; never templated "what if" scenarios.
- **Per-post summary format** (issue update 2026-07-15), 3-5 lines each:
  > **NN-title** — Added: <frontmatter/diagram/missteps w/ commits>. Changed:
  > <structural moves>. Preserved: <sections kept>.
- **Operator checklist** (inline): `[ ] read the batch → [ ] gather git
  evidence → [ ] rewrite in-place → [ ] live-preview each → [ ] per-post
  summaries → [ ] batch-gate → [ ] commit batch`.

Note the divergence from single-post mode explicitly (in-place vs `/tmp`+`.bak`)
so a reader isn't confused by the two safety models.

## Test Plan

Skill doc + operator script; **no deployment** → no post-merge Test Plan.
Verification is the unit suite.

### Unit tests (`tests/unit/test_batch_gate.py`, new)

- good batch (a how-to post with evidence + diagram) with `BATCH_GATE_SKIP_BUILD=1`
  → exit 0, prints `BATCH GATE PASS`.
- bad batch (a post failing the educational gate) → exit 1, prints
  `BATCH GATE FAILED`, surfaces the underlying validator failure.
- multiple posts, one bad → exit 1 (fail-fast/aggregate).
- build auto-skip: with `BATCH_GATE_SKIP_BUILD=1` the script never invokes hugo
  (asserted by passing on a machine without hugo).
- `SKILL.md` shape: the new section exists and references `batch-gate.sh` and
  `hugo-serve.sh` (guards against the doc/script drifting apart).

## Acceptance rows (matrix backfill — same PR)

- **BRW-1** — "The batch gate validates a set of posts and fails the batch when
  any post fails the educational gate" — level
  `unit=blog-craft:tests/unit/test_batch_gate.py`, status `ci`.
- **BRW-2** — "post-rewrite documents a batch/campaign mode with in-place edits
  and a reproducible per-batch gate" — level
  `unit=blog-craft:tests/unit/test_batch_gate.py`, status `ci`.

## Out of scope

- Automating the rewrite itself or the approval rounds (guided, not full, by
  design).
- A new sibling skill (declined — lives in post-rewrite).
- Changing single-post mode's `/tmp`+`.bak` safety model.
