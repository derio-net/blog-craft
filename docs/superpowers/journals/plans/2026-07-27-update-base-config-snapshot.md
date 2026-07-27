# Journal: 2026-07-27-update-base-config-snapshot

<!-- fr:journal kind=discovery scope=plan id=p2-noop-is-the-tell created=2026-07-27T15:24:02 phase=2 -->
### p2-noop-is-the-tell · discovery · The wrong base and the NOOP report are the same event (phase 2)

With the base rendered from the post-toggle config, the merge resolves entirely in local's favour — so the very entry that silently dropped the feature is exactly the one the new NOOP action names. The reporting fix is not a separate nicety: it is the observable surface of the base defect, and test_base_rendered_with_the_post_toggle_config_drops_it asserts both in one place.
