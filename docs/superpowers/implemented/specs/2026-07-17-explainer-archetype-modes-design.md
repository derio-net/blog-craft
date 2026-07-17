# Explainer archetype modes — design

- **Date:** 2026-07-17
- **Branch:** `feat/explainer-modes`
- **Issue:** none (operator ask — "build up the explainer, it has a few modes that are not implemented")
- **Status:** design → plan

## Problem

The `explainers` content-type declares **six archetypes** ("modes"), but only
one is actually implemented:

- `skills/explainers/SKILL.md` §Archetypes: *"The default (and only
  fully-scaffolded) archetype is `feature-deep-dive`. Five additional
  guidance-only archetypes are documented in
  `references/archetypes.md` — no scaffold, no validator."*
- `scaffold-explainer.sh` **hardcodes** `archetype: feature-deep-dive`
  (line 91) and always emits the same six-section skeleton. It has **no
  `--archetype` flag**, even though the skill's frontmatter already lists
  `archetype` as a declared argument.
- `validate_explainers.py` checks frontmatter + the weight invariant but
  **never validates the `archetype` value** — a typo'd or bogus archetype
  passes silently.

So five of the six declared modes exist only as prose recipes. Authoring one
means hand-copying its section structure out of `references/archetypes.md`,
and nothing catches a post that drifts from (or misnames) its archetype.

## Goal

Wire the already-declared `archetype` argument through the scaffold + validator
so all six archetypes are first-class:

1. `scaffold-explainer.sh --archetype <id>` emits that archetype's section
   structure and stamps `archetype: <id>` in frontmatter.
2. `validate_explainers.py` enforces that a post's `##` sections match its
   declared archetype's recipe (and rejects unknown archetypes).

Pure code + docs + tooling. **No deployment surface → no post-merge Test
Plan.** Verified end-to-end at the unit level (the tests invoke the real
shell script and the real validator).

## Decisions (operator Q&A, 2026-07-17)

| Decision | Choice |
|---|---|
| Scope | **All five** guidance-only archetypes become fully-scaffolded |
| Scaffold richness | **Sections only** — headings + a one-line budget/guidance comment each; no pre-seeded Mermaid/table stubs (matches `feature-deep-dive`) |
| Validation | **Structural check** — the post's `##` headings must match the archetype's recipe; unknown archetypes fail |
| Archetype ids | `skill-presentation`, `skill-comparison`, `testing-pyramid`, `deployment-strategy`, `security-posture` (+ existing `feature-deep-dive`) |

## The six archetypes and their canonical sections

The scaffold emits exactly these `##` headings (in order) per archetype; the
validator enforces them. Budget/guidance comment shown in italics after each.

### `feature-deep-dive` (unchanged)
- Overview · Why it exists · How it works · Code walkthrough · Tradeoffs & alternatives · Try it yourself

### `skill-presentation` — Presenting a Claude Skill
- **Overview** — *One paragraph: what the skill does and the problem it solves.*
- **When it triggers** — *The conditions that activate it (user phrases, repo context, config gates). Include a concrete invocation example.*
- **Workflow** — *Step-by-step lifecycle. A Mermaid sequence diagram or flowchart if the flow branches.*
- **Configuration** — *What the operator configures (arguments, config knobs, env vars). A table or `cards` if comparing options.*
- **Try it yourself** — *Minimal reproducible invocation with expected output.*

### `skill-comparison` — Comparing Two Similar Skills
- **Overview** — *What both skills do, why a comparison matters.*
- **Side-by-side** — *A capability matrix (feature rows, skill columns); each cell ✓/✗/partial with a one-line note.*
- **When to choose which** — *Decision criteria: context size, autonomy, output format, cost. A Mermaid decision flowchart with ≤4 leaves.*
- **Concrete divergence** — *One scenario where the two produce different results; show both outputs.*
- **Try it yourself** — *Invoke both on the same input, compare outputs.*

### `testing-pyramid`
- **Overview** — *What the testing strategy is and why this shape.*
- **The pyramid** — *A Mermaid pyramid/flowchart of the repo's actual layers with real counts. Label each layer with its test dir or runner.*
- **One example per layer** — *A minimal test from each layer with a `file:line` ref and one sentence on what it covers.*
- **Gaps and tradeoffs** — *What's missing or under-tested; deliberate choices.*
- **Try it yourself** — *How to run the full suite, how to run one layer.*

### `deployment-strategy`
- **Overview** — *One paragraph: the deployment model (CI/CD, manual, hybrid).*
- **The pipeline** — *A Mermaid flowchart of the actual CI/CD flow: triggers, jobs, gates, environments. Label each node with the workflow file and job.*
- **Environments** — *A table of environments (staging, production, canary), what deploys to each, how promotion works.*
- **Rollback path** — *How to revert: the command, the trigger, the expected time-to-recover.*
- **Try it yourself** — *How to trigger a deploy manually (if possible), how to verify it landed.*

### `security-posture`
- **Threat surface** — *What's exposed (endpoints, file access, secrets, CI inputs). One sentence per surface, rated high/medium/low.*
- **What's enforced in CI** — *Automated checks: secret scanning, dependency audit, SAST, permission boundaries. Name the workflow and tool.*
- **What's manual** — *Things requiring human review: privilege escalation, credential rotation, infra changes. Why they can't be automated.*
- **One concrete control** — *Deep-dive on one control: what it enforces, where it's defined (file:line), how it's tested.*
- **Try it yourself** — *How to run the security checks locally.*

## Design

### 1. `scaffold-explainer.sh` — add `--archetype`

- New flag `--archetype <id>` (default `feature-deep-dive`), parsed in the
  existing `while`/`case` arg loop; applies to both blog and standalone modes.
- Validate the id against the known set up front; unknown → error + exit 1
  (single source of truth: a `case "$ARCHETYPE" in` that both validates and
  selects the section block).
- Frontmatter line becomes `archetype: ${ARCHETYPE}` (was hardcoded).
- A `sections_for()` shell helper (a `case` over the archetype) emits the
  correct heading block into the heredoc. Everything else — weight math,
  bundle/standalone layout, duplicate refusal — is unchanged.

### 2. `validate_explainers.py` — structural archetype check

- Add `ARCHETYPE_SECTIONS: dict[str, list[str]]` — the six canonical heading
  lists above (heading text without the leading `## `).
- Add `extract_h2(body: str) -> list[str]` — the ordered level-2 headings.
  **Strips fenced code blocks first** so a `## ` line inside a ```` ``` ````
  snippet is never mistaken for a section (real risk: shell/markdown examples).
- Extend the library signature **backward-compatibly**:
  `validate_post(fm, weight_offset=1, explainers_key="explainers", body: str | None = None) -> list[str]`.
  - `archetype` present but **not** in `ARCHETYPE_SECTIONS` → fail (runs even
    when `body is None`, so a typo is caught frontmatter-only).
  - `body` provided and archetype known → **ordered-superset** check: every
    canonical heading must be present, and the present ones must appear in
    canonical relative order. **Extra `##` sections are allowed** (an author
    may append "Further reading"), but a missing or reordered required section
    fails. A freshly scaffolded post passes by construction.
  - `body is None` → structural (heading) check skipped — preserves existing
    frontmatter-only callers (`validate_post(fm)` in the unit tests).
- CLI `_main`: read the full file text, parse frontmatter (unchanged
  `parse_frontmatter` → dict), and pass the post-frontmatter body to
  `validate_post(..., body=body)` so the CLI always runs the full check.
  `parse_frontmatter`'s dict return is **unchanged** (a separate small
  body-split is used for the CLI; `parse_frontmatter` keeps its signature).

### 3. Mirrors (byte-identical — `tests/unit/test_mirrors.py`)

Both edited scripts are mirrored; the edits land identically in both copies:
- `tools/scaffold-explainer.sh` ↔ `templates/content-type-explainers/shared/scripts/scaffold-explainer.sh`
- `tools/validate_explainers.py` ↔ `templates/content-type-explainers/shared/scripts/validate_explainers.py`
- `render_explainer.py` is untouched.

### 4. Docs

- `skills/explainers/SKILL.md` — drop "only fully-scaffolded" language; list
  all six archetype ids; show `scaffold-explainer.sh --archetype <id>` in the
  scaffold step; note the validator now enforces archetype structure.
- `skills/explainers/references/archetypes.md` — add the `id:` for each of the
  five recipes (so the prose and the machine id are co-located), and note the
  five are now scaffolded, not guidance-only.
- `CHANGELOG.md` — a `0.7.0` entry.

### 5. Versioning (#18 machinery)

Touches `tools/` + `skills/` + `templates/` → the bump-guard requires a bump.
New capability → **0.6.0 → 0.7.0** (`tools/bump_version.py minor`). On merge,
`auto-tag.yml` cuts `v0.7.0`.

## Out of scope

- Pre-seeded Mermaid/table visual stubs (operator chose "sections only").
- Per-archetype validators beyond the section-structure check (e.g. "the
  pyramid archetype must contain a `mermaid` block") — the diagram gate (#25)
  already covers diagram presence for how-to/tutorial; explainers stay light.
- A config registry of archetypes in `.blog-craft.yaml` — archetype is a
  per-post frontmatter value, not an operator config knob.

## Test Plan

Pure code + docs + tooling, **no deployment** → no post-merge Test Plan.
Verification is the unit suite (the scaffold tests invoke the real
`scaffold-explainer.sh`; the validator tests call the real `validate_post`):

- **Scaffold** (`test_scaffold_explainer.py`, extended):
  - each of the 6 archetypes: `--archetype <id>` → frontmatter `archetype: <id>`
    and the file contains exactly that archetype's `##` headings;
  - default (no flag) → `feature-deep-dive` (unchanged);
  - unknown `--archetype bogus` → non-zero exit.
- **Validator** (`test_explainers_validators.py`, extended):
  - scaffolded body for each archetype → no failures;
  - unknown archetype value → failure (with and without body);
  - missing / reordered required section → failure; extra section → OK;
  - `## ` inside a fenced code block is **not** counted as a section;
  - backward compat: `validate_post(fm)` (no body) → structural check skipped.
- **Mirror** (`test_mirrors.py`): byte-identity of both edited scripts (auto).
- Full suite green in the dev container; `bump_version.py --check` consistent
  at 0.7.0.

## Implementation Plans

| Plan | Repo | File | Depends on |
|------|------|------|------------|
| 2026-07-17-explainer-archetype-modes | `derio-net/blog-craft` | `2026-07-17-explainer-archetype-modes` | — |

## Acceptance rows (backfilled, same PR)

- `explainer-archetype-scaffold` (ci) — the operator can scaffold any of the
  six archetypes via `--archetype`, getting that archetype's section structure.
- `explainer-archetype-structure-validation` (ci) — the validator rejects a
  post whose `##` sections don't match its declared archetype, and rejects
  unknown archetypes.
