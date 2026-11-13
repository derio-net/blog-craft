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

<!-- fr:journal kind=decision scope=plan id=p2-nominalization-endings created=2026-11-13T14:24:54+00:00 phase=2 -->
### p2-nominalization-endings · decision · nominalizations matches -ion and -sis, not only -tion (phase 2) (phase 2)

The spec's kind table listed -tion/-ment/-ance/-ence/-al, which misses the plan's own examples "make a decision" (-sion) and "conduct an analysis" (-sis). The matcher uses -ion/-ment/-ance/-ence/-al/-sis with a stop-list of nouns that hide no verb (question, moment, document, total, ...); the spec's table row was amended to match.

<!-- fr:journal kind=decision scope=plan id=p2-phrases-longest-wins created=2026-11-13T14:24:54+00:00 phase=2 -->
### p2-phrases-longest-wins · decision · phrases reports a phrase inside a longer listed phrase once (phase 2) (phase 2)

elements-of-style lists both "the fact that" and "owing to the fact that" (as the spec block does), so one phrase would fail twice. match_phrases drops a hit whose span lies inside a longer hit of the same check in the same sentence. Tested in test_writing_standard_kinds.py.

<!-- fr:journal kind=decision scope=plan id=p2-heuristic-shapes created=2026-11-13T14:24:54+00:00 phase=2 -->
### p2-heuristic-shapes · decision · loose_sentences and abbreviations heuristics (phase 2) (phase 2)

loose_sentences counts a sentence as loose when a comma precedes and/but/so/which/who ("salt and pepper" is not a clause join), and a run never crosses a paragraph. abbreviations: a 2-6 capital token (optional plural s) is spelled out when written "full form (ABC)" or "ABC (full form with a lowercase letter)"; only its first use counts.

<!-- fr:journal kind=discovery scope=plan id=p2-ste-after-example created=2026-11-13T14:24:54+00:00 phase=2 -->
### p2-ste-after-example · discovery · ste's inline two-step "after" example read as one step (phase 2) (phase 2)

"- After: 1. Open the file. 2. Run the tests." becomes one ordered item on a scratch page and fails one_instruction. ste.md now writes it as a two-line list. A registry test (test_each_standards_after_examples_pass_its_own_checker) checks every standard's "- After:" examples against its own checker, so P2.T2.S3 is enforced, not one-off.

<!-- fr:journal kind=review scope=plan id=review-p2 created=2026-11-13T14:37:12+00:00 phase=2 -->
### review-p2 · review · phase 2 code review: 7 findings (6 in, 1 reclassified in), all fixed (phase 2)

Independent reviewer (separate context, read-only) over spec + plan + diff 03bea73..86631a8, weighted to tests and simplicity; real-world probe of both standards on super-fr's fr-isolation explainer and two hand drafts found the hits sensible. Licensing checked: eos rules map to Strunk 1918 rules, nothing copied from later editions. Fixes in c82fe87; 222 writing-standard tests pass locally; CI test green on c82fe87. Reviewer suggested a heuristic-precision lens (false-positive pass of warn-level heuristics on a real corpus).

<!-- fr:journal kind=finding scope=plan id=p2-r1 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r1 · finding [open] (reviewer: in scope) · abbreviations misses a sentence-final token (phase 2)

Raised by the phase 2 reviewer.

<!-- fr:journal kind=finding scope=plan id=p2-r2 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r2 · finding [open] (reviewer: in scope) · nominalizations fires on -al adjectives and common nouns; stop-lists real nominalizations (phase 2)

Raised by the phase 2 reviewer.

<!-- fr:journal kind=finding scope=plan id=p2-r3 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r3 · finding [open] (reviewer: in scope) · loose_sentences counts Oxford-comma lists as clause joins (phase 2)

Raised by the phase 2 reviewer.

<!-- fr:journal kind=finding scope=plan id=p2-r4 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r4 · finding [open] (reviewer: in scope) · abbreviations flags all-caps emphasis and Roman numerals (phase 2)

Raised by the phase 2 reviewer.

<!-- fr:journal kind=finding scope=plan id=p2-r5 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r5 · finding [open] (reviewer: in scope) · README misstates which exact kinds ship at warn; 'capitalized' vs all-capitals (phase 2)

Raised by the phase 2 reviewer.

<!-- fr:journal kind=finding scope=plan id=p2-r6 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r6 · finding [open] (reviewer: in scope) · README kinds test only checked names appear anywhere (phase 2)

Raised by the phase 2 reviewer.

<!-- fr:journal kind=finding scope=plan id=p2-r7 created=2026-11-13T14:37:12+00:00 phase=2 state=open review_scope=in -->
### p2-r7 · finding [open] (reviewer: in scope) · front-matter waiver keyed by kind name accepted but never applied when the check id differs (phase 2)

The reviewer tagged it out of scope as phase 1 code; reclassified in scope by the orchestrator because this feature (phase 1) introduced it, so this change is what is wrong.

<!-- fr:journal kind=finding scope=plan id=p2-r1-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r1 -->
### p2-r1-resolved · finding [fixed] · resolves p2-r1: abbreviations misses a sentence-final token (phase 2)

c82fe87; test_r1_sentence_final_abbreviation_hits, test_r1_dotted_token_is_not_an_abbreviation

<!-- fr:journal kind=finding scope=plan id=p2-r2-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r2 -->
### p2-r2-resolved · finding [fixed] · resolves p2-r2: nominalizations fires on -al adjectives and common nouns; stop-lists real nominalizations (phase 2)

c82fe87; test_r2_nouns_that_hide_no_verb_pass, test_r2_real_al_nominalizations_hit (spec kind row amended)

<!-- fr:journal kind=finding scope=plan id=p2-r3-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r3 -->
### p2-r3-resolved · finding [fixed] · resolves p2-r3: loose_sentences counts Oxford-comma lists as clause joins (phase 2)

c82fe87; test_r3_oxford_comma_lists_are_not_loose_sentences, test_r3_a_clause_join_after_a_list_still_counts

<!-- fr:journal kind=finding scope=plan id=p2-r4-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r4 -->
### p2-r4-resolved · finding [fixed] · resolves p2-r4: abbreviations flags all-caps emphasis and Roman numerals (phase 2)

c82fe87; test_r4_emphasis_caps_and_roman_numerals_pass

<!-- fr:journal kind=finding scope=plan id=p2-r5-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r5 -->
### p2-r5-resolved · finding [fixed] · resolves p2-r5: README misstates which exact kinds ship at warn; 'capitalized' vs all-capitals (phase 2)

c82fe87; test_readme_names_long_sentence_as_an_exception, test_readme_and_plain_language_say_all_capitals

<!-- fr:journal kind=finding scope=plan id=p2-r6-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r6 -->
### p2-r6-resolved · finding [fixed] · resolves p2-r6: README kinds test only checked names appear anywhere (phase 2)

c82fe87; test_readme_kind_table_matches_kinds

<!-- fr:journal kind=finding scope=plan id=p2-r7-resolved created=2026-11-13T14:37:12+00:00 phase=2 state=fixed resolves=p2-r7 -->
### p2-r7-resolved · finding [fixed] · resolves p2-r7: front-matter waiver keyed by kind name accepted but never applied when the check id differs (phase 2)

c82fe87; test_r7_a_kind_name_waiver_applies_to_the_standards_check_of_that_kind

<!-- fr:journal kind=decision scope=plan id=p3-preserve-shape created=2026-11-13T14:59:58+00:00 phase=3 -->
### p3-preserve-shape · decision · --preserve-from: one unwaivable FAIL per item that appeared or disappeared; a page outside git is exit 2 (phase 3)

preserved_items(text) is a pure function returning four Counters (fenced code incl. its
fence lines, inline code content, link targets incl. reference definitions, autolinks and
bare URLs, numerals by the spec's regex in prose with list markers, link targets, HTML tags
and inline code removed). Each difference is one `preserve` FAIL: a disappeared item at
line 1 naming its line at the ref, an appeared item at its line in the page. Preserve hits
are added after waivers, so an in-source waiver cannot hide one (the skill may not waive to
pass). A page with no git toplevel is a usage error (exit 2), distinct from a page with no
version at the ref (FAIL `preserve: no version at <ref>`). Anchor moves: an appeared
`path#a` pairs with a disappeared target of the same path when `a` is a heading slug of
the linked page (in-page for an empty path; `p`, `p.md`, `p/index.md`, `p/_index.md`
relative to the page); slugs are GitHub-style with -1/-2 repeats, or an explicit `{#id}`.

<!-- fr:journal kind=decision scope=plan id=p3-skill-stats-standard-guard created=2026-11-13T14:59:58+00:00 phase=3 -->
### p3-skill-stats-standard-guard · decision · apply-writing-standard stops when a STATS line names another standard than the one applied (phase 3)

The checker resolves front matter `writing_standard` and the series default before
`--default`, so a page pinned to another standard would be gated against that one while
the skill rewrites to the requested one. The skill reads the standard on each STATS line
and asks the operator when it differs; not in the spec's procedure, added as a guard.

<!-- fr:journal kind=finding scope=plan id=p3-readme-skill-list created=2026-11-13T14:59:58+00:00 phase=3 state=open review_scope=out -->
### p3-readme-skill-list · finding [open] (reviewer: out of scope) · README's skill list does not mention /apply-writing-standard (phase 3)

README.md lists every user-invocable skill; no phase of the plan adds the new skill there.
Left out of phase 3 (scope is P3.T1-P3.T2); a one-bullet README addition belongs to phase 4
or a follow-up.

<!-- fr:journal kind=discovery scope=plan id=p3-opencode-mirror created=2026-11-13T14:59:58+00:00 phase=3 -->
### p3-opencode-mirror · discovery · A new skill needs its generated OpenCode mirror (phase 3)

scripts/sync-opencode.py generates .opencode/ copies; test_opencode_sync and test_opencode_namespace fail CI without them.

<!-- fr:journal kind=review scope=plan id=review-p3 created=2026-11-13T15:16:06+00:00 phase=3 -->
### review-p3 · review · phase 3 code review: 12 findings, all in scope, all fixed (phase 3)

Independent reviewer (separate context, read-only) over spec + plan + diff 360a56d..992ee51, weighted to tests and simplicity, probing preservation with throwaway git repos. Fixes in ccb0b20, 7dbbb2e, e24a60d, 14d6836, f1f9378 (mirror); 306 tests pass locally; CI test green on f1f9378. Reviewer suggested adversarial-input and agent-procedure lenses.

<!-- fr:journal kind=finding scope=plan id=p3-r1 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r1 · finding [open] (reviewer: in scope) · numerals in link text never compared (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r2 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r2 · finding [open] (reviewer: in scope) · angle, Hugo ref/relref and HTML href/src link targets not extracted (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r3 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r3 · finding [open] (reviewer: in scope) · anchor move accepted while the old heading still exists (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r4 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r4 · finding [open] (reviewer: in scope) · ordered-marker strip applied to any line starting N. (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r5 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r5 · finding [open] (reviewer: in scope) · skipped pages got no preserve check; skill guard silent and late (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r6 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r6 · finding [open] (reviewer: in scope) · baseline copies collide on same basename (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r7 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r7 · finding [open] (reviewer: in scope) · unresolvable anchor updates were an unwaivable dead end (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r8 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r8 · finding [open] (reviewer: in scope) · inbound-link search incomplete and under-specified (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r9 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r9 · finding [open] (reviewer: in scope) · tests pinned less than claimed (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r10 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r10 · finding [open] (reviewer: in scope) · bad ref reported as no version (exit 1); non-UTF-8 old version traceback (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r11 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r11 · finding [open] (reviewer: in scope) · fact-keeper over-share rule forbade the rewrite itself (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r12 created=2026-11-13T15:16:06+00:00 phase=3 state=open review_scope=in -->
### p3-r12 · finding [open] (reviewer: in scope) · setext headings unslugged; adjacent fences merged (phase 3)

Raised by the phase 3 reviewer.

<!-- fr:journal kind=finding scope=plan id=p3-r1-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r1 -->
### p3-r1-resolved · finding [fixed] · resolves p3-r1: numerals in link text never compared (phase 3)

ccb0b20; test_numerals_in_link_text_are_compared, test_link_text_numerals_unchanged_pass

<!-- fr:journal kind=finding scope=plan id=p3-r2-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r2 -->
### p3-r2-resolved · finding [fixed] · resolves p3-r2: angle, Hugo ref/relref and HTML href/src link targets not extracted (phase 3)

ccb0b20; test_each_link_form_gives_its_target, test_a_changed_hugo_ref_target_fails, test_a_changed_html_href_fails, test_an_anchor_move_into_a_hugo_ref_is_accepted

<!-- fr:journal kind=finding scope=plan id=p3-r3-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r3 -->
### p3-r3-resolved · finding [fixed] · resolves p3-r3: anchor move accepted while the old heading still exists (phase 3)

ccb0b20; test_an_anchor_move_is_refused_when_the_old_heading_still_exists

<!-- fr:journal kind=finding scope=plan id=p3-r4-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r4 -->
### p3-r4-resolved · finding [fixed] · resolves p3-r4: ordered-marker strip applied to any line starting N. (phase 3)

ccb0b20; test_a_wrapped_sentence_ending_in_a_number_is_not_a_list_marker, test_a_changed_year_at_a_wrapped_line_start_fails, test_list_markers_after_a_blank_line_or_in_a_list_are_not_numerals

<!-- fr:journal kind=finding scope=plan id=p3-r5-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r5 -->
### p3-r5-resolved · finding [fixed] · resolves p3-r5: skipped pages got no preserve check; skill guard silent and late (phase 3)

ccb0b20+7dbbb2e; test_a_page_with_no_standard_is_still_preserve_checked, test_step_2_resolves_each_pages_standard_before_any_rewrite, test_the_batch_stops_when_stats_lines_do_not_match_the_pages

<!-- fr:journal kind=finding scope=plan id=p3-r6-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r6 -->
### p3-r6-resolved · finding [fixed] · resolves p3-r6: baseline copies collide on same basename (phase 3)

7dbbb2e; test_the_baseline_keeps_the_repository_relative_path

<!-- fr:journal kind=finding scope=plan id=p3-r7-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r7 -->
### p3-r7-resolved · finding [fixed] · resolves p3-r7: unresolvable anchor updates were an unwaivable dead end (phase 3)

ccb0b20+7dbbb2e; test_a_root_relative_anchor_resolves_against_the_content_root, test_a_url_encoded_anchor_is_decoded, test_an_anchor_the_checker_cannot_resolve_is_restored_and_listed

<!-- fr:journal kind=finding scope=plan id=p3-r8-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r8 -->
### p3-r8-resolved · finding [fixed] · resolves p3-r8: inbound-link search incomplete and under-specified (phase 3)

7dbbb2e; test_the_inbound_link_search_catches_every_link_form

<!-- fr:journal kind=finding scope=plan id=p3-r9-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r9 -->
### p3-r9-resolved · finding [fixed] · resolves p3-r9: tests pinned less than claimed (phase 3)

e24a60d+14d6836; test_the_preserve_hit_cannot_be_waived (strengthened), test_a_front_matter_preserve_waiver_is_refused, test_preserved_items_lists_each_kind_of_a_known_page, contract tests for the mismatch stop, two paths, summary fields, count line

<!-- fr:journal kind=finding scope=plan id=p3-r10-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r10 -->
### p3-r10-resolved · finding [fixed] · resolves p3-r10: bad ref reported as no version (exit 1); non-UTF-8 old version traceback (phase 3)

ccb0b20; test_an_unknown_ref_is_a_usage_error, test_an_old_version_that_is_not_utf8_is_a_usage_error

<!-- fr:journal kind=finding scope=plan id=p3-r11-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r11 -->
### p3-r11-resolved · finding [fixed] · resolves p3-r11: fact-keeper over-share rule forbade the rewrite itself (phase 3)

7dbbb2e; test_the_over_share_rule_does_not_forbid_the_rewrite_itself

<!-- fr:journal kind=finding scope=plan id=p3-r12-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=fixed resolves=p3-r12 -->
### p3-r12-resolved · finding [fixed] · resolves p3-r12: setext headings unslugged; adjacent fences merged (phase 3)

ccb0b20; test_setext_headings_get_slugs, test_a_thematic_break_after_a_blank_line_is_no_heading, test_an_anchor_move_to_a_setext_heading_is_accepted, test_adjacent_fences_are_two_items

<!-- fr:journal kind=finding scope=plan id=p3-readme-skill-list-resolved created=2026-11-13T15:16:06+00:00 phase=3 state=open resolves=p3-readme-skill-list out_of_scope=true -->
### p3-readme-skill-list-resolved · finding [out-of-scope] · resolves p3-readme-skill-list: README's skill list does not mention /apply-writing-standard (phase 3)

Same gap as spec-review finding s19 (README skill list); no decision requires it and this change's behaviour does not depend on it. Listed in the PR body for the operator.

<!-- fr:journal kind=decision scope=plan id=p4-severity-keys-refused created=2026-11-13T15:30:29+00:00 phase=4 -->
### p4-severity-keys-refused · decision · quality.writing_standard.severities refuses unknown keys, unlike quality.lint (phase 4)

validate_config checks each severity key with the checker's own
validate_severity_keys (loaded lazily, so a config without writing-standard
keys needs neither the checker nor yaml). quality.lint allows unknown keys for
forward compatibility; here the checker exits 2 on an unknown key, so accepting
it in the validator would only move the error to the gate.

<!-- fr:journal kind=discovery scope=plan id=p4-checker-needs-validate-educational created=2026-11-13T15:30:29+00:00 phase=4 -->
### p4-checker-needs-validate-educational · discovery · The materialized checker imports validate_educational from scripts/ (phase 4)

validate_writing_standard.py imports validate_educational._prose_lines. A blog's
scripts/ ships validate_educational.py too, so the materialized checker runs; the
test copies the whole template scripts/ tree (no PYTHONPATH) and runs every
standard from it. The super-fr standalone contract runs the tools/ copy, where
the sibling import also resolves.

<!-- fr:journal kind=decision scope=plan id=p4-ci-step-placement created=2026-11-13T15:30:29+00:00 phase=4 -->
### p4-ci-step-placement · decision · CI writing-standard step sits after the educational step, gated on quality.writing_standard.enabled only (phase 4)

`{{- with .quality }}{{- with .writing_standard }}{{- if .enabled }}`, independent of
quality.enabled, so a blog can run either gate alone. FULL_CFG in the site_dir
byte-identity test has no writing_standard, so already-synced blogs render unchanged.

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p4-t3 created=2026-11-13T15:30:29+00:00 phase=4 -->
### no-refactor-p4-t3 · discovery · no-refactor-because P4.T3 (phase 4)

P4.T3 is release bookkeeping (CHANGELOG entry, version check); there is no code to clean

<!-- fr:journal kind=review scope=plan id=review-p4 created=2026-11-13T15:44:47+00:00 phase=4 -->
### review-p4 · review · phase 4 code review: 5 findings (4 in, 1 reclassified in), all fixed (phase 4)

Independent reviewer (separate context, read-only) over spec + plan + diff 9c34c7b..7e515e7, weighted to tests and simplicity; verified materialization end to end (bootstrap renders all scripts/, /update adds the new files, the copied checker imports and runs in a throwaway blog). Fixes in 9277d6c, 38155d7, 1a87fc4, 5f9d1a7; 506 tests pass locally; CI test green on 5f9d1a7. Reviewer suggested a config-yaml-round-trip lens.

<!-- fr:journal kind=finding scope=plan id=p4-r1 created=2026-11-13T15:44:47+00:00 phase=4 state=open review_scope=in -->
### p4-r1 · finding [open] (reviewer: in scope) · unquoted `off` severity (the CONFIG.md example) loads as YAML False and was refused by both validators (phase 4)

Raised by the phase 4 reviewer.

<!-- fr:journal kind=finding scope=plan id=p4-r2 created=2026-11-13T15:44:47+00:00 phase=4 state=open review_scope=in -->
### p4-r2 · finding [open] (reviewer: in scope) · CONFIG.md schema overview omitted the writing_standard keys (phase 4)

Raised by the phase 4 reviewer.

<!-- fr:journal kind=finding scope=plan id=p4-r3 created=2026-11-13T15:44:47+00:00 phase=4 state=open review_scope=in -->
### p4-r3 · finding [open] (reviewer: in scope) · unknown keys in quality.writing_standard accepted; null treated differently by the two validators (phase 4)

Raised by the phase 4 reviewer.

<!-- fr:journal kind=finding scope=plan id=p4-r4 created=2026-11-13T15:44:47+00:00 phase=4 state=open review_scope=in -->
### p4-r4 · finding [open] (reviewer: in scope) · CHANGELOG 0.23.0 announced the two new standards twice (phase 4)

Raised by the phase 4 reviewer.

<!-- fr:journal kind=finding scope=plan id=p4-r5 created=2026-11-13T15:44:47+00:00 phase=4 state=open review_scope=in -->
### p4-r5 · finding [open] (reviewer: in scope) · test_mirrors docstring said validate_educational ships only with the quality gate on (phase 4)

The reviewer tagged it out of scope as an old docstring; reclassified in scope because this change made validate_educational's unconditional shipping load-bearing for the new checker.

<!-- fr:journal kind=finding scope=plan id=p4-r1-resolved created=2026-11-13T15:44:47+00:00 phase=4 state=fixed resolves=p4-r1 -->
### p4-r1-resolved · finding [fixed] · resolves p4-r1: unquoted `off` severity (the CONFIG.md example) loads as YAML False and was refused by both validators (phase 4)

9277d6c; test_r1_config_md_example_passes_validate_config, test_r1_config_md_example_passes_the_checker_config_and_turns_the_check_off, test_r1_parse_severity_overrides_maps_false_to_off_and_refuses_true, test_r1_a_bare_on_is_refused_with_a_clear_message

<!-- fr:journal kind=finding scope=plan id=p4-r2-resolved created=2026-11-13T15:44:47+00:00 phase=4 state=fixed resolves=p4-r2 -->
### p4-r2-resolved · finding [fixed] · resolves p4-r2: CONFIG.md schema overview omitted the writing_standard keys (phase 4)

38155d7; test_r2_config_md_overview_names_the_writing_standard_keys

<!-- fr:journal kind=finding scope=plan id=p4-r3-resolved created=2026-11-13T15:44:47+00:00 phase=4 state=fixed resolves=p4-r3 -->
### p4-r3-resolved · finding [fixed] · resolves p4-r3: unknown keys in quality.writing_standard accepted; null treated differently by the two validators (phase 4)

9277d6c; test_r3_both_validators_refuse[enable, null]

<!-- fr:journal kind=finding scope=plan id=p4-r4-resolved created=2026-11-13T15:44:47+00:00 phase=4 state=fixed resolves=p4-r4 -->
### p4-r4-resolved · finding [fixed] · resolves p4-r4: CHANGELOG 0.23.0 announced the two new standards twice (phase 4)

1a87fc4; test_r4_changelog_announces_each_standard_once

<!-- fr:journal kind=finding scope=plan id=p4-r5-resolved created=2026-11-13T15:44:47+00:00 phase=4 state=fixed resolves=p4-r5 -->
### p4-r5-resolved · finding [fixed] · resolves p4-r5: test_mirrors docstring said validate_educational ships only with the quality gate on (phase 4)

5f9d1a7; docstring only

<!-- fr:journal kind=finding scope=plan id=p3-readme-skill-list-resolved-2 created=2026-11-13T15:45:38+00:00 phase=3 state=open resolves=p3-readme-skill-list tracked_by=https://github.com/derio-net/blog-craft/issues/107 -->
### p3-readme-skill-list-resolved-2 · finding [deferred → https://github.com/derio-net/blog-craft/issues/107] · resolves p3-readme-skill-list: README's skill list does not mention /apply-writing-standard (phase 3)

Filed at deliver as https://github.com/derio-net/blog-craft/issues/107.
