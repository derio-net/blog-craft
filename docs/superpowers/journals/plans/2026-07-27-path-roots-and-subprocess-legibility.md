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
