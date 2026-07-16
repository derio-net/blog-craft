# Build-time Mermaid syntax validator

- **Issue:** derio-net/blog-craft#27
- **Branch:** `feat/mermaid-validator`
- **Date:** 2026-07-16
- **Type:** feature (validator + config + CI wiring + docs + tests)

## Goal

Catch common Mermaid syntax errors at build time — with `file:line` — instead
of contributors discovering dead diagrams by opening the page. A broken fence
renders as a dead code block on *any* page type.

## Operator decisions (batched Q&A, 2026-07-16)

1. **Standalone, all content.** A new `tools/validate_mermaid.py` lints
   ` ```mermaid ` fences in ANY `index.md` (posts + explainers + papers), wired
   as its own CI step over `content/docs/*/*/index.md`. Pure-Python regex
   linter — no node/mmdc toolchain. Broader than folding into the posts-only
   educational gate (which would miss explainer + paper diagrams).
2. **On by default.** Config flag `quality.mermaid_syntax` (bool) — **absent →
   on**. A blog opts out with `quality.mermaid_syntax: false`.
3. **Blocking.** When enabled, a syntax error fails CI (a syntax error = a
   diagram that renders dead).

## Design

### `tools/validate_mermaid.py` (+ byte-mirror)

Follows the `validate_explainers.py`/`validate_papers.py` library+CLI shape:

- `lint_mermaid_block(src: str) -> list[tuple[int, str]]` — returns
  `(line_offset_within_block, message)` for each issue. Rules (v1, high
  confidence, low false-positive):
  - **R1 subgraph-targeting edge** — collect `subgraph <id>` ids; flag any edge
    (`-->`, `---`, `-.->`, `==>`, `--o`, `--x`, …) whose endpoint token is a
    subgraph id (invalid in Mermaid).
  - **R2 bare `<br>`** — `<br>` not written `<br/>` / `<br />` (Hextra's bundled
    Mermaid wants the self-closed form); suggest `<br/>`.
  - **R3 unbalanced brackets** — per block, after stripping quoted spans, the
    counts of `[]`, `()`, `{}` must each balance (an unquoted stray bracket in a
    node label breaks the parse). Reported at the block's opening-fence line.
  - Must NOT false-positive on valid constructs: `%%{init: {...}}%%` directives
    (balanced braces), `subgraph id [Title]`, short edge labels `-->|logs|`.
- `find_mermaid_blocks(md: str) -> list[tuple[int, str]]` — `(start_line, src)`
  for each fence, tracking real 1-based line numbers into the source file.
- `validate_file(path, md) -> list[str]` — `"<path>:<line>: <message>"` strings.
- CLI: `validate_mermaid.py --config <.blog-craft.yaml> <index.md>...`. Reads
  `quality.mermaid_syntax`; **absent/true → validate**, **false → print
  "mermaid syntax check disabled" and exit 0**. Exit 1 on any finding.

### Byte-mirror + guard

Ships into blogs, so `templates/hugo-hextra/scripts/validate_mermaid.py` is a
byte-identical copy, and the pair is added to `tests/unit/test_mirrors.py`
`MIRRORS` (the guard #25 established for `validate_educational.py`).

### `tools/validate_config.py`

Add a check: `quality.mermaid_syntax`, if present, must be a bool.

### CI wiring — `templates/hugo-hextra/.github/workflows/blog-ci.yml.tmpl`

A new **unconditional** step (the script self-gates on the flag, so on-by-default
holds even when `quality.enabled` is absent), placed **before "Hugo build"** so
a dead diagram is caught before render:

```
      - name: Validate mermaid syntax
        run: python3 scripts/validate_mermaid.py --config .blog-craft.yaml content/docs/*/*/index.md
```

### `docs/CONFIG.md` §7

Document `quality.mermaid_syntax` (default on, opt-out) and the rule set.

## Test Plan

Pure validator + config + CI wiring; **no deployment** → no post-merge Test
Plan. Verification is the unit suite (`tests/unit/test_mermaid_validator.py`).

### Unit tests

- clean diagram (subgraphs, edge labels, `%%{init}%%`, `<br/>`) → no findings.
- R1: `subgraph db ... end` then `A --> db` → flagged; edge between real nodes
  inside/around a subgraph (not the id) → clean.
- R2: `A["x<br>y"]` → flagged; `<br/>` and `<br />` → clean.
- R3: `A[label with ] extra` → flagged; `A["text with ] in quotes"]` → clean;
  `%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%` → clean.
- `find_mermaid_blocks` reports correct 1-based line numbers into the file.
- CLI: a file with a bad diagram → exit 1 + `path:line:` message; clean → exit 0.
- flag: `quality.mermaid_syntax: false` → exit 0 "disabled" even with a bad
  diagram; absent → validates (on by default).
- mirror pair byte-identical.

## Acceptance rows (matrix backfill — same PR)

- **MERM-1** — "validate_mermaid flags a subgraph-targeting edge with file:line
  and fails CI" — `unit=blog-craft:tests/unit/test_mermaid_validator.py`, ci.
- **MERM-2** — "quality.mermaid_syntax: false disables the mermaid syntax
  gate" — `unit=blog-craft:tests/unit/test_mermaid_validator.py`, ci.

## Out of scope

- A full Mermaid parser / mmdc toolchain (regex linter only).
- Speculative "deprecated v11 construct" rules beyond the three high-confidence
  checks (the rule set is extensible; start conservative to avoid false CI
  failures).
