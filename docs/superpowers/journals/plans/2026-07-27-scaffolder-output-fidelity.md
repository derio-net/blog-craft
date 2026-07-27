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

<!-- fr:journal kind=discovery scope=plan id=17d636c58397 created=2026-07-27T22:36:08 phase=5 -->
### 17d636c58397 · discovery · rendered_text wiring: $display moved INSIDE the else branch, and the index sorts on ONE composite key (phase 5)

Three seams that are not visible from the plan text.

1. In abbr.html `$display` could not merely move below the `$entry` lookup — it had to move INSIDE the `{{- else -}}` branch. `or (.Get 1) $entry.rendered_text $key` evaluated between the lookup and the `if not $entry` guard reads `.rendered_text` off a nil entry, which is a Go template error ("nil pointer evaluating interface {}.rendered_text") and would pre-empt the errorf that names the file and the key. The guard still fires first, and the unknown-key build failure message is byte-unchanged.

2. glossary-index.html now builds a slice of `dict "sortkey" … "display" … "entry" …` and does `sort $rows "sortkey"`, where sortkey is `printf "%s\x1f%s" $display $k`. Two reasons, both load-bearing:
   - Hugo's `sort` is not documented as stable, so `sort (sort $rows "key") "display"` cannot be relied on for the key tiebreaker. One composite string is a total order by construction.
   - The separator has to sort BELOW every printable character. With `\x1f` (US, 0x1f): display "GC" + key "GC" -> "GC\x1f GC" vs display "GCX" -> "GCX\x1f…"; 0x1f < 'X', so display order wins. A high separator like "~" (0x7e) would invert that and order "GCX" before "GC".
   Where no entry carries rendered_text, display == key and this is exactly the previous key sort — hence the untouched assertion at test_glossary_index_lists_every_term_alphabetically.
   Side note: the template's old explicit `sort $keys` was already belt-and-braces (Go's template range sorts map keys), but explicitness is kept.

3. `$id`, the anchor name and `anchorize` are UNTOUCHED and still key-derived. Verified in the built HTML with both senses on one page: `id="abbr-gc-1"` / `--abbr-gc-1` for GC and `id="abbr-gc_goatcounter-0"` / `--abbr-gc_goatcounter-0` for GC_GOATCOUNTER — two anchors, no collision, #49's placement fix intact. anchorize lowercases the key and KEEPS the underscore, which is also why "GC_GOATCOUNTER" (uppercase) appearing nowhere in the page is a usable assertion.

Emitted HTML, verbatim (registry: GC/Garbage Collection, GC_GOATCOUNTER/rendered_text GC/GoatCounter):

trigger for `{{< abbr "GC_GOATCOUNTER" >}}`
<button type="button" class="abbr-trigger" popovertarget="abbr-gc_goatcounter-0" style="anchor-name: --abbr-gc_goatcounter-0" aria-label="Expand abbreviation: GC"><abbr title="GoatCounter">GC</abbr></button><span popover id="abbr-gc_goatcounter-0" class="abbr-panel" style="position-anchor: --abbr-gc_goatcounter-0"><strong class="abbr-name">GoatCounter</strong><span class="abbr-desc">The analytics tool behind the numbers.</span></span>

index rows
  <dt class="glossary-term"><abbr title="Garbage Collection">GC</abbr> — Garbage Collection</dt>
  <dt class="glossary-term"><abbr title="GoatCounter">GC</abbr> — GoatCounter</dt>

The two senses are adjacent and each row's expansion is what disambiguates them for the reader — the key is gone from both surfaces, aria-label included.

<!-- fr:journal kind=discovery scope=plan id=f7c14c293257 created=2026-07-27T22:36:28 phase=5 -->
### f7c14c293257 · discovery · Validator: only the TYPE half of the rendered_text tests was diagnostic RED; the quote check is about hand-marking, not the data path (phase 5)

TDD evidence, split honestly.

Diagnostic RED (4 of 7 validator tests): non-string, empty, whitespace-only and quote-bearing rendered_text all validated CLEAN before the change — `_REQUIRED` (tools/validate_glossary.py:34) is a whitelist of REQUIRED fields, so an unknown key was already accepted silently. That is the whole reason to touch the validator; the field never needed permission.

Passed from the start, kept as regression guards, not evidence:
- a well-formed `rendered_text: GC` validates clean;
- GC + GC_GOATCOUNTER SHARING `rendered_text: GC` validates clean — a shared display text must never be reported, it is the feature;
- keys differing only in case are still an error even when both carry the same rendered_text (:72-79 untouched).

Same split in the Hugo tests (4 diagnostic RED of 6): `{{< abbr "GC_GOATCOUNTER" "GCs" >}}` already rendered ">GCs<" (arg 1 already won), and the id/anchor pair was already key-derived. Both are now pinned.

The quote rejection: `rendered_text` does NOT reach a shortcode argument through any code path today — glossary_apply.py:28-31 builds `{{< abbr "TERM" "DISPLAY" >}}` from the token it MATCHED IN PROSE (glossary_scan candidates), never from the registry field, and abbr.html emits it into an HTML attribute where Hugo escapes a quote to &#34;. It is rejected because the field is the text an operator copies into `{{< abbr "KEY" "TEXT" >}}` when marking the second sense BY HAND (which is the only way the second sense can be marked — see the finding for phase 6), and a quote there emits an unparseable shortcode. The error message says exactly that rather than repeating the key check's wording.

Not done, deliberately: spec §4 line 218 mentions "the type check and the sorted-registry warning". The sorted-registry warning still checks KEY order (`keys != sorted(keys)`), untouched. The registry file is read by an operator as a keyed YAML mapping and GC / GC_GOATCOUNTER sort adjacently as keys anyway; re-basing that warning on display text would ask an operator to sort a file by a field most entries do not have. Plan task 1 lists only the type check as the deliverable. Flagged here in case phase 6's docs want to say something about file order.

<!-- fr:journal kind=finding scope=plan id=c3ade469d220 created=2026-07-27T22:36:45 phase=5 state=open -->
### c3ade469d220 · finding [open] · Phase 6 owes rendered_text docs (SKILL, CONFIG §9) and matrix rows GL-10 + GL-11, both satisfied in CI now (phase 5)

Phase 5 documented `rendered_text` only in the two template header comments and the validator docstring. It touched no skill, not docs/CONFIG.md and not docs/acceptance/matrix.yaml (phase 6 owns all three). Still owed:

- skills/glossary/SKILL.md — the field, the precedence chain (call-site arg 1 › entry.rendered_text › key), and spec D8's honest half: `glossary_apply.py` matches LITERAL TOKENS against registry keys, so it can only ever auto-mark the DEFAULT sense (`GC`). The second sense is marked by hand as `{{< abbr "GC_GOATCOUNTER" >}}` — nothing scans for it, and a bare "GC" in prose will be auto-marked as Garbage Collection. That is a workflow instruction, not a footnote: without it the field looks self-applying.
- .opencode/skills/blog-craft-glossary/SKILL.md — the byte-identical mirror (tests/unit/test_opencode_sync.py); re-run scripts/sync-opencode.py.
- docs/CONFIG.md §9 — `rendered_text` in the entry schema (optional, non-empty string, no double quote), defaulting to the key; two entries may share one; the index sorts by display text with the key as tiebreaker. Worth one sentence that keys stay the identifier (anchors and the marker argument both use the key).
- docs/acceptance/matrix.yaml: GL-10 and GL-11 are both now verified in CI and only need refs written down. `fr plan edit --complete-phase 5` warns accordingly.
  - GL-10 (two expansions both render as the abbreviation, inline and in the index): status ci, levels.unit -> blog-craft:tests/unit/test_glossary_hugo.py. Tests: test_rendered_text_is_shown_instead_of_the_key, test_rendered_text_is_used_in_the_aria_label, test_call_site_argument_still_beats_rendered_text, test_rendered_text_does_not_move_the_id_or_the_anchor, test_glossary_index_shows_rendered_text_never_the_key, test_glossary_index_sorts_on_the_resolved_text_keeping_senses_adjacent.
  - GL-11 (validator accepts rendered_text typed, never rejects a shared one): status ci, levels.unit -> blog-craft:tests/unit/test_glossary_validator.py. Tests: test_rendered_text_is_optional_and_a_string_is_fine, test_two_entries_may_share_a_rendered_text, test_non_string_rendered_text_is_an_error, test_empty_rendered_text_is_an_error, test_whitespace_only_rendered_text_is_an_error, test_rendered_text_containing_a_quote_is_an_error, test_case_colliding_keys_are_still_an_error_with_rendered_text.
- CHANGELOG 0.17.0 / tools/bump_version.py minor (spec D9) if phase 6 owns it: this phase touched tools/ and templates/, both under check_version_bump_needed.py:22's required prefixes.

No migration is owed: templates/manifest.yaml classes `layouts/**` and `scripts/**` as framework (an /update ships the new templates) and `data/**` as content (the operator's registry is untouched), and the field is purely additive.

<!-- fr:journal kind=discovery scope=plan id=p6-repro-end-to-end created=2026-07-27T22:50:49 phase=6 -->
### p6-repro-end-to-end · discovery · The issue's exact reproduction now passes on a column-0 frank-shaped blog — all three checks, verbatim (phase 6)

P6.T3.S2, run against a throwaway blog with `site_dir: blog`, `series_index.layers: [obs, bld]`, and the issue s own seed — an `images:` sequence at COLUMN 0 plus one real entry (`existing-01`, static-shaped `output`).

The issue s literal command (`--no-generate operating 30 silent-failure`, no new flags) exits 0 and:

(a) the file PARSES — `entries = 2`, keys `[existing-01, operating-30]`. The appended entry sits at column 0, matching the file s own sequence, and lines 1-6 (the seed) are byte-identical. Before the fix this same seed produced `expected <block end>, but found -`.
(b) `generate-images.py --config .blog-craft.yaml --print-prompt operating-30` — the Step 6 preview the issue reports as impossible — RUNS, emitting the composed prompt (base_character + scene). The scaffolder prints that exact command with the resolved key substituted.
(c) frontmatter carries `series: ["operating"]`, `layer: TODO` (with the two-line stderr WARNING naming `obs, bld`), and `tags: []  # TODO: add tags`.

`output:` resolved to `blog/static/images/operating-30-cover.png` — output_dir, not the bundle, because the seed entry is static-shaped. That is D7 working as designed: the reporting blog keeps the default it already had.

A second run with the flags this release adds (`--layer obs --tag operations --tag slo --key ops-31-noisy-alerts`) appends a THIRD entry to the same file (still parses; keys `[existing-01, operating-30, ops-31-noisy-alerts]`), `--print-prompt ops-31-noisy-alerts` runs, and the frontmatter is `series: ["operating"]` / `layer: obs` / `tags: ["operations", "slo"]`. The `--key` override reaches the entry key, the cover basename and both printed hints; the bundle directory is still `31-noisy-alerts` — the key does not leak into a per-post path.

<!-- fr:journal kind=discovery scope=plan id=p6-docs-were-more-than-flag-lists created=2026-07-27T22:51:06 phase=6 -->
### p6-docs-were-more-than-flag-lists · discovery · The doc debt was three false promises, not three missing flag lists (phase 6)

Phases 3-5 each recorded "phase 6 owes docs". What the edits actually turned out to be:

1. `skills/blog-post/SKILL.md` Step 8 item 4 PROMISED the series overview "lists the new post automatically" while the scaffolder emitted no `series` — the promise is the reason nobody checked. It now says the overview lists the post *because* the frontmatter carries `series`, and names 0.17.0 as the version that made it true. The stale `--output` sentence had the mirror-image problem: it told the agent to "check existing entries in <image.prompts_file>" by hand for something the helper now detects, so it read as the only lever when it is now an override.
2. `--key` needed a SKILL STEP, not a flag mention (phase 4 was right about this). Step 8 now carries a "Check the key convention before you run it" paragraph that says why no config field can supply the abbreviation and what to read instead. Step 6 (which is the step that actually RUNS the helper) had to be re-pointed at Step 8s invocation verbatim, or the check would sit in a block the agent reads after the fact.
3. Every `<series>-<number>` in the generate/preview/regen commands (Steps 6, 8, 9) was wrong the moment `--key` existed. They are now `<key>`, with one sentence saying the helper prints the resolved command to copy.
4. `skills/glossary/SKILL.md`: the apply caveat went into Step 4 (where the entry is written) AND Step 6 (where the markers are inserted, and where the author has to re-point them by hand), not into Notes. In Notes it would be a footnote about a workflow the agent has already got wrong.

Also added beyond the plan text: `docs/CONFIG.md` §5 now says `series_index.layers` is the registry `--layer` is validated against (it previously read as gen-layer-palette.py-only input), and §4.1 documents both the blog-dependent `output:` default and that `key` is never detected. The §9 CI-gate table gained the `rendered_text` error row plus an explicit "two entries sharing a rendered_text — never reported" row, because the absence of a rule is not visible in a table of rules.

<!-- fr:journal kind=discovery scope=plan id=p6-acceptance-report-drift created=2026-07-27T22:51:18 phase=6 -->
### p6-acceptance-report-drift · discovery · fr acceptance check exit 1 on report drift, not on the row flips — the report set is committed and must be regenerated (phase 6)

Flipping BPC-1..5 + GL-10/11 to `ci` with real refs left `fr acceptance check` at EXIT 1 — but not for anything about the rows. The three failures were `report drift: docs/acceptance/report_{local.html,linked.html,linked.md} is missing or stale vs docs/acceptance/matrix.yaml`. This repo COMMITS the generated report set, so any matrix.yaml edit owes `fr acceptance report --deterministic` in the same commit. Not mentioned in the plan step, and easy to misread as a bad ref.

After regenerating: exit 0, `57 rows OK ({not-implemented: 6, ci: 49, skipped: 2})`. None of BPC-1..5 / GL-10 / GL-11 appear as warnings; the 6 remaining not-implemented are the pre-existing manual/post-merge rows (OC-1, OC-2, OC-5, IMG-OPT-1, IMG-COMP-8, IMG-COMP-9) and the 2 skipped are GL-3/GL-9 (browser-walk evidence CI has no layout engine for).

The `notes` rewrite was the substantive half. The placeholder notes said "Awaits X"; they now record which named tests pin what, and specifically which tests were DIAGNOSTIC versus which are regression guards — that distinction is in the phase 1-5 journal entries and would have been lost the moment those entries scrolled out of anyone s context. BPC-1 notes name the column-0 and no-trailing-newline seeds as the diagnostic ones and record that the pre-existing empty-sequence seed could see neither; GL-11 notes record that a malformed `rendered_text` validated CLEAN before the change because `_REQUIRED` is a required-field whitelist, not an allowlist.

<!-- fr:journal kind=finding scope=plan id=p6-deferred-debt-paid created=2026-07-27T22:52:11 phase=6 state=fixed -->
### p6-deferred-debt-paid · finding [fixed] · All five deferred phase 2-5 findings are paid; only p1-keep-chomp-seam remains open (phase 6)

Closing entry for the debt phases 2-5 recorded against phase 6. `fr journal add` with an existing `--id` is a NO-OP (it does not rewrite `state=open`), so those five entries still RENDER as open — this entry is the authoritative state.

PAID:
- `p2-bpc12-backfill-deferred` (phase 2) — BPC-1 and BPC-2 flipped to `ci` with unit refs `tests/unit/test_prompts_append.py` + `tests/unit/test_blog_post_create.py` and int ref `tests/smoke-blog-post.sh`.
- `d842482e5770` (phase 3) — `--layer` / `--tag` / `layer: TODO` / the tags-comment departure are now in `skills/blog-post/SKILL.md` (Step 4 asks for both; Step 8 shows the flags and the frontmatter order) and `docs/CONFIG.md` §5.
- `dd2022e25525` (phase 3) — BPC-3 and BPC-4 flipped to `ci`, notes naming the 4 + 9 tests.
- `b56820abcc36` (phase 4) — `--key` is a SKILL STEP in Step 8, the detected `output:` default is in `docs/CONFIG.md` §4.1, BPC-5 flipped to `ci`, and 0.17.0 + the CHANGELOG section shipped.
- `c3ade469d220` (phase 5) — `rendered_text` is in `skills/glossary/SKILL.md` Step 4 (schema + precedence chain) and Step 6 (the by-hand marking of the second sense) and in `docs/CONFIG.md` §9; both OpenCode mirrors re-synced by `scripts/sync-opencode.py`; GL-10 and GL-11 flipped to `ci`.

STILL OPEN, deliberately: `p1-keep-chomp-seam` (phase 1) — the seam normalisation (`rstrip(chr(10)) + chr(10)`) drops trailing BLANK lines, which a final entry ending in a `|+` KEPT block scalar would notice. No blog-craft template or tool emits `|+`, and the D2 verification checks the entry count and last key rather than scalar contents, so it would be silent. Left as a recorded edge; the fix, if it ever matters, is to strip only the trailing newlines beyond one when the file does not end inside a kept scalar. Not documented in CONFIG or the skill, because telling operators not to end a prompts file with a `|+` scalar is worse than the edge case.

Also unchanged by design (phase 5, `f7c14c293257`): the validator sorted-registry warning still checks KEY order, not display order. `docs/CONFIG.md` §9 now says "alphabetically sorted **by key**" explicitly so the two are not confused.

<!-- fr:journal kind=finding scope=plan id=r-f1-atomic-append created=2026-07-27T23:42:45 state=fixed -->
### r-f1-atomic-append · finding [fixed] · F1: the append was truncate-then-write — a short write destroyed the operator's entries file

tools/prompts_append.py:125 did `path.write_bytes(new.encode())`, which truncates and then writes. A write that could not complete (ENOSPC, disk quota, RLIMIT_FSIZE, SIGINT, OOM) left the operator's ~1900-line file as a truncated prefix of itself, `_restore` was unreachable from that branch, the caller got a raw traceback with exit 1 instead of the promised exit 2, and `_restore`'s own `write_bytes` was unguarded — a failed restore destroyed the only remaining copy, since the original bytes lived solely in the dying process's memory. `after = load_entries(new)` verified the IN-MEMORY string, so a short write was invisible to D2's verification. This falsified spec D2, the module docstring, and skills/blog-post/SKILL.md:29's "on **any** failure it restores the original bytes".

Reproduction (a 4839-byte column-0 prompts file, 40 entries, RLIMIT_FSIZE 2048):

    $ bash -c 'ulimit -f 2; python3 tools/prompts_append.py append --file big.yaml --key newkey --entry-file entry.txt'
BEFORE: OSError: [Errno 27] File too large  (traceback through pathlib write_bytes), rc=1, big.yaml 4839 -> 2048 bytes, DIFFERENT.
AFTER:  prompts_append: big.yaml: the append could not be written ([Errno 27] File too large) — the file is unchanged, nothing was written in place
        rc=2, big.yaml 4839 bytes, md5 identical, no temp file left.

Fix: `_write_atomically()` — mkstemp a sibling temp file in the SAME directory (os.replace is only atomic within one filesystem), raw `os.write` in a loop (a buffered writer defers the failure into a `close()` the caller cannot see), fsync, then `os.replace`. Three details worth keeping: (1) the mode is copied off the original with fchmod, because mkstemp creates 0600 and a prompts file in a git repo is 0644; (2) the replace goes through `os.path.realpath(path)`, so a symlinked prompts file keeps its link instead of being replaced by a regular file — verified by hand; (3) the temp file is unlinked in a `finally` on every path (ENOENT ignored on the success path). Verification now re-READS the bytes from disk, compares them to the payload BEFORE parsing (so a short write reports as a short write, not as "the append broke the file"), and `_restore` writes atomically too and reports clearly if the restore itself fails.

Pinned by tests/unit/test_prompts_append.py::test_a_write_that_cannot_complete_leaves_the_file_byte_identical (the `ulimit -f 2` reproduction, skipped gracefully where `ulimit -f` is unavailable; the child runs with `-B` so bytecode caches cannot hit the same limit) plus test_a_healthy_append_leaves_no_temp_file_behind. The test asserts the file first and the returncode second — the file is the acceptance, the exit code is the message.

<!-- fr:journal kind=finding scope=plan id=r-f2-locale-reads created=2026-07-27T23:43:09 state=fixed -->
### r-f2-locale-reads · finding [fixed] · F2: locale-dependent read_text() — loud in append, SILENTLY WRONG in output-style

The module used `read_bytes()` + `.decode()` for the target file but bare `Path.read_text()` (LOCALE encoding) for the entry block (:120) and for the output-style read (:158). blog-post-create.sh writes a literal em dash into every entry's `description:`, so the entry block is ALWAYS non-ASCII — this is every scaffold under a non-UTF-8 locale, not an edge case.

- :120 raised an unhandled UnicodeDecodeError -> traceback, exit 1 (inconsistent with the sibling load_entries path, which catches it).
- :158-160 was worse because it was SILENT: `except (OSError, yaml.YAMLError, ValueError)` swallows UnicodeDecodeError (a ValueError subclass) and printed `output_dir`, so a real bundle-style blog got the WRONG cover path — written where Hugo's page-resources lookup never looks — with no diagnostic. Exactly the silent-wrong-output class D7 exists to eliminate.

Reproduced (em dash in `description:`, single entry under content/):
  LC_ALL=C PYTHONUTF8=0 python3 tools/prompts_append.py output-style --file em.yaml --site-prefix ""
  BEFORE: output_dir (rc 0) / with UTF-8: bundle.   AFTER: bundle either way.
  append under the same env BEFORE: UnicodeDecodeError traceback, rc 1. AFTER: rc 0.

Fix: `encoding="utf-8"` on both reads; the entry-block read is wrapped so a genuinely non-UTF-8 block fails with a message naming the file instead of a traceback.

Environment note for anyone reproducing: `LC_ALL=C` alone is not enough on a system with C.UTF-8 — PEP 538 locale coercion would quietly make the read UTF-8 and hide the bug. The tests set PYTHONUTF8=0 (defeats PEP 540) AND PYTHONCOERCECLOCALE=0 (defeats PEP 538), which is what makes `LC_ALL=C` really mean ASCII.

Pinned by tests/unit/test_prompts_append.py::test_a_non_ascii_entry_block_appends_under_a_c_locale and ::test_detection_is_not_locale_dependent (the silent half — asserts `bundle`, which is what a swallowed decode error turns into `output_dir`).

<!-- fr:journal kind=finding scope=plan id=r-f3-all-or-nothing created=2026-07-27T23:43:09 state=fixed -->
### r-f3-all-or-nothing · finding [fixed] · F3: a refused append left a half-scaffolded post; prompts_append.py gained a "check" subcommand

The page bundle was written (blog-post-create.sh:223-255) BEFORE the append ran (:309), so any refusal exited 2 with content/docs/<series>/<NN>-<slug>/index.md already on disk and no matching entry — the operator had to know to go and delete it.

Fix: a third subcommand, `prompts_append.py check --file <prompts.yaml>`, which answers "would an append be accepted?" and never writes. It shares one `_appendability_problem()` helper with `cmd_append`, so the two can never disagree about what is refusable — `append` still runs the same checks itself; `check` is an early look, not a substitute. The shell calls it immediately after the PROMPTS_YAML / PROMPTS_APPEND existence guards, i.e. before `mkdir -p`, and `set -euo pipefail` carries its exit 2. The scaffold is now all-or-nothing.

Pinned by tests/unit/test_blog_post_create.py::test_a_refused_append_leaves_no_half_scaffolded_post (seeded with the corruption from #65: exit non-zero, prompts file byte-identical, AND the bundle directory does not exist) plus four `check` cases in tests/unit/test_prompts_append.py. Those `check` cases assert the file name appears in stderr, not merely returncode != 0 — an unknown subcommand also exits 2 via argparse, which is the same vacuity F6 was about.

<!-- fr:journal kind=finding scope=plan id=r-f4-key-retyping created=2026-07-27T23:44:03 state=fixed -->
### r-f4-key-retyping · finding [fixed] · F4: the --key guard admitted values YAML retypes (1.5, 123, 0x1f, no, on, y)

blog-post-create.sh:85's shape guard `^[A-Za-z0-9][A-Za-z0-9_.-]*$` admits 1.5, 123, 0x1f, no, on, y, true, null. The key is emitted BARE at :277, so YAML reads it back as a float/int/bool/null and the D2 verification fails with a message that blames the prompts file for the flag's value. Verbatim before:

    prompts_append: .../prompt_for_images.yaml: the last entry is not the appended key '1.5' (found 1.5) — restored the pre-append bytes

Fix, at the flag, naming the flag: after the shape check, require at least one ASCII letter (kills 1.5, 123, 017, and any all-digit key) and reject the YAML 1.1 boolean/null words plus 0x/0b prefixes (which pass the letter test but retype). Implemented with `tr '[:upper:]' '[:lower:]'` + a `case`, deliberately NOT bash 4's ${var,,} — this script must keep running under macOS's bash 3.2. Requiring a letter slightly over-rejects (a key like `1-2` is a legal YAML string) and that is the intended trade: a key names an entry and every real convention in the field has letters.

Pinned by tests/unit/test_blog_post_create.py::test_key_that_yaml_would_retype_is_rejected (all eight values: non-zero exit, stderr names --key, prompts file untouched) and ::test_a_key_with_digits_and_dots_is_still_accepted (ops-1.5-silent still scaffolds, so the guard costs no real key shape).

<!-- fr:journal kind=finding scope=plan id=r-f5-sort-fixture created=2026-07-27T23:44:04 state=fixed -->
### r-f5-sort-fixture · finding [fixed] · F5: the glossary display-sort test was unpinned and its justifying comment was false

tests/unit/test_glossary_hugo.py::test_glossary_index_sorts_on_the_resolved_text_keeping_senses_adjacent passed under a KEY sort too, because GC < GC_GOATCOUNTER < NUT < SLO in both orders. The comment at :249 ("Sorting on the key would put GC_GOATCOUNTER after NUT") was factually wrong — nothing in REGISTRY sorts between GC and GC_GOATCOUNTER.

Fix: a dedicated SORT_REGISTRY fixture (REGISTRY minus GC_GOATCOUNTER, plus key ZZZ_GC with rendered_text: GC), which genuinely separates the two orders — display sort -> [GC, GC(ZZZ_GC), NUT, SLO]; key sort -> [GC, NUT, SLO, ZZZ_GC]. Comment corrected to state what the fixture proves. REGISTRY itself is untouched, so the five other GL-10 tests keep asserting what they were written for (notably "GC_GOATCOUNTER" not in html).

Verified as a mutation test, not by inspection: with glossary-index.html's sortkey temporarily reverted to `printf "%s\x1f%s" $k $k`, the test FAILS ("At index 1 diff: 'Network UPS Tools' != 'GoatCounter'"); restored, it passes. The shortcode's own comment was reworded in the same pass — it cited the same non-example.

<!-- fr:journal kind=finding scope=plan id=r-f6-key-guard-assertion created=2026-07-27T23:44:04 state=fixed -->
### r-f6-key-guard-assertion · finding [fixed] · F6: test_bad_key_rejected could not tell the guard from an unparsed flag

The test asserted only `returncode != 0`, and every unknown flag also exits 2 ("ERROR: unknown flag"), so it passed against code that had no --key guard at all — while acceptance row BPC-5 cited it as pinning the guard. Fix: assert `"--key" in r.stderr` for every rejected value, which is only true of the guard's own message. The same discipline is now applied to the new `check` cases in tests/unit/test_prompts_append.py (they assert the file name appears in stderr, so an argparse "invalid choice" cannot satisfy them) and BPC-5's matrix notes record why returncode alone is not evidence.

<!-- fr:journal kind=finding scope=plan id=r-f7-images-must-be-last created=2026-07-27T23:44:43 state=fixed -->
### r-f7-images-must-be-last · finding [fixed] · F7: a top-level key after the images: sequence aborted every scaffold with a message that blamed the append

The entry is placed at END OF FILE, so a prompts file with any top-level key after the `images:` sequence made every scaffold fail with `expected <block end>, but found '-'` — the append reported "the append broke the file" for what is actually the file's LAYOUT. Only `images:` is documented, so this is a hand-edited-file scenario, not a field default.

Decision kept from the brief: do NOT move the insertion point. Placing an entry mid-file would put a byte-offset computation into the highest-stakes code path in the repo, to serve a shape no documented file has. Instead the condition is DETECTED and refused up front, with an accurate message.

Detection is textual (`trailing_top_level_key()`), because the parsed document has no column information — same reason `sequence_indent()` is textual (p1-indent-detection-shape). After the `images:` line, a line is offending only if it is non-blank, starts at column 0, is not a comment, and is not a `- ` sequence item. Column-0 content cannot be nested inside the sequence (a block scalar's content must be indented past its key, which is itself indented past a column-0 `- `), so this cannot false-positive on entry bodies. It reports the line number and the key name. `---` / `...` at column 0 would also be refused, which is right: an end-of-file append into a multi-document file is not correct either.

Message: "`settings` is a top-level key at line N, after the `images:` sequence. The entry is placed at end of file, so `images:` must be the last top-level key in the file — move the trailing key(s) above `images:` (or add this entry by hand)."

Because the check lives in `_appendability_problem()`, `check` refuses it too — so the scaffold refuses BEFORE the page bundle is created (see r-f3-all-or-nothing). Pinned by tests/unit/test_prompts_append.py::test_a_top_level_key_after_the_sequence_is_refused_with_an_accurate_message (asserts the offending key name AND that the stderr does NOT say "broke the file"), ::test_a_top_level_key_before_the_sequence_is_fine, ::test_a_comment_after_the_sequence_is_fine, and end to end by tests/unit/test_blog_post_create.py::test_a_trailing_top_level_key_is_refused_up_front_with_an_accurate_message. Documented in docs/CONFIG.md §4.1 ("Keep images: last") and skills/blog-post/SKILL.md Step 8.

<!-- fr:journal kind=finding scope=plan id=r-p1-keep-chomp-seam-paid created=2026-07-27T23:44:43 state=fixed -->
### r-p1-keep-chomp-seam-paid · finding [fixed] · p1-keep-chomp-seam is now PAID: the seam ensures a trailing newline instead of collapsing them

Authoritative closing state for the phase-1 finding `p1-keep-chomp-seam`, which still RENDERS as open because `fr journal add` with an existing --id is a no-op (same mechanism p6-deferred-debt-paid describes).

The seam was `text.rstrip("\n") + "\n"`, which drops trailing BLANK lines. That is value-preserving for `|` and `|-`, but a final entry ending in a `|+` KEPT block scalar loses content, and D2's verification (entry count + last key) does not look at scalar contents, so it would be silent. Measured, before the fix: seeded scene value `an existing scene\n\n` came back as `an existing scene\n` after an append.

Fix, exactly the simplest correct one: only ENSURE a trailing newline — `text if text.endswith("\n") else text + "\n"`. Blank lines between sequence items are legal YAML, so nothing needs collapsing; the newline-less case (the original reason for the normalisation) is still handled.

Two consequences worth recording: (1) the existing no-regression test was renamed from test_trailing_blank_lines_are_normalised to test_trailing_blank_lines_do_not_break_the_append, because "normalised" is no longer what happens — it is a guard that blank lines at the seam still parse; (2) with the collapse gone, `new.startswith(orig)` is now true for a file with trailing blank lines as well, i.e. D1's "every byte above the insertion point stays as the operator wrote it" is now literally true for every shape rather than nearly every shape.

New test: tests/unit/test_prompts_append.py::test_a_kept_block_scalar_keeps_its_trailing_blank_line — seeds `scene: |+` with a trailing blank line and asserts the scalar's value is unchanged after the append (plus the entry count and the byte-prefix).

<!-- fr:journal kind=discovery scope=plan id=r-doc-nits-and-promises created=2026-07-27T23:45:02 -->
### r-doc-nits-and-promises · discovery · Doc corrections shipped with the review fixes, and the one promise that is now true

Three doc surfaces were corrected in the same pass, because each stated something the code did not do:

- tools/blog-post-create.sh:19 called --key the "cover basename". Untrue under the bundle convention (D7), where the cover is always `cover.png`. Reworded: --key is the entry key, the `--only` argument, and the cover filename `<key>-cover.png` ONLY where covers live in image.output_dir.
- skills/blog-post/SKILL.md:29 promised "on **any** failure it restores the original bytes and exits non-zero". Re-checked after F1: it is now TRUE (a write that cannot complete leaves the file byte-identical, and the restore is itself atomic and reports if it fails), so the wording stands — it gained the atomicity, the from-disk verification, the check-before-scaffold ordering and the images:-must-be-last requirement rather than being softened. Step 8's item 2 and the --key paragraph were updated for the same reasons; .opencode/skills/blog-craft-blog-post/SKILL.md re-synced via scripts/sync-opencode.py (tests/unit/test_opencode_sync.py fails on drift).
- docs/CONFIG.md §4.1 gained "Keep images: last" — the entries-file layout requirement F7 introduced, stated where the entries-file schema is documented.

CHANGELOG: no version bump (0.17.0 is unreleased and these fix code shipping in the same release). The 0.17.0 "Fixed" section's own claim — "restores the pre-append bytes and exits non-zero, so a refused append leaves the file byte-identical" — was the promise F1 falsified, so that bullet now describes the temp-file + os.replace swap and the from-disk verification explicitly, and two new bullets cover the all-or-nothing scaffold and the --key retyping guard.

Acceptance matrix: no new rows or status changes (BPC-1/2/5 and GL-10 are already `ci` and already cite these files). The `notes` for BPC-2, BPC-5 and GL-10 were rewritten to record what the new tests pin and, for GL-10, that the sort test was previously unpinned — the registry is only useful if its notes say which tests are diagnostic. Reports regenerated with `fr acceptance report --deterministic`.

Pre-existing and NOT touched: `ruff check tools/ tests/` reports 52 errors (E702/E402/F401/E741/E731) at this commit and reported the same 52 on the parent commit; none are in the four files this work changed (they pass clean). Fixing them is unrelated churn for a review-fix commit, and ruff is not wired into any workflow in .github/workflows.
