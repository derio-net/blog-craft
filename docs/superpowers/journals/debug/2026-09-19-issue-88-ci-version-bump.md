# Journal: 2026-09-19-issue-88-ci-version-bump

<!-- fr:journal kind=repro scope=debug id=aa97a6e2ca3d created=2026-09-19T13:16:53 -->
### aa97a6e2ca3d · repro · PR 90 CI version gate fails

GitHub Actions run 35405669860 fails in tools/check_version_bump_needed.py: tools/update.py and skills/update/SKILL.md are shipped-surface changes without a version bump.

<!-- fr:journal kind=root-cause scope=debug id=3614613840c8 created=2026-09-19T13:16:53 -->
### 3614613840c8 · root-cause · Shipped surface requires patch version bump

The repository CI intentionally requires tools/bump_version.py patch for shipped-surface changes. The feature commit left pyproject.toml, plugin metadata, marketplace metadata, and uv.lock at 0.22.2.

<!-- fr:journal kind=finding scope=debug id=3debb0ee3925 created=2026-09-19T13:16:57 state=fixed -->
### 3debb0ee3925 · finding [fixed] · Bumped release to 0.22.3

Ran python3 tools/bump_version.py patch, which updated pyproject.toml, plugin metadata, marketplace metadata, and uv.lock. Version check and affected updater tests pass.

<!-- fr:journal kind=hypothesis scope=debug id=5fc36f029412 created=2026-09-19T13:23:51 -->
### 5fc36f029412 · hypothesis · Version bump needs changelog entry

The replacement CI run passed the version gate and ran the suite. Its only failure is tests/unit/test_changelog.py because CHANGELOG.md lacks 0.22.3; add a release section in the established format.

<!-- fr:journal kind=finding scope=debug id=816162b1d3e4 created=2026-09-19T13:23:59 state=fixed -->
### 816162b1d3e4 · finding [fixed] · Documented 0.22.3 release

Added the 0.22.3 changelog entry in newest-first order, describing the #88 divergence manifest. The changelog gate and updater coverage pass.
