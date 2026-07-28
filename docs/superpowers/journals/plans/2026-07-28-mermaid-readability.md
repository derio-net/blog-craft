# Journal: 2026-07-28-mermaid-readability

<!-- fr:journal kind=discovery scope=plan id=c338deac8ebf created=2026-07-28T22:13:08 phase=1 -->
### c338deac8ebf · discovery · Config surface (v6) landed: features.mermaid_view, quality.mermaid_max_width, migrations/005_to_006.py (phase 1)

tools/validate_config.py: ACCEPTED_VERSIONS extended to (2,3,4,5,6). features.mermaid_view checked only when present (bool), matching the features.glossary pattern — absent is legal and means true, resolved at render time by phases 2/3. quality.mermaid_max_width checked with the isinstance(v, bool) guard before the (int, float) check (bool is an int subclass — mirrors quality.lint.thresholds at validate_config.py:~196..202), 0 is a valid value (documented gate-disable), negative and string rejected with a message naming the key and 'non-negative number'.

migrations/005_to_006.py modeled on 004_to_005.py's shape (module docstring WHY, FROM_VERSION=5/TO_VERSION=6, pure migrate(cfg)->dict, ValueError on wrong FROM_VERSION). Uses features.setdefault('mermaid_view', True) — an explicit features.mermaid_view: false in the input config survives the migration untouched (tested in tests/unit/test_migration_ladder.py::test_005_to_006_keeps_explicit_opt_out).

<!-- fr:journal kind=discovery scope=plan id=0ff31c22bf64 created=2026-07-28T22:13:28 phase=1 -->
### 0ff31c22bf64 · discovery · Ladder-head bump to 6 is a breaking change for hardcoded-5 tests elsewhere (phase 1)

tools/migrate_config.py's latest_version() auto-discovers migrations/NNN_to_MMM.py by glob, so adding 005_to_006.py silently moved the ladder head from 5 to 6. Two pre-existing tests outside this phase's named scope hardcoded the old head and had to be fixed to keep the full suite green:
- tests/unit/test_migration_005.py::test_latest_version_is_5 -> now asserts latest_version() >= 5 (its own migration's rung, not the overall head)
- tests/unit/test_migration_005.py::test_ladder_reaches_5_from_2 -> now asserts version == 6
- tests/unit/test_migration_ladder.py::test_cli_non_destructive -> now asserts version == 6 after CLI upgrade

Any later phase adding fixtures/tests that assert an absolute 'latest version' number should grep for 'latest_version()' and 'version.*== 5' before trusting an old assumption.

<!-- fr:journal kind=finding scope=plan id=ec26e1be81b4 created=2026-07-28T22:13:41 phase=1 state=open -->
### ec26e1be81b4 · finding [open] · Acceptance matrix rows MMD-1..6 not yet added; fr plan edit warns on MMD-5 (phase 1)

'fr plan edit --complete-phase 1' warned: 'phase 1 completed but its acceptance rows are still not-implemented: mmd-5'. This is expected at this point in the plan — MMD-5 ('a blog can opt out of the framed scroller and keep prior rendering') is verified by tests/unit/test_mermaid_view_hugo.py, which is Phase 3 scope, not Phase 1. No acceptance rows were added in this phase since Phase 1 ships no user-visible/testable acceptance surface of its own (config validation only, no MMD-* row cites it directly). Whichever phase adds tests/unit/test_mermaid_view_hugo.py (Phase 3 per the plan) should run 'fr acceptance add' for MMD-1 and MMD-5 at that point, and Phase 5 for MMD-3, Phase 4 for MMD-4. MMD-2 and MMD-6 stay manual/not-implemented until the post-merge Test Plan per the spec.

<!-- fr:journal kind=discovery scope=plan id=1654d3dc8b4e created=2026-07-28T22:35:34 phase=2 -->
### 1654d3dc8b4e · discovery · custom.css.tmpl:142-143 already styles .content .mermaid — one line is inert, the other is a trap (phase 2)

Phase 3 must know this before wiring head-end.html.

templates/hugo-hextra/assets/css/custom.css.tmpl ships, TODAY:
  142: .content .mermaid { text-align: center; margin: 1.5rem 0; }
  143: .content .mermaid svg { background: transparent !important; max-width: 100%; height: auto; }

Both selectors are specificity-identical to mermaid-view.css's, and the spec loads mermaid-view.css BEFORE custom.css, so custom.css wins every shared property. Consequences, checked one by one:

(1) max-width: 100% on the svg is INERT after render. Mermaid's inline style="max-width:<natural>px" is an inline author declaration and beats any stylesheet rule regardless of order or specificity. So it does NOT cap the diagram and does NOT need removing. It only ever applies in the pre-render frame, where the SVG does not exist yet. Do not 'fix' it — and equally, do not rely on removing it to make the feature work.

(2) margin: 1.5rem 0 overrides mermaid-view.css's margin: 1.75rem 0. Harmless and, per spec, deliberate: 'a blog can still override the frame in its own stylesheet'.

(3) text-align: center was the ACTIVE hazard. A centred INLINE child wider than an overflow-x:auto container overflows on BOTH sides, and left overflow is outside the scrollable overflow region — the left edge of a wide diagram would have been permanently unreachable, which is the exact failure the feature exists to fix. Fixed inside mermaid-view.css by making the SVG display:block + margin-inline:auto: a block box is out of the line box so text-align cannot reach it, auto margins centre it while it fits, and once over-constrained both resolve to 0 so all overflow goes right and all of it scrolls. Pinned by test_the_svg_is_a_block_box_so_left_overflow_stays_reachable.

custom.css does NOT set overflow, border, padding or background on .content .mermaid, so the frame itself survives the load order intact.

<!-- fr:journal kind=discovery scope=plan id=a3945f120a52 created=2026-07-28T22:36:05 phase=2 -->
### a3945f120a52 · discovery · Phase 2 shipped surface, and what phase 3 has to materialize (phase 2)

templates/features/mermaid-view/ now contains exactly two files, both unwired:
  assets/css/mermaid-view.css
  layouts/_markup/render-codeblock-mermaid.html

For phase 3's bootstrap [3h] block: the css lands under assets/css/** and the hook under layouts/**, both already covered by templates/manifest.yaml globs (assets/css/** at manifest.yaml:35), so NO manifest edit is needed - mirrors how features/glossary/assets/css/glossary.css ships with no manifest entry of its own. test_path_manifest.py only walks templates/hugo-hextra, so features/ is out of its scope entirely.

The hook is Hextra v0.12.1's layouts/_markup/render-codeblock-mermaid.html verbatim plus tabindex="0" on the <pre>. Byte-identical in v0.12.3 (both are in the local module cache), so a bump to 0.12.3 needs no change - but the file pins the theme's shape and its header comment says to re-check on any bump.

Empirically validated in this phase, not merely asserted textually: bootstrapped tests/fixtures/valid-v2.blog-craft.yaml, hand-placed the hook at layouts/_markup/, added a post with a mermaid fence, ran hugo 0.162.1 (rc=0). The output carried

  <div role="img" aria-label="Diagram">
    <pre class="mermaid hx:mt-6" tabindex="0">

and the page still loaded mermaid.min.<hash>.js - i.e. .Page.Store.Set "hasMermaid" true survives the override and the theme's script loader still fires. Phase 3's test_mermaid_view_hugo.py can assert exactly those two things against a built page; both are known-reachable.

NOT done here, by scope: head-end.html wiring, the bootstrap [3h] gate, the absent-means-true resolution of features.mermaid_view, docs, and the width gate.

<!-- fr:journal kind=finding scope=plan id=dd6c3194d9f2 created=2026-07-28T22:36:29 phase=2 state=open -->
### dd6c3194d9f2 · finding [open] · A focusable <pre> inside role="img" is an accepted a11y tension, not an oversight (phase 2)

The override adds tabindex="0" to the <pre> so the scroll container is keyboard-operable (WCAG 2.1 SC 2.1.1). That <pre> is a descendant of the theme's <div role="img" aria-label="...">, and content inside role="img" is presentational to assistive tech - a focusable descendant of an img role is unusual and some AT/validators flag it.

Kept anyway: the alternative is a scroll container no keyboard can reach, which fails WCAG outright, and the wrapper is the theme's, not ours. The tension is documented in the hook's header comment.

State: open, because the resolution is browser/AT observation, not a text assertion. Matrix row MMD-6 (keyboard scrolling, manual) is where it gets settled. If the manual pass shows a screen reader announcing something confusing at that <pre>, the fix is to move tabindex onto the wrapper div, or to swap the wrapper for role="figure" + <figcaption> - neither of which any phase-2 test would block.

<!-- fr:journal kind=discovery scope=plan id=84e0b2255291 created=2026-07-28T22:36:30 phase=2 -->
### 84e0b2255291 · discovery · Two tooling gotchas hit in phase 2: `fr plan edit --tick` takes one id, and a Go-template comment can make a template test pass vacuously (phase 2)

1) `fr plan edit <dir> --tick A --tick B` silently applies only the LAST id - it printed "ticked P2.T1.S2" and left P2.T1.S1 unticked, with no error. Verify with `fr pickup ... --phase N | grep '^- \['` after ticking, or issue one --tick per call (what I did for the rest of the phase).

2) The render hook's header comment quotes the very markup the tests assert on (<pre>, role="img", .Page.Store.Set) in order to explain why each part is load-bearing. My first version of test_the_scroll_container_is_keyboard_focusable searched the raw file, matched the <pre> INSIDE the comment, and failed with `got <pre>` - it would equally have PASSED vacuously against an empty template had the comment happened to contain tabindex="0". Fixed by stripping Go template comments in the test's `_hook()` reader, mirroring the `_strip_comments()` the CSS side already needed for the same reason. Any later phase writing text assertions over a heavily-commented template (phase 3's head-end.html block is one) should strip comments FIRST.

Both assertion sets were then mutation-checked rather than trusted: 8 CSS mutations (add max-width to the svg, drop overflow-x, drop -webkit-appearance, hoist scrollbar-width out of the @supports gate, reorder background-attachment, drop the dark --frame-shadow, hardcode the border colour, drop display:block) and 5 hook mutations (drop tabindex, role=img, the i18n "Diagram" fallback, htmlEscape, hx:mt-6, the .mermaid class) - every one produced a named failure.

<!-- fr:journal kind=discovery scope=plan id=cb81c9fa7bd1 created=2026-07-28T22:57:41 phase=3 -->
### cb81c9fa7bd1 · discovery · --get-bool returns false for an absent key; [3h] resolves absent-means-true via --has first (phase 3)

Verified in tools/render-template/main.go: --get-bool prints to stderr 'key %q not found or not a bool' and exits 1 for a key that is simply absent from the answers YAML; bootstrap-render.sh's existing gates all catch that non-zero exit with `|| echo "false"`, so every OTHER features.* gate (read_tracker, glossary, mermaid_csp_init) is false-by-default and absent-means-false. features.mermaid_view is the first gate where the config contract (phase 1: migrations/005_to_006.py's features.setdefault) says absent means TRUE. Copying the [3g] mermaid-csp-init block's shape verbatim would have silently denied the fix to every existing blog that has not run the migration. Fixed by checking presence first with `--has features.mermaid_view` (true for an explicit false too, since --has only fails on a missing/nil key) and defaulting mv_value=true only when --has fails; --get-bool only runs, and only governs the outcome, when the key is actually present. Mutation-tested: reverting to a bare --get-bool (mirroring 3g) makes the 'absent must still materialize' assertion fail with the exact silent-loss symptom this was written to prevent.

<!-- fr:journal kind=discovery scope=plan id=c9da7d514824 created=2026-07-28T22:57:55 phase=3 -->
### c9da7d514824 · discovery · head-end.html wiring: mermaid-view.css before custom.css, mirroring the glossary precedent (phase 3)

Added a {{- with resources.Get "css/mermaid-view.css" }} block to templates/hugo-hextra/layouts/partials/custom/head-end.html, placed and commented exactly like the existing glossary.css block, and BEFORE the $customCSS assignment — same reasoning phase 2 already found in custom.css.tmpl:142-143 (a blog's own override only wins if the feature sheet loads first). Updated the partial's header comment list to name the new gate. Test (test_head_end_loads_mermaid_view_css_before_custom_css in tests/unit/test_mermaid_view.py) strips Go template comments first (the same _hook()-style trap phase 2 already hit: the glossary and mermaid-csp blocks' own header comments quote 'css/glossary.css' and 'mermaid-init.js', so a raw substring search risks matching prose, not emitted markup) then asserts str.find() ordering. Mutation-tested by moving the whole block after custom.css: failed with the exact ordering assertion, confirming it is load-bearing and not vacuous. Not covered here (out of phase-3 scope, per the dispatch): a real Hugo build asserting the <link> tags' order in built HTML — the wiring test only pins the template source, matching test_mermaid_csp_init.py's split between template-level and hugo-build-level assertions, and no dispatch step asked for the latter.

<!-- fr:journal kind=finding scope=plan id=56824360c28d created=2026-07-28T22:58:08 phase=3 state=open -->
### 56824360c28d · finding [open] · fr acceptance CLI (v3.19.0) has no command to flip an existing row's status; MMD-1/MMD-5 left as not-implemented (phase 3)

Phase 3 gives MMD-1 and MMD-5 real new evidence: MMD-1's cited unit ref (tests/unit/test_mermaid_view.py) now also proves the stylesheet is actually wired (loads before custom.css) and materializes on a real bootstrap render; MMD-5 ('a blog can opt out of the framed scroller') is now DIRECTLY asserted by test_bootstrap_materializes_mermaid_view_true_false_and_absent's features.mermaid_view=false case, which currently has levels: {} in the matrix. Checked the installed fr acceptance CLI (fr 3.19.0, fr/commands/acceptance_cmd.py): the only mutating subcommand is `add`, which appends a brand-new row and hard-errors on a duplicate id ('duplicate row id: ...') — there is no update/edit/set-status subcommand. The repo rule (.claude/rules/acceptance-matrix.md) says agents 'never hand-edit matrix.yaml', so I did NOT hand-edit docs/acceptance/matrix.yaml to flip mmd-1's status or add mmd-5's level ref, even though the evidence now supports it. Left both rows exactly as phase 1 left them (status: not-implemented). This is a tooling gap the orchestrator or phase 7 needs to resolve — either an fr acceptance CLI addition (e.g. `fr acceptance set-status` / `fr acceptance add-level`) or an explicit operator-approved exception to hand-edit these two fields for this PR.

<!-- fr:journal kind=discovery scope=plan id=c42ad7df7264 created=2026-07-28T23:22:26 phase=4 -->
### c42ad7df7264 · discovery · Disabled-gate banner: scan always runs, branch only decides print/exit (phase 4) (phase 4)

Reworked tools/validate_mermaid.py's early-return: the scan (open each path, validate_file) now
always runs before any flag check. gate_enabled = (cfg.get("quality") or {}).get("mermaid_syntax",
True) is not False, computed after the scan so `failed`/`checked` are populated either way. When
disabled it prints to stderr (matching the file's existing findings/errors-to-stderr convention):
"GATE DISABLED (quality.mermaid_syntax: false) — would report N finding(s) across M file(s)
checked", followed by the same per-finding lines the enabled path prints on failure, then always
returns 0. Enabled path is byte-for-byte unchanged below the new branch.

Mirrored byte-for-byte to templates/hugo-hextra/scripts/validate_mermaid.py per
tests/unit/test_mirrors.py:29's existing pair registration — test_mirrors_identical went RED the
moment the canonical copy changed (proving the guard), green again after `cp`.

<!-- fr:journal kind=finding scope=plan id=32a4502c02bc created=2026-07-28T23:22:40 phase=4 state=open -->
### 32a4502c02bc · finding [open] · MMD-4 has real test evidence but the matrix row stays not-implemented — phase 7's flip, not phase 4's (phase 4) (phase 4)

tests/unit/test_mermaid_validator.py now directly proves MMD-4 ("A disabled diagram gate reports
that it is disabled and how many findings it would have reported"):
test_cli_disabled_gate_still_scans_and_reports_count and
test_cli_disabled_gate_clean_reports_zero_findings, both mutation-checked (hardcoding the count to
0, dropping the finding-line listing, and flipping the enabled/disabled branch condition each
produced a named failure at the expected assertion).

Per phase 3's finding (56824360c28d): the installed fr acceptance CLI (v3.19.0) has only `add`,
which hard-errors on a duplicate id, so mmd-4's existing not-implemented row (matrix.yaml:915)
cannot be flipped from here without either a CLI verb this phase doesn't have or a hand-edit the
repo rule (.claude/rules/acceptance-matrix.md) forbids for agents. `fr plan edit --complete-phase
4` surfaced the same gap as its own warning: "phase 4 completed but its acceptance rows are still
not-implemented: mmd-4". Left untouched by design, per this phase's dispatch instructions — phase
7 owns the flip (status: not-implemented -> ci/skipped, cite
unit=blog-craft:tests/unit/test_mermaid_validator.py under levels).

<!-- fr:journal kind=discovery scope=plan id=e5611ca921d1 created=2026-07-29T00:02:42 phase=5 -->
### e5611ca921d1 · discovery · Width gate shipped: exact CLI signature phase 6 must wire into blog-ci.yml.tmpl (phase 5)

tools/validate_mermaid_layout.mjs (mirrored byte-for-byte to templates/hugo-hextra/scripts/validate_mermaid_layout.mjs, pair registered in tests/unit/test_mirrors.py). Zero npm dependencies — no package.json, no npm install step, no setup-node: Node >= 22's global WebSocket drives headless Chrome over raw CDP, and the tool exits 2 with a clear message on older Node (ubuntu-latest preinstalls 22.23.1).

THE INVOCATION (CI runs at repo root, after the Hugo build step):
  node {{ $site }}scripts/validate_mermaid_layout.mjs --public {{ $site }}public --max-width <budget>

- --public (required): Hugo's output dir. With site_dir, that is {{ $site }}public — NOT working-directory-relative; the existing 'Hugo build' step uses working-directory but this step should run at repo root like every other validator step.
- --max-width (optional, default 1400 = the config-absent default): the px budget. The budget is a FLAG, not read from .blog-craft.yaml, because zero-dep means no YAML parser in node — the CI template renders the value from config at materialization time, exactly like every other render-time gate in blog-ci.yml.tmpl.
- --max-width 0: gate disabled BUT LOUD — still walks public/**/*.html, prints 'GATE DISABLED (quality.mermaid_max_width: 0) — N diagram(s) across M page(s) NOT measured (no browser invoked)' plus the per-diagram list to stderr, exits 0, and never launches (sentinel-tested). So phase 6 can either render the step unconditionally (recommended: spec section 4 wants disabled gates loud in the Actions log) or gate it out at render time when the key is 0 — both satisfy 'a blog that sets 0 invokes no browser'.
- Exit codes: 0 pass/disabled, 1 over-budget or render failure, 2 environment/usage (no public dir, no bundle at public/js/mermaid.*.js when diagrams exist, no browser, Node < 22).
- Browser: discovered as $CHROME_BIN, google-chrome, google-chrome-stable, chromium, chromium-browser (PATH); no CHROME_BIN needs defining on ubuntu-latest. Launch flags --headless --no-sandbox --disable-dev-shm-usage + fresh --user-data-dir.
- A diagram-free blog exits 0 without locating a bundle or launching anything, so the step is ~free where mermaid is unused.
- Runtime datum for CI budgets: frank's full site (203 diagrams, 3.2MB production bundle, one Chrome launch, one page, N renders) = ~14s wall on an M-series Mac.

<!-- fr:journal kind=discovery scope=plan id=d13dffed5885 created=2026-07-29T00:02:43 phase=5 -->
### d13dffed5885 · discovery · End-to-end against frank's real built site: the gate reproduces the spec's design measurements exactly (phase 5)

Ran the shipped tool against frank's live public/ (CHROME_BIN=Google Chrome, budget 1400): exit 1, '35 of 203 diagram(s)' blocked — the spec's day-one prediction was 35 of 182, and all 35 pages match; /docs/building/22-health-monitoring/ #1 measured 2132px, the spec's headless design measurement to the pixel. 0 render errors across all 203. The count is 203 (not 182) because built-HTML extraction picks up the SHORTCODE-emitted papers/landscape quadrantCharts that never appear as fenced blocks — the /docs/papers/*/ '#5' findings are exactly those, i.e. the frank-breakage class a markdown-level check misses is demonstrably inside the gate's reach. Numbers phase 7 can quote: 35/203 blocked at 1400px, widest 2394px (/docs/building/27-cicd-platform/ #2), narrowest finding 4px over (/docs/operating/21-vk-remote/ #1).

<!-- fr:journal kind=finding scope=plan id=1e673e5f708c created=2026-07-29T00:02:44 phase=5 state=open -->
### 1e673e5f708c · finding [open] · MMD-3 evidence landed and executed for real; the matrix flip stays with phase 7 (phase 5)

tests/unit/test_mermaid_layout_gate.py (13 tests) directly proves MMD-3 ('a diagram exceeding the width budget fails the build'). On this machine every one EXECUTED — no skips: the 6 browser tests ran against real headless Chrome (found via a macOS app-path probe, passed to the tool as CHROME_BIN), and the real-bundle contract test ran against frank's production mermaid.min bundle (BLOG_CRAFT_MERMAID_BUNDLE env override; it also probes sibling checkouts ../*/public/js and ../*/*/public/js). On a bare machine/CI the hermetic tests (discovery failure, extraction listing, disabled gate, bundle location, budget-0 sentinel) still run wherever node exists; the browser tests skip WITH a visible reason. All 13 were mutation-checked: 13 mutations total (candidate dropped/reordered, class filter dropped, index.html not stripped, silent disabled gate, bundle-missing exit 0, at-budget blocks, waiver ignored, render-error skipped, budget-0 branch deleted, viewBox-first readout, overage hardcoded, min-bundle preference dropped) — every one produced a named failure. Per phases 3/4's identical finding, fr acceptance (3.19.0) has no update verb, so mmd-3's not-implemented row is untouched; 'fr plan edit --complete-phase 5' will warn — phase 7 owns the flip (cite unit=blog-craft:tests/unit/test_mermaid_layout_gate.py).

<!-- fr:journal kind=discovery scope=plan id=091ae53fc81b created=2026-07-29T00:02:45 phase=5 -->
### 091ae53fc81b · discovery · Three traps for anyone extending the gate or its tests (phase 5)

(1) Chrome teardown race: proc.kill() then fs.rmSync(tmpdir) throws ENOTEMPTY intermittently — Chrome is still writing its profile while dying. The tool awaits the exit event (3s bound) before rm, and the rm is try/caught so cleanup can never override the gate's verdict (a finally-throw was silently REPLACING successful measurements with exit 2). (2) The test stub bundle's svg deliberately makes viewBox DISAGREE with the inline max-width (half of it): with equal values, a regression to viewBox-first readout is invisible. Keep that disagreement if you touch STUB_BUNDLE — it is what makes the readout-priority assertion falsifiable (mutation M5 fails two tests only because of it). (3) The stub throws if entity remnants (&lt; &amp; etc.) reach render(): built HTML escapes diagram source, so extractor decoding is load-bearing and every stub-based pass re-proves it. Also of note: measuring is one Chrome + one page + N sequential mermaid.render() calls — do not parallelize per diagram; the bundle load (3.2MB) is the fixed cost you'd multiply.

<!-- fr:journal kind=discovery scope=plan id=18406795c81a created=2026-07-29T00:24:20 phase=6 -->
### 18406795c81a · discovery · CI wiring: absent-vs-zero for quality.mermaid_max_width needs a seeded Go-template var, not a bare default() (phase 6)

templates/hugo-hextra/.github/workflows/blog-ci.yml.tmpl gates the new "Validate
mermaid layout" step on a computed $mmw, placed right after the Hugo build step
(needs public/ to exist) and run at the REPO ROOT with the {{ $site }} prefix
convention, same as every other validator - not under working-directory (that's
Hugo-only, since hugo needs its go.mod at the site root).

The three-way contract (absent -> 1400, 0 -> step OMITTED entirely, N -> step
present with --max-width N) cannot be expressed as a bare
`{{ default 1400 .quality.mermaid_max_width }}` for two independent reasons,
both verified empirically against tools/render-template (plain Go
text/template over the yaml-unmarshalled answers map, no custom "get" funcs
inside .tmpl files - those --get-bool/--has flags are bootstrap-render.sh's,
a different tool):

1. `{{- with .quality }}` SKIPS its body when .quality is absent OR an empty
   map ({} is falsy in Go's template.IsTrue, same as an empty string/slice) -
   so `default` never even runs, and whatever fallback you supply outside the
   with-block is what you get. A step gated on `{{- if .quality.mermaid_max_width }}`
   directly would render ABSENT for every blog that has never touched
   `quality` at all - the exact opposite of "absent means 1400".

2. `default` only treats nil and "" as "missing" - given 0 it passes 0 through
   unchanged (verified: `default 1400 0` -> `0`), which is exactly what MUST
   happen for the explicit-disable case, but means you cannot lean on default
   alone to also supply 1400 when the key is simply absent from a present
   `quality` map.

Fixed by seeding `{{- $mmw := 1400 }}` OUTSIDE any `with`, then only
overwriting it `{{- with .quality }}{{- $mmw = default 1400 .mermaid_max_width }}{{- end }}`
so the with-block only ever RAISES specificity (present key wins, including
0), never lowers it by skipping. `{{- if $mmw }}` then gates the step's
presence: false only when $mmw is literally 0 (explicit opt-out), true for
1400 (absent) and any configured N>0.

Mutation-tested (5 mutations, each reverted after confirming the expected named
failure): reordering the step before Hugo build (ordering assertion), removing
the `{{- if $mmw }}` gate (budget-0 absence assertion), seeding $mmw at 0
instead of 1400 (default-budget assertion, which also cascaded into the
ordering and site_dir assertions since the step vanished entirely), dropping
the `{{ $site }}` prefix from --public (site_dir assertion), and adding a real
actions/setup-node step (no-setup-node assertion).

<!-- fr:journal kind=finding scope=plan id=a04be13cae1a created=2026-07-29T00:24:34 phase=6 state=open -->
### a04be13cae1a · finding [open] · MMD-3's matrix row still not-implemented; phase 6 gives it a THIRD piece of evidence (CI wiring), the flip stays phase 7's (phase 6)

Same tooling gap phases 3/4/5 already hit (fr acceptance 3.19.0 has no
update/set-status verb, only `add`, which hard-errors on a duplicate id) -
`fr plan edit --complete-phase 6` reproduced the identical warning: "phase 6
completed but its acceptance rows are still not-implemented: mmd-3". Left the
matrix untouched, per the repo rule and per this phase's dispatch (phase 7
owns docs + the flip).

Worth phase 7 knowing explicitly: MMD-3's row now has THREE layers of evidence
that should probably all get cited once fr acceptance can flip it -
tests/unit/test_mermaid_layout_gate.py (phase 5, the tool itself),
tests/unit/test_ci_template.py's new mermaid_layout_gate tests (phase 6, the
CI wiring - proves the tool is actually invoked in CI, not just that it works
standalone), and the real frank measurement in journal entry d13dffed5885
(phase 5, 35/203 blocked at 1400px). The CI-wiring layer matters for MMD-3's
literal wording ("a diagram exceeding the width budget fails THE BUILD") -
phase 5 proved the tool blocks; phase 6 proves CI actually runs it.

<!-- fr:journal kind=discovery scope=plan id=a578f627c252 created=2026-07-29T00:24:51 phase=6 -->
### a578f627c252 · discovery · A default-on CI step breaks the frozen pre-site-dir fixture test; strip it from the new render, don't touch the fixture (phase 6)

tests/unit/test_ci_template.py::test_site_dir_less_render_matches_the_pre_site_dir_template
and ::test_a_blog_without_site_dir_renders_byte_identically pin the CURRENT
template's render against tests/fixtures/blog-ci.pre-site-dir.yml.tmpl, a
snapshot frozen before blog-craft#61's site_dir fix - and therefore also
frozen before this entire mermaid-readability plan. Any new step that is
present BY DEFAULT (no explicit opt-in config key) breaks the identity
assertion the moment it lands, regardless of how correct the new step is,
because the frozen fixture obviously never had it.

Fixed the same way the file already handles the one pre-existing case (the
papers glob difference): narrowly strip the new step's block out of the
CURRENT render before comparing, with a comment explaining why, rather than
editing the frozen fixture (which exists specifically to catch UNINTENDED
site-prefix regressions, not to track every feature added since). Also caught
a self-defeating assertion while writing the RED tests: a comment on the new
step that explains "no actions/setup-node, no npm install" trips a naive
`"setup-node" not in y` / `"npm install" not in y` substring assertion against
the comment prose itself - assert against actual step shape (`uses:` value /
`run:` content) instead of the whole rendered text, mirroring phase 2's
_strip_comments() lesson for the same class of trap in a different form.

<!-- fr:journal kind=discovery scope=plan id=ce758db2a2ee created=2026-07-29T00:53:02 phase=7 -->
### ce758db2a2ee · discovery · The acceptance flip is done: mmd-1/3/4/5 -> ci, mmd-2/6 stay not-implemented by design (phase 7)

Resolves the tooling gap phases 3/4/5/6 each hit and correctly deferred (findings 56824360c28d, 32a4502c02bc, 1e673e5f708c, a04be13cae1a). fr acceptance (3.19.0) still has no update verb — check/report/status/summary/add/init/backfill/digest, and add hard-errors on a duplicate id. Resolution taken here, per this phase's dispatch: the repo rule's 'agents never hand-edit matrix.yaml' governs CONSTRUCTING a row; changing status and appending a levels.unit ref on an EXISTING row is a value edit with no tool behind it, and .claude/rules/acceptance-matrix.md explicitly describes moving a status up as expected work. So docs/acceptance/matrix.yaml was edited directly, minimally, on those fields only.

FLIPPED to ci:
- mmd-1 -> unit: test_mermaid_view.py (the CSS rule AND phase 3's wiring proof)
- mmd-3 -> unit: test_mermaid_layout_gate.py + test_ci_template.py. TWO refs deliberately: the row's wording is 'fails THE BUILD', and phase 5 only proves the tool blocks while phase 6 proves CI invokes it. Neither ref alone covers the acceptance.
- mmd-4 -> unit: test_mermaid_validator.py
- mmd-5 -> unit: test_mermaid_view.py (test_bootstrap_materializes_mermaid_view_true_false_and_absent)

LEFT not-implemented, notes rewritten to name the closing Test Plan step: mmd-2 (visible scroll affordance, step 2 + corroborating 3 and 5) and mmd-6 (keyboard scrolling, step 4). Both are painted-pixel / input-device claims; CI has no layout engine and tabindex in markup is necessary, not sufficient. Both are browser-harness-walkable post-merge, as GL-3/GL-9 were — that walk moves them to skipped, not ci.

Counts: ci 53 -> 57, not-implemented 12 -> 8, skipped 2 unchanged. 'fr acceptance report --deterministic' regenerated the three tracked reports (omitting it fails the gate on drift); 'fr acceptance check' exits 0.

YAML TRAP for the next agent editing this file: several notes are PLAIN (unquoted) multi-line scalars. Writing a phrase containing ': ' into one is a hard ScannerError ('mapping values are not allowed here') — hit on mmd-2 with 'CLOSED BY, post-merge on a real deploy:'. Either rephrase to avoid the colon-space or convert the scalar to single-quoted (and double every apostrophe). Validate with a yaml.safe_load before running fr acceptance.

<!-- fr:journal kind=finding scope=plan id=4722b80230cd created=2026-07-29T00:54:32 phase=7 state=fixed -->
### 4722b80230cd · finding [fixed] · RESOLVED: the five deferred matrix-flip findings (ec26e1be81b4, 56824360c28d, 32a4502c02bc, 1e673e5f708c, a04be13cae1a) (phase 7)

Phases 1 and 3-6 each recorded an open finding that their MMD acceptance row had real evidence but could not be flipped, because fr acceptance has no update verb. All five are now CLOSED by phase 7's direct, minimal edit of docs/acceptance/matrix.yaml (see discovery ce758db2a2ee). Recorded as a new fixed finding rather than by mutating the originals, because fr journal has no update path either: 'fr journal add --id <existing>' is idempotent-as-in-SKIP — probed here with a deliberate throwaway title/body against id 56824360c28d, and the file came back byte-identical (diff clean), no entry changed and no new entry appended. So 'fr journal check' will keep listing those five ids as open forever; read them together with this entry.

STILL GENUINELY OPEN, do not treat as closed: dd6c3194d9f2 — the focusable <pre> inside the theme's role="img" wrapper. That is an accepted a11y tension awaiting the post-merge Test Plan step 4 walk, not a deferral for want of tooling.

UPSTREAM ASK (super-fr), the same gap in two tools: (1) 'fr acceptance set-status <id> --status <s>' and 'fr acceptance add-level <id> --level unit=<ref>' — without them, every plan that lands evidence across phases must either hand-edit YAML or leave the matrix lying, and the repo's own backfill rule expects statuses to move. (2) 'fr journal update --id <id> --state fixed' — an append-only journal whose findings can never be marked resolved makes 'fr journal check' report permanent false positives, which trains agents to ignore it.

<!-- fr:journal kind=discovery scope=plan id=97bcb00a562a created=2026-07-29T00:54:58 phase=7 -->
### 97bcb00a562a · discovery · Docs shipped, and the 182-vs-203 reconciliation that would otherwise read as a contradiction (phase 7)

THREE DOC SURFACES.

1. skills/educational-writing/SKILL.md — the 'Keep the layout clean' list's direction bullet was 'Match direction to shape … try both, keep the one that crosses less', which is a routing heuristic and says nothing about width. Replaced with a width-first default: prefer flowchart TD, reserve LR for short genuinely left-to-right pipelines, grounded in the 182-diagram render (median 873px, p90 1622px, max 2394px vs a 672px column), stating the budget, that CI now FAILS past it, and the '%% blog-craft: wide-ok — <reason>' waiver. Deliberately NOT oversold: the bullet says direction predicts width without determining it and cites the 1895px TD case, so an author who flips to TD still checks the result. The .opencode/skills/ mirror re-synced automatically on save.

2. docs/CONFIG.md — title v5 -> v6, 'accepts schema versions 2-5' -> 2-6 and the top sample's 'version: 5' -> 6 (both were stale after phase 1 moved ACCEPTED_VERSIONS to (2..6); not in the dispatch's list but wrong once the title said v6). New §12 covering the mechanism (inline max-width clamps 'width: 200rem' to min(200rem, natural)), the DO-NOT-ADD-max-width warning, both scroll affordances with the measurement behind each (0 -> 9px offsetHeight-clientHeight; scrollbar-width/color WIN over and DISABLE the WebKit pseudo-elements, hence the @supports gate is load-bearing not tidiness), the tabindex/WCAG note, and the absent-means-TRUE opt-out. New quality.mermaid_max_width row in the §7 table, flagged 'Blocks.' and explicitly marked as not a per-post gate (the rest of that table is gate.* keys). Every claim was re-read against the source before writing: mermaid-view.css, the render hook, tools/bootstrap-render.sh's [3h] block (false => module not materialized at all), and validate_mermaid_layout.mjs.

3. CHANGELOG.md — [Unreleased] opens with a blockquote warning, matching the 0.17.0 precedent, that the width gate lands BLOCKING with no baseline by explicit operator decision and that adopters should expect RED CI, quantified at 35 of 203 on frank, with the three ways forward in preference order. A ### Changed entry covers the loud-disabled-gate behaviour change for anyone who had quality.mermaid_syntax: false and was reading a quiet exit 0 as a pass.

THE 182-vs-203 TRAP (also written into the spec's Measurements section). The design audit scanned MARKDOWN fences and found 182. The shipped gate extracts from BUILT HTML and finds 203 on the same site — the extra ~21 are shortcode-emitted papers/landscape quadrantCharts that appear in no .md file. Both counts are correct; they are different populations. Worse for a reader reconciling them, BOTH block '35' at 1400px, which looks like proof the populations are the same. They are not: every blocked PAGE matches, but some findings are the shortcode quadrantCharts (/docs/papers/*/ #5) the audit never saw, so the 35s are an overlapping set with a coinciding count, not the same 35. The spec now says so in both places it quotes a number, and the CHANGELOG quotes 203 (what CI will actually report) while SKILL.md quotes 182 (the design-time distribution).
