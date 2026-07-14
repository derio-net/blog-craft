"""P1.T4 -- Hugo smoke: explainers content-type builds cleanly with Mermaid."""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
SCAFFOLD = os.path.join(ROOT, "tools", "scaffold-explainer.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
ENV = dict(os.environ, PYTHON=sys.executable)


def test_explainers_hugo_build(tmp_path):
    blog = str(tmp_path / "blog")
    subprocess.run(
        ["bash", RENDER, os.path.join(FIX, "answers-explainers-v2.yaml"), blog],
        check=True, capture_output=True, text=True,
    )

    # Scaffold post 1 / smoke-test
    cfg = os.path.join(blog, ".blog-craft.yaml")
    r = subprocess.run(
        ["bash", SCAFFOLD, "--config", cfg, "1", "smoke-test"],
        capture_output=True, text=True, env=ENV,
    )
    assert r.returncode == 0, r.stderr

    # Append mermaid block under ## How it works
    idx = os.path.join(blog, "content", "docs", "explainers", "01-smoke-test", "index.md")
    content = open(idx).read()
    content = content.replace(
        "## How it works",
        "## How it works\n\n```mermaid\ngraph TD; A-->B;\n```",
    )
    # Set draft: false so Hugo includes it
    content = content.replace("draft: true", "draft: false")
    open(idx, "w").write(content)

    # Hugo build
    r = subprocess.run(["hugo", "--buildDrafts"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

    # Check rendered page exists — content lives under content/docs/explainers/
    hits = glob.glob(
        os.path.join(blog, "public", "docs", "explainers", "01-smoke-test", "index.html"),
    )
    assert hits, f"no rendered HTML under {blog}/public/docs/explainers/01-smoke-test/"

    html = open(hits[0]).read()
    assert "mermaid" in html.lower(), "mermaid block not rendered in output HTML"
