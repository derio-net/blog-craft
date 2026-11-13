<!-- fr:journal-schema=4 -->
# Journal: 2026-11-13-ste-writing-standard

<!-- fr:journal kind=discovery scope=spec id=brief created=2026-11-13T11:50:19+00:00 input=true -->
### brief · discovery · Operator brief (verbatim)

Turn 1: "can you write a few of the fr documentation & explainer pages with ASD-STE100 and show them here for comparison? Are the current pages using a standard today? What is decided by blog-craft?"

Turn 2: "make the side-by-side comparison page

What about a blog-craft feature that uses STE as another writing method and we use it in super-fr afterwards to regenerate the explainers/documentation?"

Turn 3: "yes, add blog-craft and start the brainstorm"

<!-- fr:journal kind=decision scope=spec id=d-scope created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-scope · decision · First release: checker + rewrite + fact check

Operator chose the recommended scope: deterministic checker and rules reference, batch rewrite of any Markdown, read-only fact-check subagent.

<!-- fr:journal kind=decision scope=spec id=d-strictness created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-strictness · decision · Exact checks fail, heuristic checks warn

Sentence length, contractions, one instruction per step fail; passive, -ing, vocabulary warn; every severity overridable fail|warn|off.

<!-- fr:journal kind=decision scope=spec id=d-vocabulary created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-vocabulary · decision · Own replacement list, no ASD dictionary text

Feature described as 'STE writing rules, based on ASD-STE100', never STE-conformant; product terms exempt.

<!-- fr:journal kind=decision scope=spec id=d-optin created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-optin · decision · Opt-in by front matter plus group default

writing_standard front matter wins; else series default (blog) or CLI --default (no blog config).

<!-- fr:journal kind=decision scope=spec id=d-home created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-home · decision · New skill apply-writing-standard, standard as a parameter

Operator: 'new skill, apply-writing-standard with the standard passed as a parameter. We can even ship multiple writing standards'. A standard is a registry entry; ste is the first.

<!-- fr:journal kind=decision scope=spec id=d-verification created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-verification · decision · CI plus one pre-merge client-live rewrite, no post-merge gate

Unit tests for checker/registry/selection; one client-live walk of the skill on two super-fr pages; super-fr adoption is a separate super-fr feature.

<!-- fr:journal kind=decision scope=spec id=d-three-standards created=2026-11-13T12:17:55+00:00 decided_by=operator -->
### d-three-standards · decision · Ship three standards: ste, elements-of-style, plain-language

Operator: "let's extend this by shipping a second and third standard": The Elements of Style (Strunk & White) and Plain English / Plain Language, "We could try these for the explainers". Built on Strunk 1918 (public domain) and the US Federal Plain Language Guidelines (US government work); check data moves to named instances of a closed set of kinds.

<!-- fr:journal kind=decision scope=spec id=d-verify-none created=2026-11-13T13:23:39+00:00 decided_by=operator -->
### d-verify-none · decision · No live walk: verify none, unit and contract tests suffice

Operator: "verify: none, the tests should suffice". Replaces the client-live walk of decision d-verification.

<!-- fr:journal kind=review scope=spec id=spec-review created=2026-11-13T13:29:50+00:00 -->
### spec-review · review · independent spec review: 19 findings (18 in scope, 1 out)

fr-spec-reviewer, read-only, separate context. Verified the named codebase surfaces (validate_educational.py, validate_config.py, test_mirrors.py, cold-reader contract, batch-gate.sh, CI template, CONFIG.md §14 last) and the licensing claims.

<!-- fr:journal kind=finding scope=spec id=s1 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s1 · finding [open] (reviewer: in scope) · R15 anchor updates broke R12's link-target preservation

severity: high. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s2 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s2 · finding [open] (reviewer: in scope) · Number preservation failed legitimate rewrites (list renumbering, step splits)

severity: high. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s3 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s3 · finding [open] (reviewer: in scope) · Non-goals still cited the dropped live walk

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s4 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s4 · finding [open] (reviewer: in scope) · Standards lookup named siblings, materialization uses scripts/writing-standards/

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s5 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s5 · finding [open] (reviewer: in scope) · Hand-listed mirror pairs made R2 false for blogs

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s6 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s6 · finding [open] (reviewer: in scope) · standards/README.md would be read as a standard

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s7 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s7 · finding [open] (reviewer: in scope) · Series default ambiguous for multi-series posts

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s8 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s8 · finding [open] (reviewer: in scope) · Flat severity keys across standards; unknown ids unspecified

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s9 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s9 · finding [open] (reviewer: in scope) · Inline code dropped vs counted as one word

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s10 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s10 · finding [open] (reviewer: in scope) · Splitter rules for ':' , closing emphasis, abbreviations

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s11 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s11 · finding [open] (reviewer: in scope) · Context-dependent phrases and verbs at fail severity

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s12 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s12 · finding [open] (reviewer: in scope) · Page-level hits unwaivable; waiver delimiter ambiguous

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s13 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s13 · finding [open] (reviewer: in scope) · fact-keeper baseline as a temp file contradicted 'no /tmp copies'; untracked pages

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s14 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s14 · finding [open] (reviewer: in scope) · Test Plan gaps for R19 wiring, R11 wording, R5 skipped count, R12 absent page

severity: medium. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s15 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s15 · finding [open] (reviewer: in scope) · Repo root for terms file and git show undefined without blog config

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s16 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s16 · finding [open] (reviewer: in scope) · R10 exemption scope vs kind table; typographic apostrophes

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s17 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s17 · finding [open] (reviewer: in scope) · Config schema version for new keys unstated

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s18 created=2026-11-13T13:29:50+00:00 state=open review_scope=in -->
### s18 · finding [open] (reviewer: in scope) · Registry acceptance row described one standard

severity: low. Independent spec review.

<!-- fr:journal kind=finding scope=spec id=s19 created=2026-11-13T13:29:50+00:00 state=open review_scope=out -->
### s19 · finding [open] (reviewer: out of scope) · README skill list and USING-ON-A-HOST do not mention the new skill or agent

severity: low. Adjacent docs; no decision requires it.

<!-- fr:journal kind=discovery scope=spec id=ste-draft-preserve created=2026-11-13T13:29:50+00:00 -->
### ste-draft-preserve · discovery · The hand-written STE draft of fr-isolation fails the preservation check

Measured 2026-11-13 against super-fr's fr-isolation.md: the STE draft split the bash block into steps (lost fence) and list markers counted as numerals; the Elements of Style and Plain language drafts preserve every fence, inline code span, link and numeral. Fed findings s1/s2.

<!-- fr:journal kind=finding scope=spec id=s1-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s1 -->
### s1-resolved · finding [fixed] · resolves s1: R15 anchor updates broke R12's link-target preservation

R12 now passes an anchor-only change whose new anchor names a heading; skill keep-list and Test Plan 6 updated.

<!-- fr:journal kind=finding scope=spec id=s2-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s2 -->
### s2-resolved · finding [fixed] · resolves s2: Number preservation failed legitimate rewrites (list renumbering, step splits)

Ordered-list markers excluded; spelled-out numbers left to fact-keeper; step-split case in Test Plan 6.

<!-- fr:journal kind=finding scope=spec id=s3-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s3 -->
### s3-resolved · finding [fixed] · resolves s3: Non-goals still cited the dropped live walk

Reworded: the choice belongs to super-fr's adoption feature.

<!-- fr:journal kind=finding scope=spec id=s4-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s4 -->
### s4-resolved · finding [fixed] · resolves s4: Standards lookup named siblings, materialization uses scripts/writing-standards/

Lookup now names writing-standards/ next to the script.

<!-- fr:journal kind=finding scope=spec id=s5-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s5 -->
### s5-resolved · finding [fixed] · resolves s5: Hand-listed mirror pairs made R2 false for blogs

Standards mirrored by a glob both ways; only the checker is a pair.

<!-- fr:journal kind=finding scope=spec id=s6-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s6 -->
### s6-resolved · finding [fixed] · resolves s6: standards/README.md would be read as a standard

Registry excludes README.md; Test Plan 1 asserts exactly three.

<!-- fr:journal kind=finding scope=spec id=s7-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s7 -->
### s7-resolved · finding [fixed] · resolves s7: Series default ambiguous for multi-series posts

Series from front matter; conflicting defaults exit 2 (R5); Test Plan 3 case.

<!-- fr:journal kind=finding scope=spec id=s8-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s8 -->
### s8-resolved · finding [fixed] · resolves s8: Flat severity keys across standards; unknown ids unspecified

Keys <standard>.<check> with bare fallback; unknown keys exit 2 (R9); tested.

<!-- fr:journal kind=finding scope=spec id=s9-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s9 -->
### s9-resolved · finding [fixed] · resolves s9: Inline code dropped vs counted as one word

Inline code becomes one placeholder token counted as a word; Test Plan 2.

<!-- fr:journal kind=finding scope=spec id=s10-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s10 -->
### s10-resolved · finding [fixed] · resolves s10: Splitter rules for ':' , closing emphasis, abbreviations

Rules sharpened (closing emphasis, abbreviation list, colon only before list/fence); each pinned in Test Plan 2.

<!-- fr:journal kind=finding scope=spec id=s11-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s11 -->
### s11-resolved · finding [fixed] · resolves s11: Context-dependent phrases and verbs at fail severity

who is / which was moved to a warn instance; one_instruction looks only at sentence-initial verbs; decision 2 states the rule for the later standards.

<!-- fr:journal kind=finding scope=spec id=s12-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s12 -->
### s12-resolved · finding [fixed] · resolves s12: Page-level hits unwaivable; waiver delimiter ambiguous

Front matter waiver for page-level checks; delimiter ' -- ' or ' — '; hit line is the sentence's first line.

<!-- fr:journal kind=finding scope=spec id=s13-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s13 -->
### s13-resolved · finding [fixed] · resolves s13: fact-keeper baseline as a temp file contradicted 'no /tmp copies'; untracked pages

Baseline in a per-run scratch dir outside the repo, deleted after the batch; pages with no HEAD version refused (R14a).

<!-- fr:journal kind=finding scope=spec id=s14-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s14 -->
### s14-resolved · finding [fixed] · resolves s14: Test Plan gaps for R19 wiring, R11 wording, R5 skipped count, R12 absent page

Each added to Test Plan 1, 3, 6, 7; R14a added for refusing dirty or untracked pages.

<!-- fr:journal kind=finding scope=spec id=s15-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s15 -->
### s15-resolved · finding [fixed] · resolves s15: Repo root for terms file and git show undefined without blog config

Both resolve at each page's git toplevel; cross-repo case in Test Plan 2.

<!-- fr:journal kind=finding scope=spec id=s16-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s16 -->
### s16-resolved · finding [fixed] · resolves s16: R10 exemption scope vs kind table; typographic apostrophes

R10 lists replacements, ing_forms, abbreviations; apostrophes normalise.

<!-- fr:journal kind=finding scope=spec id=s17-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s17 -->
### s17-resolved · finding [fixed] · resolves s17: Config schema version for new keys unstated

R20: optional keys of contract v7, no bump or migration.

<!-- fr:journal kind=finding scope=spec id=s18-resolved created=2026-11-13T13:29:50+00:00 state=fixed resolves=s18 -->
### s18-resolved · finding [fixed] · resolves s18: Registry acceptance row described one standard

Row notes now state all three standards; fr 6.2 has no reword command and the matrix is never hand-edited.

<!-- fr:journal kind=finding scope=spec id=s19-resolved created=2026-11-13T13:29:50+00:00 state=open resolves=s19 out_of_scope=true -->
### s19-resolved · finding [out-of-scope] · resolves s19: README skill list and USING-ON-A-HOST do not mention the new skill or agent

Not required by any decision; raised to the operator to add README entries during implementation if wanted.

<!-- fr:journal kind=decision scope=spec id=exit-baseline created=2026-11-13T13:29:51+00:00 -->
### exit-baseline · decision · exit when spec-review resolved

The exit when spec-review resolved; `fr verification set` and `deliver` compare against it.

```yaml
row_gates:
  writing-standard-apply-skill: none
  writing-standard-blog-integration: none
  writing-standard-checker: none
  writing-standard-elements-of-style: none
  writing-standard-plain-language: none
  writing-standard-preservation: none
  writing-standard-registry: none
  writing-standard-selection: none
  writing-standard-ste-checks: none
row_kinds:
  writing-standard-apply-skill: none
  writing-standard-blog-integration: none
  writing-standard-checker: none
  writing-standard-elements-of-style: none
  writing-standard-plain-language: none
  writing-standard-preservation: none
  writing-standard-registry: none
  writing-standard-selection: none
  writing-standard-ste-checks: none
run_gate: none
run_kind: none
```

<!-- fr:journal kind=decision scope=spec id=phase-split-2026-11-13-writing-standards-p2 created=2026-11-13T13:40:24+00:00 -->
### phase-split-2026-11-13-writing-standards-p2 · decision · ask: ship the elements-of-style and plain-language standards (R22-R25)

<!-- fr:journal kind=decision scope=spec id=phase-split-2026-11-13-writing-standards-p3 created=2026-11-13T13:40:25+00:00 -->
### phase-split-2026-11-13-writing-standards-p3 · decision · ask: the apply-writing-standard rewrite with preservation and fact check (R12, R14-R18)

<!-- fr:journal kind=decision scope=spec id=phase-split-2026-11-13-writing-standards-p4 created=2026-11-13T13:40:26+00:00 -->
### phase-split-2026-11-13-writing-standards-p4 · decision · ask: blog integration, materialization and release (R19-R21)

<!-- fr:journal kind=finding scope=spec id=s19-resolved-2 created=2026-11-13T15:45:30+00:00 state=open resolves=s19 tracked_by=https://github.com/derio-net/blog-craft/issues/106 -->
### s19-resolved-2 · finding [deferred → https://github.com/derio-net/blog-craft/issues/106] · resolves s19: README skill list and USING-ON-A-HOST do not mention the new skill or agent

Filed at deliver as https://github.com/derio-net/blog-craft/issues/106.

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-1 created=2026-11-13T21:07:08+00:00 -->
### test-plan-step-1 · discovery · Test Plan step 1: ran

Step: `test_writing_standard_registry.py` — the shipped set is exactly `ste`, `elements-of-style` and `plain-language` (`README.md` is not a standard); their blocks parse, each reference names its source, and no standard, README or SKILL.md says "conformant" or "compliant" (R11). An unknown kind, a bad parameter for a kind, and an unknown standard name each error. A fixture fourth standard that uses only existing kinds loads with no code change. Two instances of one kind in one standard both run.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-2 created=2026-11-13T21:07:09+00:00 -->
### test-plan-step-2 · discovery · Test Plan step 2: ran

Step: `test_writing_standard_checker.py` — prose extraction ignores front matter, code fences (including a nested ```` fence), inline code, tables, HTML comments and URLs. The procedural/descriptive split follows ordered lists. A bold question and its answer are two sentences. The splitter pins: closing emphasis after `?`, the listed abbreviations, a colon before a list or fence versus inside a sentence. Inline code counts as one word; typographic apostrophes normalise. A hit is reported on the line where its sentence starts. Exit codes are 0/1/2. `--stats` prints its line. It runs with no `--config`, from one repository against pages in another (terms file and `git show` resolve at the page's toplevel).

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-3 created=2026-11-13T21:07:10+00:00 -->
### test-plan-step-3 · discovery · Test Plan step 3: ran

Step: `test_writing_standard_selection.py` — front matter beats the series default, the series default beats `--default`, and `none` skips; skipped pages appear in the `M skipped` count. A post in two series with different defaults exits 2. An unknown name exits 2 and names the page.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-4 created=2026-11-13T21:07:12+00:00 -->
### test-plan-step-4 · discovery · Test Plan step 4: ran

Step: `test_writing_standard_ste_checks.py` — one passing and one failing fixture per check. Severity overrides from config and CLI work, qualified (`ste.paragraph_length`) over bare, and an override naming an unknown standard or check exits 2. A waiver with a reason (either delimiter) suppresses one hit; one without a reason fails; a front matter waiver covers `average_sentence_length`. Terms exempt `replacements`, `-ing` and abbreviations. A descriptive clause in a step that contains a step verb ("this lets you keep working") passes `one_instruction`.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-5 created=2026-11-13T21:07:13+00:00 -->
### test-plan-step-5 · discovery · Test Plan step 5: ran

Step: `test_writing_standard_elements_of_style.py` and `test_writing_standard_plain_language.py` — for each check of the standard, one passing and one failing fixture, at the standard's default severity: under `elements-of-style` a 60-word sentence passes, "in order to" fails and "who is" only warns; under `plain-language` a page averaging 21 words fails, one averaging 19 with a single 30-word sentence passes, and "shall" fails.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-6 created=2026-11-13T21:07:14+00:00 -->
### test-plan-step-6 · discovery · Test Plan step 6: ran

Step: `test_writing_standard_preserve.py` — in a temporary git repo, a changed code block, inline code span, link target or numeral fails `preserve`, and a reworded sentence passes. Splitting a step into two (renumbering the list) passes. Changing a heading and its in-page `#anchor` link together passes; an anchor to no heading fails. A page absent at the ref fails with `no version at <ref>`.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-7 created=2026-11-13T21:07:15+00:00 -->
### test-plan-step-7 · discovery · Test Plan step 7: ran

Step: Blog integration — `validate_config.py` accepts and refuses the new keys, at v7. The mirror test pairs the checker and globs the standards both ways. `batch-gate.sh` runs the checker. The CI template adds the step only when enabled. A contract test, like `test_cold_reader_contract.py`'s wiring checks, asserts that `/blog-post` and `/post-rewrite` load the resolved standard and run the checker in their gate step.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-8 created=2026-11-13T21:07:17+00:00 -->
### test-plan-step-8 · discovery · Test Plan step 8: ran

Step: `test_apply_writing_standard_contract.py` and `test_fact_keeper_contract.py` — like `test_cold_reader_contract.py`: the skill takes `standard`, `paths` and `batch_size` (3–5); it refuses an unknown standard, dirty paths and paths with no version at `HEAD`; it writes the fact-keeper baseline outside the repository and deletes it; each batch runs the checker with `--preserve-from HEAD`, dispatches `fact-keeper` per page and stops for approval; it handles changed headings' inbound links; it names the no-`claude -p` rule. The agent is read-only (Read, Grep, Glob), takes exactly two paths, and returns kept / changed / lost / added.

Evidence: ran on merged main 358f386: the Test Plan's test files, 381 passed together (tests/run-unit.sh), and CI test was green on the PR head 1ec71c7 before merge
