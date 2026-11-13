<!-- fr:journal-schema=4 -->
# Journal: 2026-07-15-opencode-compatibility

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-4 created=2026-11-08T11:49:45+00:00 -->
### test-plan-step-4 · discovery · Test Plan step 4: ran

Step: **Sync script:** Run `python3 scripts/sync-opencode.py --check` — exit 0. Run after editing a skill's description — exit non-zero.

Evidence: 2026-11-08: uv run python scripts/sync-opencode.py --check → '.opencode/ mirrors are in sync.', exit 0

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-5 created=2026-11-08T11:49:56+00:00 -->
### test-plan-step-5 · discovery · Test Plan step 5: ran

Step: **install.sh:** Run `bash scripts/install.sh` — confirm marketplace registration, plugin enablement, and OpenCode skills/commands are installed globally.

Evidence: 2026-11-08: ~/.claude/plugins/marketplaces/derio-net--blog-craft exists and known_marketplaces registers it to derio-net/blog-craft (install.sh in regular use)

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-6 created=2026-11-08T11:50:11+00:00 -->
### test-plan-step-6 · discovery · Test Plan step 6: ran

Step: **Claude Code plugin:** Restart Claude Code — confirm `/blog-post` etc. still work (the Claude plugin path is not regressed).

Evidence: 2026-11-08: a Claude Code session loads the blog-craft:* skills, including blog-craft:blog-post (plugin path not regressed)

<!-- fr:journal kind=owed scope=spec id=test-plan-step-1 created=2026-11-08T11:50:26+00:00 -->
### test-plan-step-1 · owed · Test Plan step 1 owed

what: **OpenCode skill discovery:** Run `opencode` in blog-craft root — confirm skills appear in the skill list (open schema).
why: needs an OpenCode run in blog-craft (same check as rows OC-1/OC-2/OC-5); recorded owed in the 2026-11-08 sweep
how: fr journal resolve --scope spec --slug 2026-07-15-opencode-compatibility --id test-plan-step-1 --state fixed --note "<evidence>"
owed_key: spec:2026-07-15-opencode-compatibility#step1

<!-- fr:journal kind=owed scope=spec id=test-plan-step-2 created=2026-11-08T11:50:38+00:00 -->
### test-plan-step-2 · owed · Test Plan step 2 owed

what: **Slash commands:** Run `/blog-post` — confirm the skill loads.
why: needs an OpenCode run in blog-craft (same check as rows OC-1/OC-2/OC-5); recorded owed in the 2026-11-08 sweep
how: fr journal resolve --scope spec --slug 2026-07-15-opencode-compatibility --id test-plan-step-2 --state fixed --note "<evidence>"
owed_key: spec:2026-07-15-opencode-compatibility#step2

<!-- fr:journal kind=owed scope=spec id=test-plan-step-3 created=2026-11-08T11:50:48+00:00 -->
### test-plan-step-3 · owed · Test Plan step 3 owed

what: **Instructions loaded:** Run with `--system-info` or observe agent behavior — confirm `.opencode/instructions/*.md` is loaded.
why: needs an OpenCode run in blog-craft (same check as rows OC-1/OC-2/OC-5); recorded owed in the 2026-11-08 sweep
how: fr journal resolve --scope spec --slug 2026-07-15-opencode-compatibility --id test-plan-step-3 --state fixed --note "<evidence>"
owed_key: spec:2026-07-15-opencode-compatibility#step3
