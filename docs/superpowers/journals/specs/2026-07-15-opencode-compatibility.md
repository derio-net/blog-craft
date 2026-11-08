<!-- fr:journal-schema=3 -->
# Journal: 2026-07-15-opencode-compatibility

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-4 created=2026-11-08T11:49:45+00:00 -->
### test-plan-step-4 · discovery · Test Plan step 4: ran

Step: **Sync script:** Run `python3 scripts/sync-opencode.py --check` — exit 0. Run after editing a skill's description — exit non-zero.

Evidence: 2026-11-08: uv run python scripts/sync-opencode.py --check → '.opencode/ mirrors are in sync.', exit 0
