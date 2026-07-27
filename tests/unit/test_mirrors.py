"""Mirror guards — files intentionally duplicated must stay byte-identical.

Some tools are both a blog-craft tool (canonical, tested here) AND shipped into a
materialized blog so a plain-python CI / operator can run them without the plugin:
  - compose.py            -> templates/hugo-hextra/scripts/           (every blog)
  - validate_educational  -> templates/hugo-hextra/scripts/           (quality gate on)
  - the papers validators -> templates/content-type-papers/shared/scripts/ (papers on)
  - scaffold-explainer.sh -> templates/content-type-explainers/shared/scripts/ (explainers on)
  - render-explainer.py   -> templates/content-type-explainers/shared/scripts/ (explainers on)
  - validate_glossary.py  -> templates/hugo-hextra/scripts/           (glossary gate)
  - glossary_scan.py      -> templates/hugo-hextra/scripts/           (imported by it)
Keep each pair in sync; edit the tools/ copy and re-mirror.

glossary_scan.py travels with validate_glossary.py because the validator imports
its marker + code-span helpers rather than re-deriving them. A blog's CI has no
plugin on sys.path, so the companion has to ship too.

ai-tells.md travels with validate_educational.py for the same reason: the lint
layer's word lists live in its fenced yaml block, and a materialized blog has
no skills/ tree — load_lint_data() falls back to the sibling scripts/ai-tells.md.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIRRORS = [
    ("tools/compose.py", "templates/hugo-hextra/scripts/compose.py"),
    ("tools/validate_educational.py", "templates/hugo-hextra/scripts/validate_educational.py"),
    ("tools/validate_mermaid.py", "templates/hugo-hextra/scripts/validate_mermaid.py"),
    ("tools/dossier_parser.py", "templates/content-type-papers/shared/scripts/dossier_parser.py"),
    ("tools/validate_papers.py", "templates/content-type-papers/shared/scripts/validate_papers.py"),
    ("tools/validate_dossier.py", "templates/content-type-papers/shared/scripts/validate_dossier.py"),
    ("tools/sync_dossier_to_data.py", "templates/content-type-papers/shared/scripts/sync_dossier_to_data.py"),
    ("tools/scaffold-paper.sh", "templates/content-type-papers/shared/scripts/scaffold-paper.sh"),
    ("tools/scaffold-explainer.sh", "templates/content-type-explainers/shared/scripts/scaffold-explainer.sh"),
    ("tools/validate_explainers.py", "templates/content-type-explainers/shared/scripts/validate_explainers.py"),
    ("tools/render_explainer.py", "templates/content-type-explainers/shared/scripts/render_explainer.py"),
    ("tools/validate_glossary.py", "templates/hugo-hextra/scripts/validate_glossary.py"),
    ("tools/glossary_scan.py", "templates/hugo-hextra/scripts/glossary_scan.py"),
    ("skills/educational-writing/references/ai-tells.md",
     "templates/hugo-hextra/scripts/ai-tells.md"),
]


def test_mirrors_identical():
    for a, b in MIRRORS:
        pa, pb = os.path.join(ROOT, a), os.path.join(ROOT, b)
        assert open(pa).read() == open(pb).read(), f"{a} and {b} diverged — re-mirror"
