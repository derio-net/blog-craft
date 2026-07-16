# Diagram quality gate — require a Mermaid diagram in how-to / tutorial posts

- **Issue:** derio-net/blog-craft#25
- **Branch:** `feat/suggest-diagram-gate`
- **Date:** 2026-07-16
- **Type:** feature (validator + config + docs)

## Goal

For visual learners a topology/flow diagram is the difference between
understanding and guessing. Add a build-time check that a post which teaches a
*procedure* (Diátaxis `how-to` or `tutorial`) carries at least one
` ```mermaid ` block, and fails the quality gate with a `file:line`-style
message and a concrete suggestion when it does not.

## Operator decisions (batched Q&A, 2026-07-16)

1. **Integration — fold into `quality.gate`.** No new standalone
   `tools/suggest_diagram.py`, no new CI step. The check becomes a fifth
   sibling inside `tools/validate_educational.py`'s existing gate, riding the
   already-wired `{{ with .quality }}{{ if .enabled }}` CI step. This diverges
   from #25's "new script" wording; the code has a better home the issue could
   not have known about.
2. **Trigger — `how-to` + `tutorial`.** A post whose normalized `diataxis`
   modes include `how-to` OR `tutorial`, with no ` ```mermaid ` fence in the
   body, fails. Reference/explanation posts are unaffected. Hard rule ("err
   toward too many diagrams"), no fuzzy multi-component heuristic.
3. **Default — on (opt-out).** `gate.require_diagram` defaults `True`, so it is
   active wherever `quality.enabled` is already true. A post that legitimately
   needs no diagram opts out with `diagram_exempt: <reason>` in frontmatter
   (targeted — waives only the diagram check, unlike whole-post
   `quality_exempt`).

## Design

### `tools/validate_educational.py` (canonical) + its shipped mirror

- Add `"require_diagram": True` to `_DEFAULT_GATE`.
- Add `_has_mermaid(body: str) -> bool` — scans fenced blocks with the same
  fence regex `_count_command_blocks` already uses; returns `True` on the first
  block whose info string `startswith("mermaid")`.
- In `validate_post(fm, body, gate)`, after the diataxis check, add:
  ```
  if g.get("require_diagram") and not fm.get("diagram_exempt"):
      modes = _normalize_modes(fm.get("diataxis"))
      if ({"how-to", "tutorial"} & set(modes)) and not _has_mermaid(body):
          fails.append("<message naming the mode + suggesting a ```mermaid block>")
  ```
  `_normalize_modes` is reused so it composes with the existing
  `require_diataxis_mode` normalization/aliasing (e.g. `howto` → `how-to`).
- CLI footer message: mention `diagram_exempt: <reason>` as the opt-out
  alongside the existing `quality_exempt` hint.

### Mirror sync + guard-gap fix

`templates/hugo-hextra/scripts/validate_educational.py` is byte-identical to
the canonical copy today but is **absent from `tests/unit/test_mirrors.py`'s
`MIRRORS` list** — a latent drift bug, since materialized-blog CI runs the
shipped copy. This PR:
- applies the identical edit to the shipped copy, and
- adds `("tools/validate_educational.py", "templates/hugo-hextra/scripts/validate_educational.py")`
  to `MIRRORS` so the pair can never silently diverge again.

### `docs/CONFIG.md` §7

Add a `gate.require_diagram` row (default `true`) to the gate table, and a line
documenting the `diagram_exempt: <reason>` per-post opt-out. Note the trigger
modes (how-to / tutorial) in the §7 prose.

## CI wiring

None. The check rides the existing `validate_educational.py` gate step in
`templates/hugo-hextra/.github/workflows/blog-ci.yml.tmpl`. Nothing new is
added to the workflow.

## Test Plan

Pure code + config; **no deployment**, so no post-merge operator Test Plan.
Verification is the unit suite (`tests/run-unit.sh`).

### Unit tests (`tests/unit/test_educational_validator.py`)

Red-first, one behavior each:
- how-to post **with** a ` ```mermaid ` block → passes (no diagram failure).
- how-to post **without** a diagram → fails with the diagram message.
- tutorial post without a diagram → fails.
- reference / explanation post without a diagram → passes (mode not triggered).
- `diagram_exempt: <reason>` on a diagram-less how-to → passes.
- `quality_exempt` on a diagram-less how-to → skipped entirely (CLI level).
- `require_diagram: False` in gate → diagram-less how-to passes (toggle honored).
- `_has_mermaid` recognizes `mermaid`, `` ```mermaid `` with trailing space,
  and is not fooled by a fenced block that merely mentions "mermaid" in prose.

### Mirror test (`tests/unit/test_mirrors.py`)

- New `MIRRORS` entry makes `test_mirrors_identical` cover the pair; it passes
  because both copies got the identical edit (and would fail if only one did).

## Acceptance rows (matrix backfill — same PR)

- **DQ-1** — "A how-to/tutorial post with no Mermaid diagram fails the quality
  gate" — level `unit=blog-craft:tests/unit/test_educational_validator.py`,
  status `ci`.
- **DQ-2** — "`diagram_exempt:` waives the diagram requirement for one post" —
  level `unit=blog-craft:tests/unit/test_educational_validator.py`, status `ci`.

## Out of scope

- Suggesting a diagram *type* or auto-generating diagrams.
- The soft multi-component heuristic (explicitly declined).
- Retrofitting diagrams into existing posts (the gate reports; authors fix).
