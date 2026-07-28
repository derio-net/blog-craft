# Journal: 2026-07-28-mermaid-readability

<!-- fr:journal kind=discovery scope=plan id=c338deac8ebf created=2026-07-28T22:13:08 phase=1 -->
### c338deac8ebf · discovery · Config surface (v6) landed: features.mermaid_view, quality.mermaid_max_width, migrations/005_to_006.py (phase 1)

tools/validate_config.py: ACCEPTED_VERSIONS extended to (2,3,4,5,6). features.mermaid_view checked only when present (bool), matching the features.glossary pattern — absent is legal and means true, resolved at render time by phases 2/3. quality.mermaid_max_width checked with the isinstance(v, bool) guard before the (int, float) check (bool is an int subclass — mirrors quality.lint.thresholds at validate_config.py:~196..202), 0 is a valid value (documented gate-disable), negative and string rejected with a message naming the key and 'non-negative number'.

migrations/005_to_006.py modeled on 004_to_005.py's shape (module docstring WHY, FROM_VERSION=5/TO_VERSION=6, pure migrate(cfg)->dict, ValueError on wrong FROM_VERSION). Uses features.setdefault('mermaid_view', True) — an explicit features.mermaid_view: false in the input config survives the migration untouched (tested in tests/unit/test_migration_ladder.py::test_005_to_006_keeps_explicit_opt_out).

<!-- fr:journal kind=discovery scope=plan id=0ff31c22bf64 created=2026-07-28T22:13:28 phase=1 -->
### 0ff31c22bf64 · discovery · Ladder-head bump to 6 is a breaking change for hardcoded-5 tests elsewhere (phase 1)

tools/migrate_config.py's latest_version() auto-discovers migrations/NNN_to_MMM.py by glob, so adding 005_to_006.py silently moved the ladder head from 5 to 6. Two pre-existing tests outside this phase's named scope hardcoded the old head and had to be fixed to keep the full suite green:
- tests/unit/test_migration_005.py::test_latest_version_is_5 -> now asserts latest_version() >= 5 (its own migration's rung, not the overall head)
- tests/unit/test_migration_005.py::test_ladder_reaches_5_from_2 -> now asserts version == 6
- tests/unit/test_migration_ladder.py::test_cli_non_destructive -> now asserts version == 6 after CLI upgrade

Any later phase adding fixtures/tests that assert an absolute 'latest version' number should grep for 'latest_version()' and 'version.*== 5' before trusting an old assumption.

<!-- fr:journal kind=finding scope=plan id=ec26e1be81b4 created=2026-07-28T22:13:41 phase=1 state=open -->
### ec26e1be81b4 · finding [open] · Acceptance matrix rows MMD-1..6 not yet added; fr plan edit warns on MMD-5 (phase 1)

'fr plan edit --complete-phase 1' warned: 'phase 1 completed but its acceptance rows are still not-implemented: mmd-5'. This is expected at this point in the plan — MMD-5 ('a blog can opt out of the framed scroller and keep prior rendering') is verified by tests/unit/test_mermaid_view_hugo.py, which is Phase 3 scope, not Phase 1. No acceptance rows were added in this phase since Phase 1 ships no user-visible/testable acceptance surface of its own (config validation only, no MMD-* row cites it directly). Whichever phase adds tests/unit/test_mermaid_view_hugo.py (Phase 3 per the plan) should run 'fr acceptance add' for MMD-1 and MMD-5 at that point, and Phase 5 for MMD-3, Phase 4 for MMD-4. MMD-2 and MMD-6 stay manual/not-implemented until the post-merge Test Plan per the spec.
