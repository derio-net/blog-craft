# Journal: 2026-07-27-update-base-config-snapshot

<!-- fr:journal kind=discovery scope=plan id=p2-noop-is-the-tell created=2026-07-27T15:24:02 phase=2 -->
### p2-noop-is-the-tell · discovery · The wrong base and the NOOP report are the same event (phase 2)

With the base rendered from the post-toggle config, the merge resolves entirely in local's favour — so the very entry that silently dropped the feature is exactly the one the new NOOP action names. The reporting fix is not a separate nicety: it is the observable surface of the base defect, and test_base_rendered_with_the_post_toggle_config_drops_it asserts both in one place.

<!-- fr:journal kind=discovery scope=plan id=p3-head-as-ref created=2026-07-27T15:29:32 phase=3 -->
### p3-head-as-ref · discovery · The smoke leg uses blog_craft_version: HEAD to stay tag-free (phase 3)

base_by_rerender resolves any git ref, not just tags. Pinning the toggle leg to the last real tag would rot — the old templates eventually cannot render a newer config schema — and what the leg tests is which CONFIG the base uses, not which templates. HEAD gives a real git archive round-trip with no tag dependency. Caveat recorded in the script: HEAD is committed state, so template edits must be committed before running it locally.

<!-- fr:journal kind=finding scope=plan id=f1-only-scope-snapshot created=2026-07-27T15:38:08 phase=4 state=fixed -->
### f1-only-scope-snapshot · finding [fixed] · A scoped --only apply recorded a full sync, reintroducing #60 by another door (phase 4)

update.py --only 'scripts/**' --apply wrote .blog-craft.sync.yaml as if the whole blog had been synced to the current config. Every path outside the scope would then be diffed against a base rendered from a config it was never rendered with — the exact shape of #60. Fixed: a scoped apply leaves the snapshot alone and says so; test_a_scoped_apply_does_not_claim_a_sync pins it, and the SKILL.md scoping section documents it.

<!-- fr:journal kind=finding scope=plan id=f2-snapshot-write-failure created=2026-07-27T15:38:08 phase=4 state=fixed -->
### f2-snapshot-write-failure · finding [fixed] · A snapshot write failure tracebacked after files were already applied (phase 4)

write_snapshot was called unguarded at the end of a successful --apply, so an OSError (read-only checkout, permissions) would raise after the merge results were on disk — telling the operator the run failed when it had in fact applied. Fixed: caught, warned with the #60 consequence spelled out, run still reports success. test_a_snapshot_write_failure_does_not_undo_a_successful_apply.

<!-- fr:journal kind=finding scope=plan id=f3-tally-drops-unknown created=2026-07-27T15:38:08 phase=4 state=fixed -->
### f3-tally-drops-unknown · finding [fixed] · plan_summary silently dropped any action outside its hardcoded list (phase 4)

The tally iterated a fixed _ACTIONS tuple, so an action added later would be counted and then never printed — a silent undercount in the very reporting fix meant to end silent outcomes. Fixed: known actions first for stable order, then anything unrecognised, so nothing vanishes.
