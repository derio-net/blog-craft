"""Mirror guards — files intentionally duplicated must stay byte-identical.

compose.py is both a blog-craft tool (tested here) and shipped alongside the
generator (templates/hugo-hextra/scripts/compose.py). Same pattern as the
repo's media-fill.py mirror; keep them in sync.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_compose_mirror_identical():
    a = os.path.join(ROOT, "tools", "compose.py")
    b = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "compose.py")
    assert open(a).read() == open(b).read(), "tools/compose.py and shipped scripts/compose.py diverged"
