# Journal: 2026-09-19-consumer-framework-divergence

<!-- fr:journal kind=discovery scope=plan id=891786345f4e created=2026-09-19T01:16:23 -->
### 891786345f4e · discovery · no-refactor-because P2.T1

P2.T1 already ends with a dedicated refactor and full-suite quality-gate step (P2.T1.S3); the self-review heuristic did not recognize its wording.

<!-- fr:journal kind=discovery scope=plan id=1569a0cfc721 created=2026-09-19T01:17:01 phase=1 -->
### 1569a0cfc721 · discovery · Strict manifest validation is sufficient (phase 1)

A simple YAML file at the blog root can validate declared paths against the shipped ownership manifest without altering render or sync-state behavior.

<!-- fr:journal kind=finding scope=plan id=phase-1-root-mapping created=2026-09-19T01:17:11 phase=1 state=fixed -->
### phase-1-root-mapping · finding [fixed] · Override manifest root type could crash (phase 1)

Fixed before integration: a YAML scalar parses successfully but has no .get. Require the document root to be a mapping and raise OverridesError.

<!-- fr:journal kind=discovery scope=plan id=2b8aabef5894 created=2026-09-19T01:18:24 phase=2 -->
### 2b8aabef5894 · discovery · Divergence reuses merge behavior (phase 2)

The existing merged branch needs only the update-time divergence classification. apply_plan already writes merge results, while conflicts retain both input files.

<!-- fr:journal kind=finding scope=plan id=phase-2-update-docs created=2026-09-19T01:18:42 phase=2 state=fixed -->
### phase-2-update-docs · finding [fixed] · Consumer-facing update documentation omitted the manifest (phase 2)

Added the override file schema and divergence behavior to skills/update/SKILL.md, then regenerated the OpenCode mirror.

<!-- fr:journal kind=finding scope=plan id=phase-2-cli-error created=2026-09-19T01:21:20 phase=2 state=fixed -->
### phase-2-cli-error · finding [fixed] · Invalid manifest needed CLI-safe failure (phase 2)

The loader initially raised OverridesError at the CLI boundary. The CLI now emits a concise ERROR and exits 2 before rendering or applying, covered by a dedicated test.
