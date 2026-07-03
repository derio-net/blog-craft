"""P7 generalize — the papers-roadmap shortcode renders the roster from data.

papers-roadmap.html is already data-driven (reads site.Data.papers.entries and
derives live status from Site.Pages), so it ships verbatim in the papers
content-type. This proves a papers-enabled blog materializes it and renders
each roster entry with its derived status badge.
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


def test_papers_roadmap_ships_and_renders(tmp_path):
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, os.path.join(FIX, "answers-papers-v2.yaml"), blog],
                   check=True, capture_output=True, text=True)

    # The shortcode is materialized by the papers content-type.
    assert os.path.exists(os.path.join(blog, "layouts", "shortcodes", "papers-roadmap.html"))

    # Roster (content-owned data file) — one shippable, one deferred.
    data_dir = os.path.join(blog, "data")
    os.makedirs(data_dir, exist_ok=True)
    open(os.path.join(data_dir, "papers.yaml"), "w").write(
        "entries:\n"
        "  - number: 0\n    title: The Choice\n    layer: gpu\n    covers: inference\n"
        "  - number: 1\n    title: The Deferred One\n    layer: auth\n    covers: identity\n"
        "    deferred: true\n    deferred_reason: awaiting the auth layer\n")

    # A published paper page for entry 0 -> status derives to "published".
    pp = os.path.join(blog, "content", "docs", "papers", "00-choice")
    os.makedirs(pp)
    open(os.path.join(pp, "index.md"), "w").write(
        "---\ntitle: The Choice\nseries: [papers]\npaper_number: 0\nweight: 1\n"
        "draft: false\n---\nbody\n")

    # Roadmap page invoking the shortcode.
    rp = os.path.join(blog, "content", "docs", "papers", "99-roadmap")
    os.makedirs(rp)
    open(os.path.join(rp, "index.md"), "w").write(
        "---\ntitle: Roster\nseries: [papers]\npaper_number: 99\nweight: 100\n"
        "draft: false\n---\n{{< papers-roadmap >}}\n")

    r = subprocess.run(["hugo", "--buildDrafts"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

    html = _read_html(blog, os.path.join("papers", "99-roadmap"))
    assert "papers-roadmap" in html                        # roster container
    assert "The Choice" in html and "The Deferred One" in html
    assert "paper-status-published" in html                # entry 0 -> live page, not draft
    assert "paper-status-deferred" in html                 # entry 1 -> deferred
    assert "paper-card-deferred" in html and "awaiting the auth layer" in html
    assert 'class="layer-num">00<' in html                 # zero-padded number
