# Journal: 2026-07-26-abbreviation-glossary

<!-- fr:journal kind=decision scope=spec id=d1-mechanism created=2026-07-26T00:04:35 -->
### d1-mechanism · decision · Authored shortcode, not runtime DOM annotation

Operator chose the `{{< abbr "NUT" >}}` shortcode inserted into post markdown by the skill, over client-side JS that wraps known terms in the rendered DOM. Rationale: deterministic rendered HTML, reviewable in the git diff, verifiable by a CI validator, and a teaching blog cannot afford false-positive matches inside prose. Cost accepted: scanning a whole series produces a large (reviewable) diff across post files.

<!-- fr:journal kind=decision scope=spec id=d2-interaction created=2026-07-26T00:04:38 -->
### d2-interaction · decision · Native HTML Popover API — zero JavaScript

Trigger is a `<button popovertarget>` wrapping an `<abbr title>`; the panel is a `<span popover>`. Click/tap opens, Esc and click-away close, keyboard focusable, top-layer positioned — all native, no JS asset. Rejected: JS hover-tooltip + click-popup (real dependency, hand-written focus management, mobile hover special-casing) and bare `<abbr title>` (hover-only, invisible on touch — does not satisfy 'an element the user can click').

<!-- fr:journal kind=decision scope=spec id=d3-term-scope created=2026-07-26T00:04:41 -->
### d3-term-scope · decision · Scanner proposes acronyms/initialisms only; manual adds supported

Candidate extraction is limited to capitalized acronyms and initialisms the skill can expand with confidence from the post's own context (NUT, SLO, CDP, OKLCH). Lowercase tool/jargon names (systemd, kubectl, Hextra) are NOT auto-proposed — too noisy — but the operator may hand-add any term to data/glossary.yaml and it renders identically.

<!-- fr:journal kind=decision scope=spec id=d4-index-page created=2026-07-26T00:04:45 -->
### d4-index-page · decision · Ship {{< glossary-index >}} shortcode only; no auto-created page

The feature ships an alphabetical definition-list shortcode the operator drops on a page of their choosing. Bootstrap does NOT write a content/glossary/_index.md — that would place operator-class content on disk that /update can never manage.

<!-- fr:journal kind=decision scope=spec id=d5-models created=2026-07-26T00:04:48 -->
### d5-models · decision · fr model tiers rebound to claude-opus-5

All three claude-code tiers (mechanical/standard/hard) were bound to claude-opus-4-8 in ~/.config/fr/models.yaml while this session runs Opus 5. Operator chose to rebind all tiers to claude-opus-5 globally, so phase-executor subagents match the session model.

<!-- fr:journal kind=review scope=spec id=r1-spec-review created=2026-07-26T00:09:41 -->
### r1-spec-review · review · Spec reviewed against codebase reality — 7 findings fixed

1. Journal path was `journals/spec/`; actual is `journals/specs/` (plural). Fixed.
2. **Dropped the proposed `templates/manifest.yaml` narrowing.** The spec wanted `assets/css/**` split so glossary.css could be framework-class. Verified against `update.py:plan_update`: a merged-class file that does not exist locally yields `add`, and later updates 3-way merge cleanly — so merged is already correct, and it lets an operator's colour tweak survive. read-tracker.js sets the precedent (feature-shipped, covered by the blanket `assets/js/**` rule). Narrowing would have changed /update behaviour for every existing blog's operator-authored CSS to buy nothing.
3. Pinned regex `\b[A-Z][A-Z0-9]{1,9}(?:s|'s)?\b` was subtly wrong (`\b` after an apostrophe). Replaced with a prose rule; exact pattern left to implementation.
4. Stoplist listed `I` and `A`, which the 2-char minimum makes unmatchable — internal contradiction. Replaced with real candidates (OK, TODO, AM, PM, USD…).
5. Added the head-end ordering requirement: glossary.css links BEFORE custom.css so a blog can override at equal specificity.
6. Acceptance rows OC-1/OC-2 hardcode 'all 9 blog-craft skills'; /glossary makes ten. Same PR restates them count-free.
7. Test Plan step 8 told the operator to enable the feature in frank/gondor, contradicting the stated non-goal. Reworded as a scratch-clone verification of the update path.

Verified as existing: features toYaml passthrough in .blog-craft.yaml.tmpl:34, the `with resources.Get` idiom in head-end.html, `:is(html.dark)` in custom.css:83, the CI-template `{{- with .quality }}{{- if .enabled }}` gating idiom, test_features_gating/test_mirrors/test_papers_hugo patterns, tools/media-fill.py as the scan-apply precedent, and pyproject version 0.12.0.

<!-- fr:journal kind=discovery scope=spec id=disc1-hugo-future-flake created=2026-07-26T00:19:49 -->
### disc1-hugo-future-flake · discovery · Pre-existing time-of-day flake in test_explainers_hugo.py (blocks Hugo-render tests)

Baseline on the branch point (docs-only commit off origin/main): 395 passed, 1 FAILED — test_explainers_hugo.py::test_explainers_hugo_build.

Root cause, reproduced by hand: local clock was 00:19 CEST 2026-07-26 = 22:19 UTC 2026-07-25. scaffold-explainer.sh stamps `date:` from the LOCAL date (2026-07-26); Hugo parses a bare `date: YYYY-MM-DD` as midnight in the SITE timezone, so the page is future-dated and Hugo silently omits it — build still exits 0, which is why the test's returncode assertion passes and only the glob fails. Confirmed: `hugo --buildDrafts` renders 22 pages and no 01-smoke-test; `hugo --buildDrafts --buildFuture` renders 23 and the page appears.

Not an environment break and not caused by this branch: it passes in CI (UTC) and locally outside the midnight..UTC-midnight window. It matters here because the glossary render tests (GL-2, GL-7) scaffold content and build Hugo the same way and would inherit the identical flake. Plan phase 5 fixes the existing test and writes the new ones with --buildFuture from the start.
