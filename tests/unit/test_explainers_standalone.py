"""Tests for standalone scaffold and render-explainer in standalone mode."""
import importlib
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCAFFOLD = os.path.join(ROOT, "tools", "scaffold-explainer.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

# ---- standalone scaffold ---------------------------------------------------


def test_scaffold_standalone_creates_md(tmp_path):
    r = subprocess.run(
        ["bash", SCAFFOLD, "--standalone", "--output", str(tmp_path),
         "--target", "/some/repo", "3", "clickhouse"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    mdf = tmp_path / "03-clickhouse.md"
    assert mdf.exists()
    content = mdf.read_text()
    assert "standalone: true" in content
    assert "target:" in content and "/some/repo" in content
    assert "post_number: 3" in content
    assert "## Overview" in content


def test_scaffold_standalone_refuses_duplicate(tmp_path):
    subprocess.run(
        ["bash", SCAFFOLD, "--standalone", "--output", str(tmp_path), "1", "x"],
        check=True, capture_output=True, text=True,
    )
    r = subprocess.run(
        ["bash", SCAFFOLD, "--standalone", "--output", str(tmp_path), "1", "x"],
        capture_output=True, text=True,
    )
    assert r.returncode != 0


# ---- render-explainer ------------------------------------------------------


def _scaffold_standalone(tmp_path, slug="test-post", content_extra=""):
    r = subprocess.run(
        ["bash", SCAFFOLD, "--standalone", "--output", str(tmp_path), "1", slug],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    mdf = tmp_path / f"01-{slug}.md"
    if content_extra:
        with open(mdf, "a") as f:
            f.write(content_extra)
    return mdf


def test_render_produces_html(tmp_path):
    mdf = _scaffold_standalone(tmp_path)
    out = tmp_path / "out.html"
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_explainer.py"),
         str(mdf), "-o", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    html = out.read_text()
    assert "<!DOCTYPE html>" in html
    assert "Explainer" in html  # default title prefix
    assert "mermaid.min.js" in html  # mermaid JS always in the template


def test_render_respects_style_flag(tmp_path):
    mdf = _scaffold_standalone(tmp_path)
    out = tmp_path / "dark.html"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_explainer.py"),
         str(mdf), "--style", "dark", "-o", str(out)],
        check=True, capture_output=True, text=True,
    )
    html = out.read_text()
    assert "#0d1117" in html  # dark background


def test_render_with_custom_css(tmp_path):
    mdf = _scaffold_standalone(tmp_path)
    css = tmp_path / "custom.css"
    css.write_text("body{background:hotpink}")
    out = tmp_path / "custom.html"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_explainer.py"),
         str(mdf), "--style", str(css), "-o", str(out)],
        check=True, capture_output=True, text=True,
    )
    html = out.read_text()
    assert "hotpink" in html


def test_render_frontmatter_style_override(tmp_path):
    """standalone_style in frontmatter is used when no --style is given."""
    mdf = _scaffold_standalone(tmp_path)
    content = mdf.read_text()
    content = content.replace("archetype:", "standalone_style: dark\narchetype:")
    mdf.write_text(content)
    out = tmp_path / "fm.html"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_explainer.py"),
         str(mdf), "-o", str(out)],
        check=True, capture_output=True, text=True,
    )
    html = out.read_text()
    assert "#0d1117" in html  # dark theme from frontmatter


def test_render_includes_mermaid_js(tmp_path):
    """HTML includes a mermaid.js CDN script when the markdown has a mermaid block."""
    mdf = _scaffold_standalone(tmp_path, content_extra="\n```mermaid\ngraph TD; A-->B;\n```\n")
    out = tmp_path / "mermaid.html"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_explainer.py"),
         str(mdf), "-o", str(out)],
        check=True, capture_output=True, text=True,
    )
    html = out.read_text()
    assert "mermaid.min.js" in html


def test_render_explicit_style_wins_over_frontmatter(tmp_path):
    """Explicit --style overrides standalone_style in frontmatter."""
    mdf = _scaffold_standalone(tmp_path)
    content = mdf.read_text()
    content = content.replace("archetype:", "standalone_style: dark\narchetype:")
    mdf.write_text(content)
    out = tmp_path / "explicit.html"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_explainer.py"),
         str(mdf), "--style", "light", "-o", str(out)],
        check=True, capture_output=True, text=True,
    )
    html = out.read_text()
    assert "#fff" in html  # light theme, not dark (#0d1117)


def test_render_fallback_html_directly(tmp_path):
    """The fallback HTML function produces valid output."""
    from render_explainer import _fallback_html
    html = _fallback_html("<p>oh no</p>", "light")
    assert "oh no" in html
    assert "<!DOCTYPE html>" in html
