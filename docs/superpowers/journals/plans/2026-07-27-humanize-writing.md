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
