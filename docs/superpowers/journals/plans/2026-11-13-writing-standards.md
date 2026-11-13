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
