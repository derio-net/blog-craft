# Journal: 2026-07-27-scaffolder-output-fidelity

<!-- fr:journal kind=discovery scope=plan id=p1-indent-detection-shape created=2026-07-27T21:44:26 phase=1 -->
### p1-indent-detection-shape · discovery · prompts_append: one textual indent scan + a semantic pre-parse, not one or the other (phase 1)

The indent has to be read textually (the parsed document has no column information), but every *refusal* case — unparseable file, `images:` as a mapping, no `images:` key — is cleanly answered by a yaml.safe_load pre-parse that is needed anyway for the D2 count-before. So `sequence_indent()` never has to distinguish 'no images key' from 'images is a mapping': it returns a fallback of 2 for anything it cannot recognise, and `load_entries()` (which raises ValueError naming the shape problem) is the gate. `images:` with nothing under it parses to None and is deliberately mapped to `[]`, not an error — that is the bootstrap shape and what tests/unit/test_blog_post_create.py:37 seeds.

<!-- fr:journal kind=finding scope=plan id=p1-keep-chomp-seam created=2026-07-27T21:44:38 phase=1 state=open -->
### p1-keep-chomp-seam · finding [open] · Seam normalisation rewrites trailing blank lines — a |+ kept block scalar is the one shape that would notice (phase 1)

`rstrip('\\n') + '\\n'` is what stops a newline-less file being fused with the appended entry (spec §3), but it also drops trailing BLANK lines. For clip (`|`) and strip (`|-`) chomping that is value-preserving, so 'every byte above the insertion point is identical' holds for every real prompts file. A final entry ending in `scene: |+` with trailing blank lines would silently lose them, and the D2 verification would not catch it (it checks the count and the last key, not scalar contents). No blog-craft template or tool emits `|+`; left as a recorded edge rather than special-cased. If it ever matters, the fix is to only strip the trailing newlines that exceed one when the file does not end inside a kept scalar.

<!-- fr:journal kind=discovery scope=plan id=p1-tdd-backout created=2026-07-27T21:44:45 phase=1 -->
### p1-tdd-backout · discovery · T1.S2 over-implemented; backed out to get a real RED for T2 (phase 1)

The first GREEN accidentally included the seam normalisation and the D2 verify-after-write that belong to task 2. Rather than declare T2 green-on-arrival, cmd_append() was reduced to the task-1 minimum (read indent, reindent, append) and the task-2 tests were run against it: 5 of the 6 failed for the right reasons (a newline-less file fused, and the broken / mapping / no-images / key-mismatch cases were all appended to and left changed on disk). test_trailing_blank_lines_are_normalised passed against the minimum — blank lines between sequence items are legal YAML, so that case is a non-regression guard, not a defect today. The full implementation was then restored.

<!-- fr:journal kind=discovery scope=plan id=p2-empty-seed-hid-it created=2026-07-27T21:55:51 phase=2 -->
### p2-empty-seed-hid-it · discovery · The 2-space RED test passes without the fix — only the column-0 seed is diagnostic (phase 2)

Of the four new tests, three went red against the un-wired script and one (2-space seed) passed on arrival: the hard-coded `  - key:` happens to be right for a bootstrap-shaped file, so that case is a non-regression guard, not evidence. The column-0 seed failed with exactly the ParserError the issue reports — `expected <block end>, but found '-'`, the new item read as a continuation of the previous entry's mapping — and the broken-file seed failed on returncode 0. The newline-less seed failed in a third distinct way worth recording: the scene block scalar SWALLOWED the appended entry (`scene: 'an existing scene  - key: building-09\n'` with the whole new entry nested under it as extra mapping keys), so the file still parsed and still had 1 entry. That shape would never have raised at generate time either — it would have silently generated the wrong image for the wrong key. The empty-sequence default seed at tests/unit/test_blog_post_create.py:37 could not see any of the three.

<!-- fr:journal kind=discovery scope=plan id=p2-awk-terminator-was-vacuous created=2026-07-27T21:56:00 phase=2 -->
### p2-awk-terminator-was-vacuous · discovery · The smoke test awk terminator was not merely fragile — it was already wrong for a column-0 file (phase 2)

tests/smoke-blog-post.sh:93 terminated the scene-line count on `/^  - key:/`. Measured against a two-entry fixture: at 2-space indent old and new both count 1; at COLUMN 0 the old pattern never terminates, runs to EOF and counts 5 (every non-blank line of the rest of the file), while the relaxed `/^[[:space:]]*- key:/` counts 1. So the assertion was not "fine today, fragile tomorrow" — it would have gone red-for-the-wrong-reason the moment the smoke fixture used a column-0 prompts file, and if the terminator had instead been over-broad it would have gone vacuous. The fixture (templates/hugo-hextra/prompt_for_images.yaml.tmpl) is 2-space, which is why nobody saw it. B2.d still reports 1 line, not 0.

<!-- fr:journal kind=discovery scope=plan id=p2-shell-seam created=2026-07-27T21:56:06 phase=2 -->
### p2-shell-seam · discovery · Wiring notes: set -e carries exit 2, the temp block needs a trap, and the file-exists guard stays (phase 2)

The rewire is `} > "$ENTRY_BLOCK"` plus `python3 "$HERE/prompts_append.py" append --file "$PROMPTS_YAML" --key "$KEY" --entry-file "$ENTRY_BLOCK"`. Three seam details: (1) `set -euo pipefail` propagates the helper's exit 2 with no wrapper needed, and step 3 (generate-images.py) therefore never runs on a refused append — asserted by test_broken_entries_file_fails_loudly_and_is_left_alone rather than trusted; (2) mktemp + `trap 'rm -f "$ENTRY_BLOCK"' EXIT` is the script's first EXIT trap, so anything later that wants one must chain, not replace; (3) blog-post-create.sh:104's `[[ -f "$PROMPTS_YAML" ]]` guard is load-bearing and stays — cmd_append does not catch OSError, so a missing file would traceback instead of erroring cleanly. The helper is located only via `$HERE` (no fallback to the blog's scripts/), which keeps it plugin-side and keeps tests/unit/test_mirrors.py out of scope.

<!-- fr:journal kind=finding scope=plan id=p2-bpc12-backfill-deferred created=2026-07-27T21:56:21 phase=2 state=open -->
### p2-bpc12-backfill-deferred · finding [open] · BPC-1/BPC-2 are satisfied as of phase 2 but stay not-implemented until phase 6 flips them (phase 2)

Both rows now have real end-to-end evidence — tests/unit/test_prompts_append.py (phase 1) plus the four seeded tests in tests/unit/test_blog_post_create.py and tests/smoke-blog-post.sh (phase 2). `fr plan edit --complete-phase 2` warns accordingly. The flip is deliberately NOT done here: P6.T2.S2 owns editing docs/acceptance/matrix.yaml for all of BPC-1..5 + GL-10/11 in one pass, and doing it twice would collide. This is only a real debt if the plan is delivered as per-phase PRs rather than one PR through phase 6 — in the single-PR shape the repo-wide backfill rule is satisfied by phase 6. `fr acceptance check` is exit 0 today (13 not-implemented are warnings).
