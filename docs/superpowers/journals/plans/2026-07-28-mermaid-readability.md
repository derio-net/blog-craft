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
