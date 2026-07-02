# Foundation — Config v2 + Approach-A image engine (Group 1, P1+P2)

First of three grouped plans implementing the blog-craft config-migration spec
(`docs/superpowers/specs/2026-06-30--blog-craft--config-migration-design.md`).
This group lays the two load-bearing foundations everything else builds on:
the **v2 config contract** (with a real validator and the path-ownership
manifest that both the reproduction harness and the updater consume) and the
**Approach-A image engine** (the generic, config-declared composition that lets
one generator reproduce both frank's layered prompts and stoa's simpler ones).

## Phase 1 — Config v2, validator, manifest, stoa migration

Replaces v1's "rely on YAML parse errors" with a real schema validator enforcing
the layer-resolution invariants (spec §4.1). Introduces `templates/manifest.yaml`
— the single artifact classifying every materialized path as `framework` /
`content` / `merged` — with a "no unclassified path" guard so a missing
`framework` path can't silently drop out of the parity test later. Migrates
stoa's live v1 config to v2 via a pure, golden-tested transform
(`migrations/001_to_002.py`); the existing bootstrap smoke must stay green.

## Phase 2 — Approach-A image engine

Adopts frank's `generate-all-images.py` as the canonical generator and removes
its one hardcoded assumption — the composition order — turning it into a generic
concatenator driven by `image.composition_order` + `image.layers`. The proof is
`smoke-image-compose`: the new generator's `--print-prompt` must be
byte-identical to the legacy generators' output for sampled frank **and** stoa
entries (deterministic, no Gemini call). Reference-pool resolution and curation
(contact sheets, `.regen-archive` FIFO) port across, config-driven.

## TDD discipline

Every task is test-first: the failing test is step 1, the implementation that
greens it is step 2. Design detail lives in the spec; steps reference it rather
than re-embedding it.

## Gates

- P1: validator unit tests pass; stoa bootstrap smoke green.
- P2: `smoke-image-compose` prompt-equality green for frank + stoa.

## Not in this group

P3–P4 (papers content-type, theme/CSS params) → Group 2. P5–P6 (reproduction
harness, updater) → Group 3. Frank's P7 cutover → separate deferred run.
