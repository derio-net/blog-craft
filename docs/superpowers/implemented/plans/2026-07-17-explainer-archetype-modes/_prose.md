# Explainer archetype modes — implementation

Wire the already-declared `archetype` argument through the explainer scaffold
and validator so all six modes are first-class, not just `feature-deep-dive`.

Spec: `docs/superpowers/specs/2026-07-17-explainer-archetype-modes-design.md`.

## Shape

Three phases, TDD throughout, byte-identical mirror edits into
`templates/content-type-explainers/shared/scripts/`:

1. **Validator first (structural check).** The scaffold in phase 2 must obey
   the validator's section contract, so the contract is defined and tested
   first. Extend `validate_post` backward-compatibly with an optional `body`
   param: an unknown `archetype` fails always; a body that drifts from the
   archetype's canonical `##` headings (missing / reordered) fails, extras are
   allowed, and `## ` inside fenced code is ignored. `body=None` skips the
   structural check so the existing frontmatter-only callers are untouched.

2. **Scaffold `--archetype`.** Default `feature-deep-dive` (unchanged output).
   A `case` validates the id and selects the section block. Each scaffolded
   file round-trips clean through the phase-1 validator.

3. **Docs + version + acceptance.** Update `SKILL.md` and `archetypes.md`,
   bump 0.6.0 → 0.7.0 (#18 guard requires it), backfill the two matrix rows.

## Invariants

- **Mirror byte-identity** (`test_mirrors.py`): every edit to
  `tools/validate_explainers.py` and `tools/scaffold-explainer.sh` lands
  identically in the template copy. `render_explainer.py` is untouched.
- **Backward compatibility:** `parse_frontmatter` keeps its dict return
  (`test_scaffold_explainer.py` depends on it); `validate_post(fm)` with no
  body keeps working.
- **No deployment** → no post-merge Test Plan; unit suite is the full
  verification (tests drive the real script + real validator).

## Sequencing

Phase 2 depends on phase 1 (validator contract). Phase 3 depends on both.
All in one worktree, one PR, executed locally via fr-execute.
