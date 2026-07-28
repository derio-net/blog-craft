# Journal: 2026-07-27-humanize-writing

<!-- fr:journal kind=decision scope=spec id=dec-symptoms created=2026-07-27T21:39:54 -->
### dec-symptoms · decision · Primary symptom: session-timeline structure, not surface tics

Operator: posts read like a session's timeline — too narrow, no broad-picture consideration, no thought to reader takeaway. Beginning must grow when the meat is deeply technical/idiosyncratic. Confirmed against frank building/36-metrics-api.

<!-- fr:journal kind=decision scope=spec id=dec-steps-first created=2026-07-27T21:40:06 -->
### dec-steps-first · decision · Reader-arc adopted, but steps-first survives

Diagnosis accepted 'mostly, but keep steps-first': landscape beginning + what-transfers ending, mode-conditional (thick for building/tutorial, thin for operating how-to/reference); the 2am reader outranks the learning reader.

<!-- fr:journal kind=decision scope=spec id=dec-vendor created=2026-07-27T21:40:21 -->
### dec-vendor · decision · AI-tells catalog vendored into blog-craft

Operator chose vendoring (credited to @blader humanizer + WikiProject AI Cleanup) over referencing the user-level skill — blog-craft ships to multiple blogs and OpenCode; install-local deps would be silently absent.

<!-- fr:journal kind=decision scope=spec id=dec-lint created=2026-07-27T21:40:33 -->
### dec-lint · decision · Lint is warnings-first

Operator chose lint-as-warnings: AI-vocabulary hits fail; density metrics (em-dash, parallelism, rule-of-three), cliche conclusions, missing what-transfers section warn. Thresholds/severities in quality.lint, seeded.

<!-- fr:journal kind=decision scope=spec id=dec-approach created=2026-07-27T21:40:47 -->
### dec-approach · decision · Approach A+B; outline-first inversion rejected

Methodology amendments (A) + blind cold-reader editor subagent (B). C-lite (draft landscape before consulting chronology) explicitly not adopted.

<!-- fr:journal kind=review scope=spec id=rev-spec-1 created=2026-07-27T21:43:03 -->
### rev-spec-1 · review · Spec reviewed against codebase; two ambiguities fixed

Verified: validate_educational.py library shape (validate_post/gate dict), quality.gate precedent, agents/post-researcher.md dispatch precedent, skill-contract grep tests (test_batch_gate.py), fixtures layout. Fixed in spec: (1) single-source mechanism concretized as fenced YAML block in ai-tells.md parsed by the validator; (2) mode-conditional lint checks key off diataxis frontmatter, not series names.
