# Journal: 2026-10-12-bc-validation

<!-- fr:journal kind=repro scope=debug id=0be89d12eb96 created=2026-10-11T23:43:05+00:00 -->
### 0be89d12eb96 · repro · All three #68 gaps reproduce on origin/main 92c0d5f

Repro (python, tools/ on path): validate_config accepts series key "" , key "my papers", and two content_type: papers entries (no series error). glossary_scan.candidates proposes OSS and LR inside a hand-written <pre class="mermaid"> block (lines 4-5). A blog-defined renderer shortcode ({{< vega >}}OSS{{< /vega >}}) has its body proposed with no way to declare it opaque — OPAQUE_BODY_SHORTCODES is a module frozenset read by no config.
