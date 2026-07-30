# Journal: 2026-07-27-path-roots-and-subprocess-legibility

<!-- fr:journal kind=decision scope=spec id=d1-no-interactive-channel created=2026-07-27T15:52:35 -->
### d1-no-interactive-channel · decision · No interactive channel — decisions taken under stated assumptions

fr-goal's batched Q&A could not run: this session is a headless vibe-kanban runner with no AskUserQuestion tool. Blocking would have delivered nothing, and the operator pre-answered the largest question in the goal text ('choose the more general fix, no shortcuts'). The four operator-owned calls below are therefore taken as defaults, each recoverable, and each surfaced in the PR body for review.

<!-- fr:journal kind=decision scope=spec id=d2-relocate-and-prune created=2026-07-27T15:52:35 -->
### d2-relocate-and-prune · decision · Stale legacy copies are RELOCATED and pruned on --apply, reported on dry-run

Issue #61: 'deleting the inert copy and putting a correct workflow at the repo root does not settle it — the next /update re-adds the dead file'. Report-only does not self-heal, so /update relocates: the operator's copy at the stale destination becomes the 3-way 'local' at the correct destination, and the stale file is removed once the new one is written. A CONFLICT writes nothing and leaves both files in place. Alternative rejected: report-only (leaves the two-copies-no-signal state the issue is about).

<!-- fr:journal kind=decision scope=spec id=d3-hookify-shipped-correctly created=2026-07-27T15:52:35 -->
### d3-hookify-shipped-correctly · decision · The hookify rule ships at hookify's real discovery path, templated on site_dir

Verified (not assumed) against hookify's loader: core/config_loader.py:210 does glob.glob('.claude/hookify.*.local.md') relative to the process CWD (the Claude Code project root). The shipped '.hookify.warn-hextra-weight-zero.md' matches neither the directory nor the filename, so it has never loaded for ANY blog — not just site_dir ones. It moves to '.claude/hookify.warn-hextra-weight-zero.local.md', repo-rooted, and becomes a .tmpl because its own file_path pattern must carry the site prefix ('blog/content/...' on a site_dir blog) — the same who-defines-the-location question, one level down, inside the file. Alternative rejected: dropping it from the shipped surface (it is a real, useful guard; frank hand-placed a working copy, which is the evidence it is wanted).

<!-- fr:journal kind=decision scope=spec id=d4-minor-bump created=2026-07-27T15:52:35 -->
### d4-minor-bump · decision · Version bump: 0.13.1 -> 0.14.0 (minor)

Shipped-surface change (templates/ + tools/) so CI's check_version_bump_needed gate requires a bump. Minor rather than patch: /update's destination mapping and the materialized path set both change observably for site_dir blogs. Not major: no config-schema version change, and site_dir='.' blogs see only the hookify relocation.

<!-- fr:journal kind=decision scope=spec id=d5-test-plan-on-frank created=2026-07-27T15:52:35 -->
### d5-test-plan-on-frank · decision · Post-merge Test Plan runs against the real affected blog (derio-net/frank)

frank is the blog the issues were filed from and the only known site_dir blog: blog/.github/workflows/blog-ci.yml (inert, zero runs) and blog/.hookify.warn-hextra-weight-zero.md (inert) both present, with a hand-placed .claude/hookify.warn-hextra-weight-zero.local.md. It is the only place the relocation path can be verified end-to-end, so the Test Plan is operator-driven there rather than blog-craft-internal.
