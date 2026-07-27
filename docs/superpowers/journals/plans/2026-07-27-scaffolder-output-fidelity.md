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
