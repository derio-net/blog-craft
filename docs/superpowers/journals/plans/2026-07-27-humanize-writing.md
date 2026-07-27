# Journal: 2026-07-27-humanize-writing

<!-- fr:journal kind=discovery scope=plan id=p1-test-venv-bridge created=2026-07-27T21:58:49 phase=1 -->
### p1-test-venv-bridge · discovery · run-unit.sh works inside the exec bridge with its default /tmp venv (phase 1)

The exec bridge runs in the devcontainer, where /tmp IS writable, so plain 'fr isolation exec -- bash tests/run-unit.sh' works with the default venv path. Host paths (e.g. the session scratchpad) are NOT writable from inside the container (Permission denied), so do NOT set BLOG_CRAFT_TEST_VENV to a host path. The project memory about /tmp being unwritable applies to host-side agent sessions only.

<!-- fr:journal kind=discovery scope=plan id=p1-validator-mirror created=2026-07-27T22:41:58 phase=1 -->
### p1-validator-mirror · discovery · validate_educational.py is mirrored — every edit must be re-copied to templates/hugo-hextra/scripts/ (phase 1)

tests/unit/test_mirrors.py and tests/unit/test_educational_materialization.py enforce byte-identity between tools/validate_educational.py and templates/hugo-hextra/scripts/validate_educational.py (the copy shipped into blogs for plugin-less CI). Phase 1's plan text did not mention this; the fix is the repo convention: edit tools/, then cp to the template mirror. Phases 3-5 touch this file again and MUST re-mirror each time. Note the mirror's load_lint_data() default path resolves to a skills/ path that does not exist in a materialized blog — fine today (nothing calls it there yet) but the lint-layer phase must decide how the blog copy gets ai-tells data.

<!-- fr:journal kind=finding scope=plan id=p1-pytest-tmp-flake created=2026-07-27T22:42:04 phase=1 state=open -->
### p1-pytest-tmp-flake · finding [open] · Container test flake: /tmp/pytest-of-vscode numbered-dir pool exhausts across repeated full-suite runs (phase 1)

Repeated full-suite runs inside the devcontainer intermittently error out (~40-165 ERRORs, OSError 'could not create numbered dir with prefix pytest- in /tmp/pytest-of-vscode after 10 tries') on any test using tmp_path — glossary, version, roadmap, etc. Unrelated to the phase-1 change. Workaround that deterministically restores green: rm -rf /tmp/pytest-of-vscode before the run (verified twice: 555 passed clean). Pre-existing environmental issue; consider a basetemp cleanup in tests/run-unit.sh.

<!-- fr:journal kind=decision scope=plan id=p2-blog-side-lint-data created=2026-07-27T22:55:59 -->
### p2-blog-side-lint-data · decision · Blog-side lint data: ship ai-tells.md as a scripts/ sibling mirror; missing data = loud LINT SKIPPED

Phase 1 flagged that the mirrored validator's load_lint_data() default path (skills/educational-writing/references/ai-tells.md) cannot resolve in a materialized blog. Decision (both halves implemented + tested in phase 2): (1) ai-tells.md ships into blogs as templates/hugo-hextra/scripts/ai-tells.md — a byte-identical mirror registered in tests/unit/test_mirrors.py MIRRORS, same convention as glossary_scan.py traveling with validate_glossary.py; the manifest's framework glob scripts/** already covers it, so bootstrap/update need no code change. load_lint_data() resolves: explicit path -> plugin skills/ path -> sibling ai-tells.md next to the script. (2) If neither exists (a blog whose scripts/ predates ai-tells.md), the CLI prints 'LINT SKIPPED: ... — running the structural gate only' and stays gate-only with exit 0 — never a crash, never a silent skip. Tests: test_blog_copy_lints_via_sibling_ai_tells and test_blog_copy_without_ai_tells_skips_lint_loudly in tests/unit/test_educational_lint.py copy the validator into a tmp 'blog' scripts/ dir with and without the data file. NOTE for phases 3-5: ai-tells.md is now ALSO mirrored — editing skills/educational-writing/references/ai-tells.md requires cp to templates/hugo-hextra/scripts/ai-tells.md.

<!-- fr:journal kind=discovery scope=plan id=p2-hw3-flipped-early created=2026-07-27T23:03:15 -->
### p2-hw3-flipped-early · discovery · HW-3 flipped to ci in phase 2 (completion nag + repo backfill rule), not phase 5

fr plan edit --complete-phase 2 warned that HW-3/HW-4 were still not-implemented, and the repo's acceptance-matrix rule requires rows to move in the same PR as the tests that verify them. So phase 2 flipped HW-3 to ci citing tests/unit/test_educational_lint.py, test_ai_tells.py, and test_config_schema.py, and regenerated the report set (fr acceptance report --deterministic). HW-4 (quality.lint seeding) stays not-implemented with a note pointing at the pipeline-wiring phase (phase 4) — its seeding behavior does not exist yet. Phase 5 executor: HW-3 is already done; do not double-flip. HW-1 (reader-arc/what-transfers prose) note may deserve a levels ref to the what-transfers lint tests when phase 3/5 touch it.
