<!-- fr:journal-schema=3 -->
# Journal: 2026-11-13-writing-standards

<!-- fr:journal kind=decision scope=plan id=plan-tests-ci created=2026-11-13T13:40:41+00:00 -->
### plan-tests-ci · decision · Test evidence is CI (tests: ci), not a local log

The container has no hugo; 38 pre-existing tests fail locally for that reason alone (measured 2026-11-13, 3m13s run). Each phase runs its writing-standard tests locally and records CI's test job on the pushed head. The draft PR opens when implement starts.

<!-- fr:journal kind=discovery scope=plan id=p1-version-bump-early created=2026-11-13T13:58:11+00:00 phase=1 -->
### p1-version-bump-early · discovery · CI requires the version bump with the first tools/ change (phase 1)

check_version_bump_needed.py fails the test job on any tools/ change without a bump; the bump moved from P4.T3 to phase 1. Bumped 0.22.7 -> 0.23.0 with a placeholder CHANGELOG entry (test_changelog.py needs a section for the shipped version); P4.T3 completes the entry.

<!-- fr:journal kind=decision scope=plan id=p1-line-numbers-via-prose-lines created=2026-11-13T13:58:11+00:00 phase=1 -->
### p1-line-numbers-via-prose-lines · decision · Line numbers survive the reused fence rule by tagging each line's end (phase 1)

validate_educational._prose_lines drops lines, so it loses line numbers. The checker appends a NUL + index to each line before calling it (the fence match only reads the line start) and reads the indices back; validate_educational.py is unchanged (a spec non-goal).

<!-- fr:journal kind=decision scope=plan id=p1-waiver-scope created=2026-11-13T13:58:11+00:00 phase=1 -->
### p1-waiver-scope · decision · An in-source waiver covers the next non-blank line; front matter waives page-level kinds only (phase 1)

A `<!-- writing-standard: ignore <check> -- reason -->` suppresses one hit of that check on the next non-blank line after the comment. `writing_standard_waive` accepts only page-level kinds (average_sentence_length) or names no check of the standard; naming a sentence-level check of the standard fails as waiver_reason, so front matter cannot switch a check off for a whole page.

<!-- fr:journal kind=decision scope=plan id=p1-unimplemented-kinds created=2026-11-13T13:58:11+00:00 phase=1 -->
### p1-unimplemented-kinds · decision · The five P2 kinds are declared but have no matcher yet (phase 1)

KINDS declares all 12 kinds, so a standard naming one loads; run_checks raises StandardError (exit 2) for a kind with no matcher in MATCHERS, never a silent skip. P2 adds average_sentence_length, phrases, loose_sentences, nominalizations and abbreviations to MATCHERS.

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p1-t1 created=2026-11-13T13:58:11+00:00 phase=1 -->
### no-refactor-p1-t1 · discovery · no-refactor-because P1.T1 (phase 1)

a skeleton main() returning 0 and one smoke test: nothing to clean

<!-- fr:journal kind=review scope=plan id=review-p1 created=2026-11-13T14:11:59+00:00 phase=1 -->
### review-p1 · review · phase 1 code review: 13 findings, all in scope, all fixed (phase 1)

Independent reviewer (separate context, read-only) over spec + plan + diff faafc72..HEAD, weighted to tests and simplicity. Fixes in 7696e8a, tests in tests/unit/test_writing_standard_review_fixes.py; 118 writing-standard tests pass locally; CI test green on 7696e8a. Reviewer suggested a tests lens (every kind-table rule has positive and negative tests).

<!-- fr:journal kind=finding scope=plan id=p1-r1 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r1 · finding [open] (reviewer: in scope) · one_instruction misses "and then <verb>" (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r2 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r2 · finding [open] (reviewer: in scope) · waiver syntax inside fenced/inline code parsed as a real waiver (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r3 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r3 · finding [open] (reviewer: in scope) · stacked waiver comments: the first targets the second comment's line (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r4 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r4 · finding [open] (reviewer: in scope) · bad config, directory glob match or non-UTF-8 page crash instead of exit 2 (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r5 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r5 · finding [open] (reviewer: in scope) · bare URL regex swallows the sentence-ending period (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r6 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r6 · finding [open] (reviewer: in scope) · one_instruction misses a step's continuation paragraph (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r7 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r7 · finding [open] (reviewer: in scope) · proper nouns after 'and' fail one_instruction; 'Then <verb>' second sentence passes (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r8 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r8 · finding [open] (reviewer: in scope) · passive heuristic flags is open/often/even/then; no adverb handling (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r9 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r9 · finding [open] (reviewer: in scope) · contraction I'm not detected (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r10 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r10 · finding [open] (reviewer: in scope) · front-matter waiver naming no check silently accepted; waiver scope untested (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r11 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r11 · finding [open] (reviewer: in scope) · no registry tests for wrong parameter types or bad passive scope (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r12 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r12 · finding [open] (reviewer: in scope) · standards reloaded per page; page re-extracted for stats (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=finding scope=plan id=p1-r13 created=2026-11-13T14:11:59+00:00 phase=1 state=open review_scope=in -->
### p1-r13 · finding [open] (reviewer: in scope) · word count splits e.g./i.e./3.14 into two words (phase 1)

Raised by the phase 1 reviewer.

<!-- fr:journal kind=decision scope=plan id=p1-check-id-average-sentence-length created=2026-11-13T14:11:59+00:00 phase=1 -->
### p1-check-id-average-sentence-length · decision · plain-language's page-average check id is average_sentence_length (phase 1)

Waivers match by check id; the spec named the plain-language instance average_length while its waiver example used average_sentence_length. Renamed the instance in the spec so the documented front-matter waiver works.

<!-- fr:journal kind=finding scope=plan id=p1-r1-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r1 -->
### p1-r1-resolved · finding [fixed] · resolves p1-r1: one_instruction misses "and then <verb>" (phase 1)

7696e8a; test_r1_and_then_joins_a_second_instruction

<!-- fr:journal kind=finding scope=plan id=p1-r2-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r2 -->
### p1-r2-resolved · finding [fixed] · resolves p1-r2: waiver syntax inside fenced/inline code parsed as a real waiver (phase 1)

7696e8a; test_r2_waiver_syntax_in_code_is_not_a_waiver

<!-- fr:journal kind=finding scope=plan id=p1-r3-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r3 -->
### p1-r3-resolved · finding [fixed] · resolves p1-r3: stacked waiver comments: the first targets the second comment's line (phase 1)

7696e8a; test_r3_stacked_waivers_both_cover_the_sentence

<!-- fr:journal kind=finding scope=plan id=p1-r4-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r4 -->
### p1-r4-resolved · finding [fixed] · resolves p1-r4: bad config, directory glob match or non-UTF-8 page crash instead of exit 2 (phase 1)

7696e8a; test_r4_bad_config_exits_2, test_r4_glob_matching_a_directory_keeps_files_only, test_r4_non_utf8_page_exits_2

<!-- fr:journal kind=finding scope=plan id=p1-r5-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r5 -->
### p1-r5-resolved · finding [fixed] · resolves p1-r5: bare URL regex swallows the sentence-ending period (phase 1)

7696e8a; test_r5_bare_url_keeps_the_sentence_end

<!-- fr:journal kind=finding scope=plan id=p1-r6-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r6 -->
### p1-r6-resolved · finding [fixed] · resolves p1-r6: one_instruction misses a step's continuation paragraph (phase 1)

7696e8a; test_r6_step_continuation_paragraph_is_the_same_step, test_r6_separate_steps_do_not_join

<!-- fr:journal kind=finding scope=plan id=p1-r7-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r7 -->
### p1-r7-resolved · finding [fixed] · resolves p1-r7: proper nouns after 'and' fail one_instruction; 'Then <verb>' second sentence passes (phase 1)

7696e8a; test_r7_capitalised_word_mid_sentence_is_not_a_verb, test_r7_then_verb_sentence_is_a_second_instruction

<!-- fr:journal kind=finding scope=plan id=p1-r8-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r8 -->
### p1-r8-resolved · finding [fixed] · resolves p1-r8: passive heuristic flags is open/often/even/then; no adverb handling (phase 1)

7696e8a; test_r8_passive_stop_list, test_r8_one_adverb_before_the_participle

<!-- fr:journal kind=finding scope=plan id=p1-r9-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r9 -->
### p1-r9-resolved · finding [fixed] · resolves p1-r9: contraction I'm not detected (phase 1)

7696e8a; test_r9_i_am_contraction (spec kind table updated)

<!-- fr:journal kind=finding scope=plan id=p1-r10-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r10 -->
### p1-r10-resolved · finding [fixed] · resolves p1-r10: front-matter waiver naming no check silently accepted; waiver scope untested (phase 1)

7696e8a; test_r10_front_matter_waiver_naming_no_check_exits_2, test_r10_front_matter_waiver_of_a_sentence_level_check_fails

<!-- fr:journal kind=finding scope=plan id=p1-r11-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r11 -->
### p1-r11-resolved · finding [fixed] · resolves p1-r11: no registry tests for wrong parameter types or bad passive scope (phase 1)

7696e8a; test_r11_bad_parameter_values_are_refused (loader already correct)

<!-- fr:journal kind=finding scope=plan id=p1-r12-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r12 -->
### p1-r12-resolved · finding [fixed] · resolves p1-r12: standards reloaded per page; page re-extracted for stats (phase 1)

7696e8a; test_r12_standards_load_once_per_run, test_r12_run_checks_returns_the_page

<!-- fr:journal kind=finding scope=plan id=p1-r13-resolved created=2026-11-13T14:11:59+00:00 phase=1 state=fixed resolves=p1-r13 -->
### p1-r13-resolved · finding [fixed] · resolves p1-r13: word count splits e.g./i.e./3.14 into two words (phase 1)

7696e8a; test_r13_dotted_tokens_are_one_word
