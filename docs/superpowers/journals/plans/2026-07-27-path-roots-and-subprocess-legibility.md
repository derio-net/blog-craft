# Journal: 2026-07-27-path-roots-and-subprocess-legibility

<!-- fr:journal kind=discovery scope=plan id=p1-four-sites created=2026-07-27T16:04:45 phase=1 -->
### p1-four-sites · discovery · The relative-path break has four sites, not one (phase 1)

Audited every path argument threaded into a subprocess. update.py's --config (reported) and base_by_rerender's config, PLUS reproduce.py's own --config and --scratch, all resolve after bootstrap-render.sh's internal cd. The last two are unreported in #59 and would have survived a fix scoped to the issue text.

<!-- fr:journal kind=discovery scope=plan id=p1-verified-on-frank created=2026-07-27T16:04:45 phase=1 -->
### p1-verified-on-frank · discovery · #59 verified fixed against the real blog (phase 1)

Ran the documented invocation from /home/claude/repos/frank (site_dir: blog, the blog the issues were filed from): previously a CalledProcessError traceback, now prints an 8-line plan. Note .github/** does NOT appear in that plan — the stale blog/.github/workflows/blog-ci.yml is byte-identical to the staged render, which is exactly why the inert file has never drawn attention.
