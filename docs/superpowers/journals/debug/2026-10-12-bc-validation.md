# Journal: 2026-10-12-bc-validation

<!-- fr:journal kind=repro scope=debug id=0be89d12eb96 created=2026-10-11T23:43:05+00:00 -->
### 0be89d12eb96 · repro · All three #68 gaps reproduce on origin/main 92c0d5f

Repro (python, tools/ on path): validate_config accepts series key "" , key "my papers", and two content_type: papers entries (no series error). glossary_scan.candidates proposes OSS and LR inside a hand-written <pre class="mermaid"> block (lines 4-5). A blog-defined renderer shortcode ({{< vega >}}OSS{{< /vega >}}) has its body proposed with no way to declare it opaque — OPAQUE_BODY_SHORTCODES is a module frozenset read by no config.

<!-- fr:journal kind=root-cause scope=debug id=3196b42f7edf created=2026-10-11T23:43:12+00:00 -->
### 3196b42f7edf · root-cause · Each guard trusts a closed/under-specified input: series key presence-only, opaque regions = fixed shortcode-name set

Single class (#68 own framing: fix narrower than the bug). (1) validate_config.py:302 checks only that key exists, but the key is interpolated into a CI shell glob (blog-ci.yml.tmpl:31,72) and a content path, so it must be a non-empty slug, and papers must be unique (last-wins silently). (2)+(3) glossary_scan._OPAQUE_BODY is built once from OPAQUE_BODY_SHORTCODES; the opaque category is "content another parser consumes", but the seam only enumerates shipped shortcode names — raw <pre class="mermaid"> HTML and blog shortcodes fall outside it. _INLINE_PATTERNS excludes the <pre> tag only, not its body.
