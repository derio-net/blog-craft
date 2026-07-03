# Harness + Updater — reproduction proof & non-destructive updates (Group 3, P5+P6)

Third and final blog-craft group. Turns the framework built in Groups 1–2 into a
**proven** creator (the frank + stoa golden reproduction tests) and a **safe**
updater (schema migration ladder + 3-way-merge update flow). This is where
"blog-craft + config reproduces both blogs" stops being a claim and becomes a
green test.

## Phase 1 — Validation/CI + reproduction harness

The reproduction harness rests on Group 1's path-ownership manifest: apply
blog-craft + a config into a scratch dir, then structurally diff only
`framework`+`merged` paths against the real blog, ignoring content. The **frank
golden test** authors frank's `.blog-craft.yaml` (reverse-engineering frank's
image layers, series, papers, features) and drives it to **zero structural
drift** — this fixture is the exact config P7 later adopts into frank. The
**stoa golden test** (using the Group-1-migrated stoa v2 config) guards against
frank-driven regressions. blog-craft ships a CI template (validation core +
config-selected deploy tail) and gains its own CI running the full suite.

## Phase 2 — Updater

Makes blog-craft an *updater*, not just a one-time bootstrap. A version-gated,
golden-fixtured **migration ladder** evolves configs (v2→v3…) purely and
non-destructively. The **update flow** renders to a staging tree, classifies
every path via the manifest, recovers the 3-way-merge base by re-rendering at
the recorded `blog_craft_version` (no stored baseline), runs `diff3` surfacing
conflicts, and emits a reviewable dry-run diff. `smoke-update` exercises a full
vN→vN+1 cycle — dry-run golden, apply, Hugo builds, reproduction still passes —
so the upgrade path is proven before any real blog is touched.

## TDD & gates

Test-first throughout. P1 gate: **both golden tests green = parity proven**
(spec §12.1–2). P2 gate: `smoke-update` green (spec §12.5).

## Sequencing

Stacked on Group 2; re-targeted to `main` as Groups 1–2 merge. After Group 3
lands and the harness is green, frank's **P7** cutover adopts the proven frank
config and retires frank's inline tooling.
