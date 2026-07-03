"""Mirror guards — files intentionally duplicated must stay byte-identical.

Some tools are both a blog-craft tool (canonical, tested here) AND shipped into a
materialized blog so a plain-python CI / operator can run them without the plugin:
  - compose.py            -> templates/hugo-hextra/scripts/           (every blog)
  - the papers validators -> templates/content-type-papers/shared/scripts/ (papers on)
Keep each pair in sync; edit the tools/ copy and re-mirror.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIRRORS = [
    ("tools/compose.py", "templates/hugo-hextra/scripts/compose.py"),
    ("tools/validate_papers.py", "templates/content-type-papers/shared/scripts/validate_papers.py"),
    ("tools/validate_dossier.py", "templates/content-type-papers/shared/scripts/validate_dossier.py"),
    ("tools/sync_dossier_to_data.py", "templates/content-type-papers/shared/scripts/sync_dossier_to_data.py"),
    ("tools/scaffold-paper.sh", "templates/content-type-papers/shared/scripts/scaffold-paper.sh"),
]


def test_mirrors_identical():
    for a, b in MIRRORS:
        pa, pb = os.path.join(ROOT, a), os.path.join(ROOT, b)
        assert open(pa).read() == open(pb).read(), f"{a} and {b} diverged — re-mirror"
