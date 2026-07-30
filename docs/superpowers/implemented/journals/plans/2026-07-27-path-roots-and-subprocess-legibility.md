# Journal: 2026-07-27-path-roots-and-subprocess-legibility

<!-- fr:journal kind=discovery scope=plan id=p1-four-sites created=2026-07-27T16:04:45 phase=1 -->
### p1-four-sites · discovery · The relative-path break has four sites, not one (phase 1)

Audited every path argument threaded into a subprocess. update.py's --config (reported) and base_by_rerender's config, PLUS reproduce.py's own --config and --scratch, all resolve after bootstrap-render.sh's internal cd. The last two are unreported in #59 and would have survived a fix scoped to the issue text.

<!-- fr:journal kind=discovery scope=plan id=p1-verified-on-frank created=2026-07-27T16:04:45 phase=1 -->
### p1-verified-on-frank · discovery · #59 verified fixed against the real blog (phase 1)

Ran the documented invocation from /home/claude/repos/frank (site_dir: blog, the blog the issues were filed from): previously a CalledProcessError traceback, now prints an 8-line plan. Note .github/** does NOT appear in that plan — the stale blog/.github/workflows/blog-ci.yml is byte-identical to the staged render, which is exactly why the inert file has never drawn attention.

<!-- fr:journal kind=discovery scope=plan id=p3-hookify-never-loaded created=2026-07-27T16:12:51 phase=3 -->
### p3-hookify-never-loaded · discovery · The hookify rule was never loaded by ANY blog, not just site_dir ones (phase 3)

#61 flagged .hookify.warn-hextra-weight-zero.md as PROBABLY the same shape and asked for verification. Verified against plugins/hookify/core/config_loader.py: load_rules() does glob.glob(os.path.join('.claude', 'hookify.*.local.md')) relative to the process CWD. The shipped file matched neither the directory nor the .local.md filename, so it was inert for every blog regardless of site_dir — worse than the issue suspected. Corroboration: frank carries a hand-written .claude/hookify.warn-hextra-weight-zero.local.md (tracked) beside the inert blog/.hookify.warn-hextra-weight-zero.md. Its file_path pattern is 'blog/content/...' where the shipped one says 'content/...' — the same who-defines-the-location question one level down, inside the file, which is why the template is now a .tmpl.

<!-- fr:journal kind=discovery scope=plan id=p2-guard-caught-it created=2026-07-27T16:12:51 phase=2 -->
### p2-guard-caught-it · discovery · The completeness guard caught the flagged path on its first run (phase 2)

test_path_roots.py's exactly-one-root assertion failed immediately on .hookify.warn-hextra-weight-zero.md — the undeclared path was the one #61 flagged. That is the evidence the guard is load-bearing rather than decorative: it forces the who-defines-this-location question at review time instead of leaving it to a future incident.

<!-- fr:journal kind=finding scope=plan id=p4-prune-ate-site-dir created=2026-07-27T16:20:24 phase=4 state=fixed -->
### p4-prune-ate-site-dir · finding [fixed] · The directory prune would have removed the operator's site directory (phase 4)

First implementation of _prune_empty_parents walked up while each directory was empty, stopping only at the blog root. In the degenerate case where the relocated file was the only thing under <site_dir>/, that removed the site directory itself. Caught by test_directories_left_empty_by_the_move_are_removed, which asserts the floor explicitly. Fixed by recording a legacy_floor on the plan entry (the site dir when the stale copy lived under it) and never pruning at or above it — a relocation retires the directories the OLD destination needed, nothing else.

<!-- fr:journal kind=finding scope=plan id=p4-replan-assertion created=2026-07-27T16:20:24 phase=4 state=fixed -->
### p4-replan-assertion · finding [fixed] · The smoke re-plan assertion conflated two different things (phase 4)

Asserted REPLAN=0 after applying a relocation. But the operator's surviving edit legitimately still differs from the shipped render, so an ordinary 3-way  remains — that is correct behaviour, not the #61 dead-file loop. Tightened to the actual invariant: the re-run must have zero entries carrying a  and must never target <site_dir>/.github again.

<!-- fr:journal kind=finding scope=plan id=r1-claude-glob-too-broad created=2026-07-27T16:40:17 phase=3 state=fixed -->
### r1-claude-glob-too-broad · finding [fixed] · Review: the .claude framework glob claimed files blog-craft does not own (phase 3)

Classifying .claude/** as framework was broader than the one file blog-craft ships there. reproduce.structural_diff walks the REFERENCE tree too and reports any framework/merged path missing from the generated tree as drift — so a blog with its own .claude/settings.json, commands/ or agents/ would have had them reported as drift, and /update would treat them as blog-craft(s) to overwrite. Narrowed to .claude/hookify.*.local.md, with a test pinning that an operator .claude/ file classifies as None. The roots glob stays broad on purpose: root_of is only consulted for paths blog-craft materializes, and any .claude/ path is repo-rooted.

<!-- fr:journal kind=review scope=plan id=v1-real-blog created=2026-07-27T16:40:24 -->
### v1-real-blog · review · Verified against the blog the issues were filed from

Dry-run of the documented invocation against /home/claude/repos/frank (site_dir: blog) plans both relocations — REPLACE blog/.hookify.warn-hextra-weight-zero.md -> .claude/hookify.warn-hextra-weight-zero.local.md, and MERGE blog/.github/workflows/blog-ci.yml -> .github/workflows/blog-ci.yml — with every other line identical to the pre-fix plan. The staged hookify rule renders pattern blog/content/.*\.md$ — byte-matching what that blog operator hand-wrote independently, which confirms the site-prefix logic rather than merely asserting it. The staged CI invokes blog/scripts/... and blog/content/..., keeps --config .blog-craft.yaml unprefixed, and carries working-directory blog.

<!-- fr:journal kind=finding scope=plan id=r2-src-roots-drift created=2026-07-27T16:48:33 state=fixed -->
### r2-src-roots-drift · finding [fixed] · The roots guard listed its own coverage by hand, and main proved that drifts

Merging origin/main (which added templates/features/mermaid-csp as a new render pass) showed the completeness guard silently not covering it — the SRC_ROOTS list was hand-maintained, which is the same class of drift the guard exists to catch. Now derived from bootstrap-render.sh by parsing its --src/--dst pairs, so a new bundle is covered the moment it is rendered. Parsing --dst as well as --src also brought the two --per-series passes into coverage (they render to $TARGET/content/docs, not $TARGET). Nine passes covered, up from six listed.

<!-- fr:journal kind=finding scope=plan id=r3-noop-vs-relocate created=2026-07-27T17:44:01 state=fixed -->
### r3-noop-vs-relocate · finding [fixed] · Merging #60 exposed a real collision: NOOP would have stranded a relocated file

main #60 added a `noop` action for a 3-way merge that resolves entirely in local favour — writing it back would rewrite the file with the bytes already in it. On a RELOCATED path that reasoning inverts: local is the copy at the OLD destination, so writing it is not a no-op, it IS the move. Left as-is, a relocated merged path whose operator edit survived intact would have reported NOOP, written nothing, and left the stale copy in place — precisely the state #61 exists to end, reintroduced by the merge. plan_update now emits relocate rather than noop whenever a legacy destination is in play, and apply_plan writes the 3-way result (not the staged bytes) for a relocation that carries one. Pinned by two tests: the collision itself, and that #60 noop behaviour is untouched for ordinary paths.
