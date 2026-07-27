# Journal: 2026-07-27-update-base-config-snapshot

<!-- fr:journal kind=discovery scope=plan id=p2-noop-is-the-tell created=2026-07-27T15:24:02 phase=2 -->
### p2-noop-is-the-tell · discovery · The wrong base and the NOOP report are the same event (phase 2)

With the base rendered from the post-toggle config, the merge resolves entirely in local's favour — so the very entry that silently dropped the feature is exactly the one the new NOOP action names. The reporting fix is not a separate nicety: it is the observable surface of the base defect, and test_base_rendered_with_the_post_toggle_config_drops_it asserts both in one place.

<!-- fr:journal kind=discovery scope=plan id=p3-head-as-ref created=2026-07-27T15:29:32 phase=3 -->
### p3-head-as-ref · discovery · The smoke leg uses blog_craft_version: HEAD to stay tag-free (phase 3)

base_by_rerender resolves any git ref, not just tags. Pinning the toggle leg to the last real tag would rot — the old templates eventually cannot render a newer config schema — and what the leg tests is which CONFIG the base uses, not which templates. HEAD gives a real git archive round-trip with no tag dependency. Caveat recorded in the script: HEAD is committed state, so template edits must be committed before running it locally.
