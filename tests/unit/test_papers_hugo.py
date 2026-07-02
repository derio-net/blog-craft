"""P3.T3.S2 — the papers cross-link partials render at Hugo build.

A paper with related_building renders a forward chip on the paper page and a
backlink chip on the referenced building page.
"""
import glob
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _read_html(blog, needle):
    hits = glob.glob(os.path.join(blog, "public", "**", needle, "index.html"), recursive=True)
    assert hits, f"no rendered HTML for {needle} under {blog}/public"
    return open(hits[0]).read()


def test_papers_crosslinks_render(tmp_path):
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, os.path.join(FIX, "answers-papers-v2.yaml"), blog],
                   check=True, capture_output=True, text=True)

    bp = os.path.join(blog, "content", "docs", "building", "01-hello")
    os.makedirs(bp)
    open(os.path.join(bp, "index.md"), "w").write(
        "---\ntitle: Hello\nseries: [building]\nweight: 2\ndraft: false\n---\nbody\n")

    pp = os.path.join(blog, "content", "docs", "papers", "01-choice")
    os.makedirs(pp)
    open(os.path.join(pp, "index.md"), "w").write(
        "---\ntitle: The Choice\nseries: [papers]\npaper_number: 0\nweight: 1\n"
        "draft: false\nrelated_building: docs/building/01-hello\n---\nbody\n")

    r = subprocess.run(["hugo", "--buildDrafts"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

    building_html = _read_html(blog, os.path.join("building", "01-hello"))
    assert "paper-cross-links" in building_html and "Decision-level view" in building_html

    paper_html = _read_html(blog, os.path.join("papers", "01-choice"))
    assert "paper-cross-links" in paper_html and "Hands-on" in paper_html
