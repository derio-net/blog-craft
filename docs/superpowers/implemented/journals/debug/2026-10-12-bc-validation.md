# Journal: 2026-10-12-bc-validation

<!-- fr:journal kind=repro scope=debug id=0be89d12eb96 created=2026-10-11T23:43:05+00:00 -->
### 0be89d12eb96 · repro · All three #68 gaps reproduce on origin/main 92c0d5f

Repro (python, tools/ on path): validate_config accepts series key "" , key "my papers", and two content_type: papers entries (no series error). glossary_scan.candidates proposes OSS and LR inside a hand-written <pre class="mermaid"> block (lines 4-5). A blog-defined renderer shortcode ({{< vega >}}OSS{{< /vega >}}) has its body proposed with no way to declare it opaque — OPAQUE_BODY_SHORTCODES is a module frozenset read by no config.

<!-- fr:journal kind=root-cause scope=debug id=3196b42f7edf created=2026-10-11T23:43:12+00:00 -->
### 3196b42f7edf · root-cause · Each guard trusts a closed/under-specified input: series key presence-only, opaque regions = fixed shortcode-name set

Single class (#68 own framing: fix narrower than the bug). (1) validate_config.py:302 checks only that key exists, but the key is interpolated into a CI shell glob (blog-ci.yml.tmpl:31,72) and a content path, so it must be a non-empty slug, and papers must be unique (last-wins silently). (2)+(3) glossary_scan._OPAQUE_BODY is built once from OPAQUE_BODY_SHORTCODES; the opaque category is "content another parser consumes", but the seam only enumerates shipped shortcode names — raw <pre class="mermaid"> HTML and blog shortcodes fall outside it. _INLINE_PATTERNS excludes the <pre> tag only, not its body.

<!-- fr:journal kind=finding scope=debug id=01277392cc71 created=2026-10-11T23:51:53+00:00 state=fixed -->
### 01277392cc71 · finding [fixed] · Series key slug/uniqueness/one-papers check, raw mermaid <pre> opaque region, declarable opaque shortcodes

Failing tests first (c111940: 24 red across test_config_schema, test_ci_template, test_glossary_opaque_bodies), then the fix. validate_config: SERIES_KEY_RE slug, duplicate key, >1 papers series. blog-ci.yml.tmpl: first non-empty papers key wins (was last, and an empty/missing key leaked into the glob). glossary_scan: RAW_MERMAID_PRE pattern (whole class token, tempered body, unclosed opener excludes nothing) added to _opaque_body_patterns(extra), cached per name set; opaque_shortcodes threaded through excluded_spans/candidates/misplaced_markers/scan_file/apply_file; load_opaque_shortcodes(config) used by all three CLIs. Template script copies synced. Swept every fixture + frank config: none newly rejected. Rows CFG-KEY-1, GL-13.

<!-- fr:journal kind=review scope=debug id=db5dff134288 created=2026-10-11T23:52:14+00:00 -->
### db5dff134288 · review · Self-review of the full diff: no findings requiring change

Checked: regex edge cases (whole-token mermaid class, single/double quotes, any attr order, case-insensitive </PRE>, unclosed opener excludes nothing, opener in code = documentation); lru_cache keyed on frozenset; malformed config value degrades to none-declared in the loader while validate_config reports it; template first-non-empty key matches scaffold-paper.sh/validate_papers; template script copies byte-identical to tools/; opencode mirror regenerated. Accepted trade-off (no change): an attribute like data-class="mermaid" also matches \bclass — fails safe (over-excludes). Version 0.22.7 chosen above #94 (0.22.5) and #95 (0.22.6); reconcile at merge if order differs.
