# Explainers standalone mode — implementation plan

Spec: `docs/superpowers/specs/2026-07-14--explainers--standalone-design.md`

Two phases, sequential. Extends the parent `explainers` content-type without
changing blog-mode behavior.

## Phase 1: Tooling

Scaffold `--standalone` flag + new `render_explainer.py` tool.

Tasks:
1. `scaffold-explainer.sh` — add `--standalone`, `--output`, `--target`,
   `--weight-offset` flags. Standalone mode writes a markdown file (not a
   Hugo bundle), records `standalone: true` and `target: <path>` in
   frontmatter, skips `--config` requirement.
2. `render_explainer.py` — new tool: parse frontmatter, convert markdown
   body to HTML via `markdown` library, wrap in themed template (3 built-in
   themes: light/dark/minimal, plus custom CSS via `--style` path).
   Self-contained output: inline CSS, Mermaid JS from CDN for mermaid fences.
3. Template mirror + `test_mirrors.py` entry for `render_explainer.py`.

## Phase 2: Docs + tests + verification

Tasks:
1. `skills/explainers/SKILL.md` — add "Standalone mode" section with
   parallel lifecycle table and style customization docs.
2. Test files:
   - Extend `test_scaffold_explainer.py` with standalone scaffold tests.
   - New `test_explainers_standalone.py` with render script tests.
3. Full-suite verification + self-review.
