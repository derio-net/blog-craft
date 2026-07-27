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

<!-- fr:journal kind=discovery scope=plan id=dd95e85adeac created=2026-07-27T22:09:04 phase=3 -->
### dd95e85adeac · discovery · series/layer/tags now emitted in convention order; field ORDER is asserted, not just presence (phase 3)

tools/blog-post-create.sh frontmatter is now: title, series, layer?, date, draft, tags, summary, weight, reader_goal?, diataxis? — asserted as an ordered key list by `_front_keys()` in tests/unit/test_blog_post_create.py (two cases: minimal spine on a layer-less blog, and the full 10-key order with --layer/--tag/reader-goal/diataxis). Presence-only assertions would not have caught a scaffold that an author reviews by diffing against a sibling post.

`series: ["<series>"]` is unconditional (D3): {{< series-index >}} is page-derived from `series`, so the omission silently kept a scaffolded post out of its own series overview while skills/blog-post/SKILL.md Step 8 promised the opposite. Quoted, unlike the sibling scaffolders bare `series: [key]` — equivalent after parsing, safe for any key.

Verbatim output on a blog that declares layers (--layer obs --tag operations --tag slo + reader-goal + diataxis):

```yaml
title: "Operating on Green"
series: ["operating"]
layer: obs
date: 2026-07-27
draft: false
tags: ["operations", "slo"]
summary: "sum"
weight: 31
reader_goal: "The reader can name the failure mode"
diataxis: [how-to, reference]
```

Same blog with --layer omitted: `layer: TODO` plus the two-line stderr WARNING. A blog that declares NO layers: no `layer` key at all, `tags: []  # TODO: add tags`.

<!-- fr:journal kind=discovery scope=plan id=19435ded9e25 created=2026-07-27T22:09:15 phase=3 -->
### 19435ded9e25 · discovery · --layer emits bare codes for greppability, quoted only when the value is not a plain token (phase 3)

D4 says an unregistered code on a layer-less blog is "accepted verbatim" (a blog may add the registry later). Verbatim means not REJECTING it — not emitting bytes the YAML parser chokes on: `--layer 'odd: "code"'` unquoted produces a broken mapping. So the emitter is conditional: `^[A-Za-z0-9][A-Za-z0-9_.-]*$` goes out bare (keeping `layer: obs` / `layer: TODO` greppable, as scaffold-paper.sh:59 established and as the spec justifies), anything else goes through yaml_escape into a double-quoted scalar. Covered by test_layer_value_is_yaml_safe. This is the only judgement call in phase 3 the spec did not state outright.

Two `set -e` traps avoided while writing this: (1) `for c in $CODES; do [[ ... ]] && ok=1; done` aborts the script when the LAST iteration is the non-match, so validation uses a single `[[ " $LAYER_CODES " != *" $LAYER "* ]]` substring test instead of a loop; (2) `[[ -n "$LAYER" ]] && echo ...` inside the frontmatter `{ ... } > file` group aborts when LAYER is empty — it must be `if/fi`.

The registry read is an inline PyYAML heredoc over $CONFIG (scaffold-paper.sh:26-34 pattern) because blog_config.py get flow-dumps non-scalars (tools/blog_config.py:52) and cannot express a list of mappings shell-parseably.

<!-- fr:journal kind=decision scope=plan id=ab777eea4db2 created=2026-07-27T22:09:25 phase=3 -->
### ab777eea4db2 · decision · FRANK_CFG gained series_index.layers; existing frank-shaped tests now scaffold with layer: TODO (phase 3)

tests/unit/test_blog_post_create.py FRANK_CFG now carries `series_index: {layers: [{code: obs, name: Observability}, {code: bld, name: Build}]}` (per P3.T2.S1), which is what makes both halves of D4 observable across the two fixture shapes. Side effect: test_frank_shaped_blog_scene_only_entry and test_entry_field_numbers_stay_numbers now scaffold posts with `layer: TODO` and a stderr WARNING. Neither asserts on stderr or on the absence of frontmatter keys, so both stay green — but a future test that asserts "clean stderr" for those cases would be asserting the wrong thing.

`series_index` appears nowhere else in this repo outside docs/CONFIG.md §5 and tools/gen-layer-palette.py; there is no config schema validator to teach, and templates/hugo-hextra/.blog-craft.yaml.tmpl does not declare it — so the bootstrap fixture path (tests/smoke-blog-post.sh, answers-frank-like.yaml) exercises the NO-layers branch and its output has no `layer` key. Smoke stayed at 13 passed: its B1.b-d greps are anchored (`^title:`, `^weight: 2$`, `^draft: false$`) and the two new lines (`series:`, the rewritten `tags:`) do not displace them.

<!-- fr:journal kind=finding scope=plan id=d842482e5770 created=2026-07-27T22:09:33 phase=3 state=open -->
### d842482e5770 · finding [open] · Phase 6 owes docs for four things phase 3 shipped: --layer, --tag, layer: TODO, and the tags-comment departure (phase 3)

Phase 3 documented the new flags in tools/blog-post-create.sh own usage header only. Still owed by phase 6 (which owns skills/docs, and by the repo acceptance-matrix rule, docs/acceptance/matrix.yaml):
- skills/blog-post/SKILL.md — the invocation now has --layer/--tag; Step 8 already promises series-index listing, which is finally TRUE.
- docs/CONFIG.md §5 — series_index.layers is now read by the scaffolder, not just gen-layer-palette.py.
- the `layer: TODO` + `# TODO: add tags` grep contract is what an author is told to search for; it needs to be written down somewhere an author reads.
- matrix rows for the new frontmatter assertions (13 new unit tests in tests/unit/test_blog_post_create.py).

Phase 3 deliberately touched neither docs/acceptance/matrix.yaml nor any skill.

<!-- fr:journal kind=discovery scope=plan id=8cf58ad3b1a2 created=2026-07-27T22:09:45 phase=3 -->
### 8cf58ad3b1a2 · discovery · Notes for phase 4 (key/output defaults): where to hook, and what phase 3 already put in place (phase 3)

Phase 4 owns `--key` (D6) and the detected `output:` default (D7). What phase 3 left it:
- The flag loop in tools/blog-post-create.sh now has four flags in one `while`/`case`; add `--key` and keep `--output` winning over detection.
- `KEY="$SERIES-$NUMBER"` and `OUTPUT_IMAGE=${OUTPUT_OVERRIDE:-"$OUTPUT_DIR/$KEY-cover.png"}` are UNTOUCHED and still sit together, right after the new TAGS_LINE block. `SITE_PREFIX` is computed on the next line — `prompts_append.py output-style --site-prefix` wants it, so the D7 detection call belongs AFTER that line, not with the other config reads.
- `PROMPTS_YAML` is validated to exist at that point already, so output-style can be called without re-checking.
- The inline-PyYAML-over-$CONFIG heredoc pattern is now established in this script (the LAYER_CODES block) if phase 4 needs another config read.
- Do not reuse `$D`-style bare unquoted interpolation for the detected output path; yaml_escape it like every other interpolated value.
- The script trap is still `trap 'rm -f "$ENTRY_BLOCK"' EXIT` and is still the only EXIT trap — chain, do not replace.

<!-- fr:journal kind=finding scope=plan id=dd2022e25525 created=2026-07-27T22:10:13 phase=3 state=open -->
### dd2022e25525 · finding [open] · Acceptance rows BPC-3 and BPC-4 are satisfied by phase 3 but left not-implemented (phase 6 owns matrix.yaml) (phase 3)

`fr plan edit --complete-phase 3` warned: "phase 3 completed but its acceptance rows are still not-implemented: BPC-3, BPC-4". Both are now verified in CI and only need the refs written down — phase 3 was instructed not to touch docs/acceptance/matrix.yaml. Phases share one branch and one PR, so the repo-wide "same PR" backfill rule is still met as long as phase 6 does this:

- BPC-3 ("A scaffolded post appears in its series overview — frontmatter carries the series the shortcode derives from"): status ci, levels.unit -> blog-craft:tests/unit/test_blog_post_create.py, levels.smoke (or the level name this repo uses for it) -> blog-craft:tests/smoke-blog-post.sh. Tests: test_series_always_emitted_default_shaped, test_series_always_emitted_frank_shaped, test_frontmatter_field_order_minimal, test_frontmatter_field_order_full.
- BPC-4 ("layer and tags are set from the invocation, and their absence is visible in the file rather than silent"): status ci, levels.unit -> blog-craft:tests/unit/test_blog_post_create.py. Tests: test_layer_flag_emitted_when_code_is_registered, test_unknown_layer_code_is_an_error_naming_the_valid_ones, test_layer_omitted_with_registry_is_todo_and_warns, test_layer_omitted_without_registry_emits_no_layer_key, test_layer_without_registry_is_accepted_verbatim, test_layer_value_is_yaml_safe, test_tag_flag_is_repeatable_and_ordered, test_tag_values_yaml_safe, test_no_tags_emits_empty_list_with_a_todo_comment.

BPC-5 (key/output defaults) stays not-implemented until phase 4.

<!-- fr:journal kind=discovery scope=plan id=096cafcc3be3 created=2026-07-27T22:22:11 phase=4 -->
### 096cafcc3be3 · discovery · --key is guarded with the script's own plain-token regex; only 1 of 3 key tests was diagnostic RED (phase 4)

`--key` reuses the exact shape the `layer:` emitter established in this script — `^[A-Za-z0-9][A-Za-z0-9_.-]*$` — rather than the --entry-field identifier regex at :51-52 (`^[A-Za-z_][A-Za-z0-9_]*$`), which would reject `ops-30-silent-failure` itself. So the script now has ONE plain-token notion, used for the two values that are interpolated bare into output the parser reads. Rejected end-to-end: `ops 30`, `ops"30`, `ops/30`, `$(id)`, `-ops` (a leading dash is consumed as the flag's argument, not re-read as a flag, so it reaches the guard). `--key ""` is caught earlier by `${2:?}`.

TDD note: of the three task-1 tests only test_key_override_names_entry_hint_and_cover went red (`ERROR: unknown flag --key`). test_key_defaults_to_series_number and test_bad_key_rejected passed against the unmodified script — the first BY DESIGN (D6's default is byte-compatible, so it is a regression guard on the thing that must not move), the second incidentally (an unknown flag already exits 2, and the guard is what keeps that true once the flag exists). Both are worth keeping and neither is evidence.

The printed hints needed no change: step 3's `--print-prompt $KEY` / `--only $KEY` and the `Edit: $BUNDLE_DIR/index.md` line already interpolate the resolved variables, never a re-derived `$SERIES-$NUMBER`. Asserted anyway (`"operating-30" not in stdout` on an override run) because that is the failure the issue would produce next.

<!-- fr:journal kind=discovery scope=plan id=65b702fe9c05 created=2026-07-27T22:22:38 phase=4 -->
### 65b702fe9c05 · discovery · D7 wiring: OUTPUT_IMAGE had to move below the prompts-file guard, and output: is now conditionally quoted (phase 4)

Four seam changes in tools/blog-post-create.sh, none of them visible from the plan text:

1. `OUTPUT_IMAGE` could no longer sit beside `KEY` (:161 as phase 3 left it). It now needs `$PROMPTS_YAML` (validated) and `$SITE_PREFIX` (computed one line later), so the resolution moved BELOW the prompts-file existence guard. `KEY` stays where it was.
2. `PROMPTS_APPEND` + its existence check were hoisted from step 2 (:229-230) to just after that guard — output-style is the first caller now. The later duplicate was removed, so there is still exactly one "helper is missing" error path.
3. New `BUNDLE_REL` holds the config-root-relative bundle path and `BUNDLE_DIR="$BLOG_ROOT/$BUNDLE_REL"`. The entry's `output:` is config-root-relative (that is what generate-images.py:325 resolves against), the mkdir needs the absolute one, and deriving both from one string is what makes "the cover lands in the bundle this run just created" true by construction instead of by coincidence.
4. `output:` is emitted BARE for a plain path (`^[A-Za-z0-9][A-Za-z0-9_./-]*$`) and quoted+escaped otherwise — the same conditional the `layer:` emitter uses, for the same reason. Bare keeps the byte shape of the 88 hand-written entries and of every previous run; the escape hatch exists because `--output` and the `<series>`/`<slug>` positional args the bundle path is built from are unguarded input.

Resolved values, verbatim, for the three detection shapes (series=operating, number=30, slug=silent-failure, output_dir=static/images):

- bundle-seeded, site_dir "." -> key `operating-30`, output `content/docs/operating/30-silent-failure/cover.png`; the 1x1 PNG lands at `<root>/content/docs/operating/30-silent-failure/cover.png` (asserted, not inferred: generate-images.py:350 mkdirs the parent).
- bundle-seeded, site_dir "blog" -> output `blog/content/docs/operating/30-silent-failure/cover.png`, cover at `<root>/blog/content/.../cover.png`.
- static-seeded -> `static/images/operating-30-cover.png` (unchanged from today).
- bare `images:` (the bootstrap/no-entries shape) -> `static/images/operating-30-cover.png` (unchanged).
- `--output static/images/chosen.png` wins in both shapes; with `--key ops-30-silent-failure` the bundle default is still `content/docs/operating/30-silent-failure/cover.png` — the key does not leak into a per-post directory name.

Ties, entries without `output`, and an unparseable file are covered at the helper level (tests/unit/test_prompts_append.py) and deliberately not re-tested end to end.

One stdout change: the entry line is now `prompts entry: key=<key> output=<path> appended to <file>`. Both halves are now variable per blog, so an operator would otherwise have to open the file to learn where the cover went. Nothing greps that line (tests/smoke-blog-post.sh asserts on the prompts file and the PNG, not the log).

<!-- fr:journal kind=finding scope=plan id=b56820abcc36 created=2026-07-27T22:22:55 phase=4 state=open -->
### b56820abcc36 · finding [open] · Phase 6 owes docs for --key and the detected output default; BPC-5 is satisfied but still not-implemented (phase 4)

Phase 4 documented `--key` and the new `--output` default in tools/blog-post-create.sh's own usage header only (it deliberately touched no skill and not docs/acceptance/matrix.yaml). Still owed by phase 6:

- skills/blog-post/SKILL.md — the invocation gains `--key`, and D6's honest half is a SKILL STEP: the agent must read an existing entry from the blog's prompts file and match its key convention, because nothing in the config can tell it that `operating` abbreviates to `ops`. Without that step `--key` exists and is never used.
- .opencode/skills/blog-craft-blog-post/SKILL.md — the mirror (tests/unit/test_opencode_sync.py).
- docs/CONFIG.md — the `output:` default is now blog-dependent; worth one line saying the scaffolder follows the file's existing convention and that `--output` overrides it.
- CHANGELOG.md / version bump to 0.17.0 (spec D9) if phase 6 owns it.
- docs/acceptance/matrix.yaml BPC-5 (key/output defaults): now verified in CI. status ci, levels.unit -> blog-craft:tests/unit/test_blog_post_create.py. Tests: test_key_override_names_entry_hint_and_cover, test_key_defaults_to_series_number, test_bad_key_rejected, test_output_default_is_the_bundle_when_the_file_says_so, test_output_default_is_the_bundle_under_site_dir, test_output_default_stays_output_dir_for_a_static_blog, test_output_default_stays_output_dir_with_no_entries, test_output_flag_beats_detection_in_both_shapes, test_bundle_default_and_key_override_compose (plus the output-style half in tests/unit/test_prompts_append.py).

`fr plan edit --complete-phase 4` warns about BPC-5 accordingly. Same shape as the BPC-1..4 debt recorded in phases 2 and 3: phases share one branch and one PR, so the repo-wide same-PR backfill rule is met as long as phase 6 does this.
