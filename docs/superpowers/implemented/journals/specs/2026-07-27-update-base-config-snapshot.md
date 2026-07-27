# Journal: 2026-07-27-update-base-config-snapshot

<!-- fr:journal kind=decision scope=spec id=d1-general-fix created=2026-07-27T15:09:19 -->
### d1-general-fix · decision · Take the config-snapshot fix, not feature-flag diffing

Operator brief pre-answered the fork: 'choose the more general fix'. Snapshot restores render(config_at_last_sync, templates_at_recorded_version); the narrow mitigation fixes toggles only and leaves site_dir / palette / series changes broken, and needs a hand-maintained per-feature path registry.

<!-- fr:journal kind=decision scope=spec id=d2-non-interactive created=2026-07-27T15:09:19 -->
### d2-non-interactive · decision · Non-interactive session: remaining calls decided and flagged, not blocked on

This runner has no AskUserQuestion channel. The four residual choices (snapshot filename/location, write policy, NOOP label, no auto-bump of blog_craft_version) are reversible engineering calls, recorded in the spec's Decisions section with reasoning and surfaced in the PR body for review. Blocking would have delivered nothing against an explicit 'open a PR when complete' contract.

<!-- fr:journal kind=review scope=spec id=r1-spec-review created=2026-07-27T15:09:25 -->
### r1-spec-review · review · Spec reviewed against codebase reality

Verified: bootstrap-render.sh stamps blog_craft_version into a temp AUGMENTED answers file (so 'effective config' is well-defined); reproduce.structural_diff flags unclassified staging paths, so the manifest content row is required not cosmetic; tests/reproduction/test_golden_configs.py renders twice and demands zero drift, so the snapshot header must be timestamp-free; sync_state needs no PyYAML (byte copy), unlike the layer-palette step it sits beside. Spec amended for the last two.
