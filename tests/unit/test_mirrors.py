"""Mirror guards — files intentionally duplicated must stay byte-identical.

Some tools are both a blog-craft tool (canonical, tested here) AND shipped into a
materialized blog so a plain-python CI / operator can run them without the plugin:
  - compose.py            -> templates/hugo-hextra/scripts/           (every blog)
  - validate_educational  -> templates/hugo-hextra/scripts/           (every blog; the writing-standard checker imports it)
  - the papers validators -> templates/content-type-papers/shared/scripts/ (papers on)
  - scaffold-explainer.sh -> templates/content-type-explainers/shared/scripts/ (explainers on)
  - render-explainer.py   -> templates/content-type-explainers/shared/scripts/ (explainers on)
  - validate_glossary.py  -> templates/hugo-hextra/scripts/           (glossary gate)
  - glossary_scan.py      -> templates/hugo-hextra/scripts/           (imported by it)
  - validate_writing_standard.py -> templates/hugo-hextra/scripts/    (batch-gate, CI)
  - the writing standards (skills/apply-writing-standard/standards/*.md but
    README.md) -> templates/hugo-hextra/scripts/writing-standards/  (by glob,
    both ways, so a new standard needs no edit here)
Keep each pair in sync; edit the tools/ (or skills/) copy and re-mirror.

glossary_scan.py travels with validate_glossary.py because the validator imports
its marker + code-span helpers rather than re-deriving them. A blog's CI has no
plugin on sys.path, so the companion has to ship too.

ai-tells.md travels with validate_educational.py for the same reason: the lint
layer's word lists live in its fenced yaml block, and a materialized blog has
no skills/ tree — load_lint_data() falls back to the sibling scripts/ai-tells.md.
The writing standards travel with validate_writing_standard.py the same way:
standards_dirs() falls back to scripts/writing-standards/, and the checker
imports validate_educational's prose-line scanner, which ships beside it.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIRRORS = [
    ("tools/compose.py", "templates/hugo-hextra/scripts/compose.py"),
    ("tools/validate_educational.py", "templates/hugo-hextra/scripts/validate_educational.py"),
    ("tools/validate_mermaid.py", "templates/hugo-hextra/scripts/validate_mermaid.py"),
    ("tools/validate_mermaid_layout.mjs", "templates/hugo-hextra/scripts/validate_mermaid_layout.mjs"),
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
    ("tools/validate_writing_standard.py",
     "templates/hugo-hextra/scripts/validate_writing_standard.py"),
]

STANDARDS_SRC = "skills/apply-writing-standard/standards"
STANDARDS_DST = "templates/hugo-hextra/scripts/writing-standards"


def test_mirrors_identical():
    for a, b in MIRRORS:
        pa, pb = os.path.join(ROOT, a), os.path.join(ROOT, b)
        assert open(pa).read() == open(pb).read(), f"{a} and {b} diverged — re-mirror"


def _standard_files(rel):
    d = os.path.join(ROOT, rel)
    return sorted(f for f in os.listdir(d) if f.endswith(".md") and f != "README.md")


def test_writing_standards_mirrored_both_ways():
    """Every standard ships to a blog, and a blog ships no standard the plugin
    lacks — by glob, so a new standard needs no edit here (R2, R21)."""
    src, dst = _standard_files(STANDARDS_SRC), _standard_files(STANDARDS_DST)
    assert src, "no standards found"
    assert src == dst, f"standards differ: plugin {src} vs blog {dst} — re-mirror"
    for name in src:
        a = open(os.path.join(ROOT, STANDARDS_SRC, name), "rb").read()
        b = open(os.path.join(ROOT, STANDARDS_DST, name), "rb").read()
        assert a == b, f"{STANDARDS_SRC}/{name} and {STANDARDS_DST}/{name} diverged — re-mirror"


def test_materialized_checker_finds_its_standards_in_scripts(tmp_path):
    """A blog has no skills/ tree: the copied checker must load the copied
    standards from scripts/writing-standards/ (run from a tmp dir holding only
    scripts/)."""
    import shutil
    import subprocess
    import sys
    # The blog's whole scripts/ as the template ships it: the checker reuses
    # validate_educational's prose-line scanner, which ships there too.
    scripts = tmp_path / "blog" / "scripts"
    shutil.copytree(os.path.join(ROOT, "templates/hugo-hextra/scripts"), scripts)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}  # no plugin on the path
    page = tmp_path / "blog" / "page.md"
    page.write_text("Open the valve.\n\nDon't close it.\n")
    for name in _standard_files(STANDARDS_SRC):
        r = subprocess.run([sys.executable, str(scripts / "validate_writing_standard.py"),
                            "--default", name[:-3], str(page)],
                           capture_output=True, text=True, cwd=tmp_path, env=env)
        assert r.returncode in (0, 1), (name, r.stderr)
    r = subprocess.run([sys.executable, str(scripts / "validate_writing_standard.py"),
                        "--default", "ste", str(page)],
                       capture_output=True, text=True, cwd=tmp_path, env=env)
    assert r.returncode == 1 and "contractions" in r.stdout + r.stderr, r.stdout + r.stderr
