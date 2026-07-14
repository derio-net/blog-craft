#!/usr/bin/env python3
"""Render an explainer markdown file to a standalone, self-contained HTML page.

Usage:
    python render_explainer.py <input.md> [--style light|dark|minimal|<css-path>]

Wraps the explainer content in a styled HTML page with inline CSS.
Mermaid diagrams render client-side via embedded mermaid.js.
"""
from __future__ import annotations

import argparse
import re
import sys

_THEMES: dict[str, str] = {}

_THEMES["light"] = """
:root{--bg:#fff;--text:#1a1a2e;--muted:#6b7280;--border:#e5e7eb;--code-bg:#f3f4f6;--accent:#2563eb;--heading:#111827;--blockquote-bg:#f9fafb;--blockquote-border:#d1d5db}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:16px;line-height:1.7;-webkit-font-smoothing:antialiased}
body{font-family:Georgia,Palatino,"Palatino Linotype","Book Antiqua",serif;color:var(--text);background:var(--bg);padding:2rem 1rem}
.explainer{max-width:740px;margin:0 auto}
header{margin-bottom:2.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border)}
h1{font-size:2rem;font-weight:700;color:var(--heading);line-height:1.3;margin-bottom:.5rem}
.meta{font-size:.875rem;color:var(--muted);display:flex;gap:1rem;flex-wrap:wrap}
.meta span{display:inline-block}
.tldr{background:var(--blockquote-bg);border-left:3px solid var(--accent);padding:.75rem 1rem;margin-top:1rem;border-radius:0 6px 6px 0;font-size:.9375rem;color:var(--text)}
.content h2{font-size:1.5rem;font-weight:600;color:var(--heading);margin:2rem 0 .75rem;padding-bottom:.375rem;border-bottom:1px solid var(--border)}
.content h3{font-size:1.25rem;font-weight:600;color:var(--heading);margin:1.5rem 0 .5rem}
.content p{margin-bottom:1rem}
.content ul,.content ol{margin-bottom:1rem;padding-left:1.5rem}
.content li{margin-bottom:.25rem}
.content a{color:var(--accent);text-decoration:none}
.content a:hover{text-decoration:underline}
.content blockquote{background:var(--blockquote-bg);border-left:4px solid var(--blockquote-border);margin:1rem 0;padding:.5rem 1rem;color:var(--muted);border-radius:0 6px 6px 0}
.content code{font-family:"SF Mono","Fira Code","Fira Mono","Roboto Mono",monospace;font-size:.875em;background:var(--code-bg);padding:.125rem .375rem;border-radius:4px}
.content pre{background:var(--code-bg);padding:1rem;border-radius:8px;overflow-x:auto;margin-bottom:1rem;font-size:.875rem;line-height:1.5}
.content pre code{padding:0;background:transparent}
.content img{max-width:100%;height:auto;border-radius:8px;margin:1rem 0}
.content table{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9375rem}
.content th,.content td{padding:.5rem .75rem;border:1px solid var(--border);text-align:left}
.content th{background:var(--code-bg);font-weight:600}
.content hr{margin:2rem 0;border:none;border-top:1px solid var(--border)}
.content .mermaid{text-align:center;margin:1.5rem 0}
""".strip()

_THEMES["dark"] = """
:root{--bg:#0d1117;--text:#c9d1d9;--muted:#8b949e;--border:#30363d;--code-bg:#161b22;--accent:#58a6ff;--heading:#f0f6fc;--blockquote-bg:#161b22;--blockquote-border:#30363d}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:16px;line-height:1.7;-webkit-font-smoothing:antialiased}
body{font-family:Georgia,Palatino,"Palatino Linotype","Book Antiqua",serif;color:var(--text);background:var(--bg);padding:2rem 1rem}
.explainer{max-width:740px;margin:0 auto}
header{margin-bottom:2.5rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border)}
h1{font-size:2rem;font-weight:700;color:var(--heading);line-height:1.3;margin-bottom:.5rem}
.meta{font-size:.875rem;color:var(--muted);display:flex;gap:1rem;flex-wrap:wrap}
.meta span{display:inline-block}
.tldr{background:var(--blockquote-bg);border-left:3px solid var(--accent);padding:.75rem 1rem;margin-top:1rem;border-radius:0 6px 6px 0;font-size:.9375rem;color:var(--text)}
.content h2{font-size:1.5rem;font-weight:600;color:var(--heading);margin:2rem 0 .75rem;padding-bottom:.375rem;border-bottom:1px solid var(--border)}
.content h3{font-size:1.25rem;font-weight:600;color:var(--heading);margin:1.5rem 0 .5rem}
.content p{margin-bottom:1rem}
.content ul,.content ol{margin-bottom:1rem;padding-left:1.5rem}
.content li{margin-bottom:.25rem}
.content a{color:var(--accent);text-decoration:none}
.content a:hover{text-decoration:underline}
.content blockquote{background:var(--blockquote-bg);border-left:4px solid var(--blockquote-border);margin:1rem 0;padding:.5rem 1rem;color:var(--muted);border-radius:0 6px 6px 0}
.content code{font-family:"SF Mono","Fira Code","Fira Mono","Roboto Mono",monospace;font-size:.875em;background:var(--code-bg);padding:.125rem .375rem;border-radius:4px}
.content pre{background:var(--code-bg);padding:1rem;border-radius:8px;overflow-x:auto;margin-bottom:1rem;font-size:.875rem;line-height:1.5}
.content pre code{padding:0;background:transparent}
.content img{max-width:100%;height:auto;border-radius:8px;margin:1rem 0}
.content table{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9375rem}
.content th,.content td{padding:.5rem .75rem;border:1px solid var(--border);text-align:left}
.content th{background:var(--code-bg);font-weight:600}
.content hr{margin:2rem 0;border:none;border-top:1px solid var(--border)}
.content .mermaid{text-align:center;margin:1.5rem 0}
""".strip()

_THEMES["minimal"] = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:16px;line-height:1.6}
body{font-family:system-ui,-apple-system,sans-serif;color:#222;background:#fff;padding:1.5rem}
.explainer{max-width:720px;margin:0 auto}
header{margin-bottom:2rem}
h1{font-size:1.75rem;font-weight:600;margin-bottom:.375rem}
.meta{font-size:.8125rem;color:#666;display:flex;gap:.75rem;flex-wrap:wrap}
.tldr{background:#f5f5f5;padding:.5rem .75rem;margin-top:.75rem;border-radius:4px;font-size:.875rem}
.content h2{font-size:1.375rem;font-weight:600;margin:1.5rem 0 .5rem}
.content h3{font-size:1.125rem;font-weight:600;margin:1.25rem 0 .375rem}
.content p{margin-bottom:.75rem}
.content ul,.content ol{margin-bottom:.75rem;padding-left:1.25rem}
.content li{margin-bottom:.1875rem}
.content a{color:#1a0dab;text-decoration:underline}
.content blockquote{border-left:3px solid #ccc;margin:.75rem 0;padding:.375rem .75rem;color:#555}
.content code{font-family:monospace;font-size:.875em;background:#f0f0f0;padding:.125rem .3125rem;border-radius:3px}
.content pre{background:#f5f5f5;padding:.75rem;border-radius:4px;overflow-x:auto;margin-bottom:.75rem;font-size:.8125rem}
.content pre code{padding:0;background:transparent}
.content img{max-width:100%;height:auto;margin:.75rem 0}
.content table{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.875rem}
.content th,.content td{padding:.375rem .625rem;border:1px solid #ddd;text-align:left}
.content th{background:#f5f5f5;font-weight:600}
.content hr{margin:1.5rem 0;border:none;border-top:1px solid #ddd}
.content .mermaid{text-align:center;margin:1rem 0}
""".strip()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_markdown)."""
    import yaml
    if not text.startswith("---"):
        return {}, text
    rest = text.split("\n", 1)[1]
    m = re.search(r"^---\s*$", rest, re.MULTILINE)
    if m is None:
        return {}, text
    fm = yaml.safe_load(rest[: m.start()]) or {}
    body = rest[m.end():].lstrip("\n")
    return fm, body


def resolve_style(style_arg: str = "light") -> str:
    """Return the CSS string for the given style name or custom CSS file path."""
    if style_arg in _THEMES:
        return _THEMES[style_arg]
    # Treat as a CSS file path
    try:
        with open(style_arg) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Style '{style_arg}' not found — falling back to 'light'", file=sys.stderr)
        return _THEMES["light"]


def render(
    md_text: str,
    style: str = "light",
    strict: bool = False,
    style_explicit: bool = False,
) -> str:
    """Convert explainer markdown to a standalone HTML page.

    Args:
        md_text: Full markdown text (may include YAML frontmatter).
        style: Theme name or path to custom CSS file.
        strict: If True, raise ImportError when markdown library is missing.
        style_explicit: If True, CLI `--style` was explicitly given and
            frontmatter `standalone_style` must NOT override it.

    Returns:
        Complete self-contained HTML string.
    """
    try:
        import markdown as _md
    except ImportError:
        if strict:
            raise
        return _fallback_html(
            "<p>render-explainer.py requires the 'markdown' Python library. "
            "Install it with: <code>pip install markdown</code></p>",
            style,
        )

    fm, body = parse_frontmatter(md_text)

    if not style_explicit:
        style = fm.get("standalone_style", style)

    css = resolve_style(style)
    title = fm.get("title", "Explainer")
    archetype = fm.get("archetype", "")
    date = fm.get("date", "")
    tldr = fm.get("tldr", "")

    html_body = _md.markdown(
        body,
        extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
    )

    html_body = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        lambda m: '<pre class="mermaid">' + m.group(1).strip() + '</pre>',
        html_body,
        flags=re.DOTALL,
    )

    return _wrap(title, html_body, css, archetype, date, tldr)


def _wrap(
    title: str,
    html_body: str,
    css: str,
    archetype: str = "",
    date: str = "",
    tldr: str = "",
) -> str:
    tldr_html = f"<div class=\"tldr\">{tldr}</div>" if tldr else ""
    archetype_tag = f"<span class=\"archetype\">{archetype}</span>" if archetype else ""
    date_tag = f"<span class=\"date\">{date}</span>" if date else ""
    meta_parts = " ".join(p for p in (archetype_tag, date_tag) if p)
    meta = f"<p class=\"meta\">{meta_parts}</p>" if meta_parts else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)} — Explainer</title>
<style>
{css}
</style>
</head>
<body>
<article class="explainer">
<header>
<h1>{_e(title)}</h1>
{meta}
{tldr_html}
</header>
<div class="content">
{html_body}
</div>
</article>
<script>
(function(){{var e=document.querySelectorAll(".mermaid");if(e.length>0){{var s=document.createElement("script");s.src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";s.onload=function(){{mermaid.initialize({{startOnLoad:true}})}};document.head.appendChild(s)}}}})()
</script>
</body>
</html>"""


def _e(s: str) -> str:
    """HTML-escape a string."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _fallback_html(msg: str, style: str) -> str:
    css = resolve_style(style)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Explainer</title>
<style>
{css}
</style>
</head>
<body>
<article class="explainer">
<div class="content">
{msg}
</div>
</article>
</body>
</html>"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Render an explainer markdown file to standalone HTML")
    ap.add_argument("input", help="Path to the explainer markdown file")
    ap.add_argument("--style", default="light",
                    help="Theme: light, dark, minimal, or path to a custom CSS file")
    ap.add_argument("-o", "--output", default=None,
                    help="Output HTML path (default: <input>.html)")
    a = ap.parse_args(argv)

    with open(a.input) as f:
        md_text = f.read()

    style_explicit = any(p.startswith("--style") for p in argv)
    html = render(md_text, style=a.style, strict=False, style_explicit=style_explicit)

    if "render-explainer.py requires the 'markdown' Python library" in html:
        print("ERROR: 'markdown' Python library is not installed.", file=sys.stderr)
        print("  Install: pip install markdown", file=sys.stderr)
        return 1

    out = a.output or (a.input.rsplit(".", 1)[0] + ".html")
    with open(out, "w") as f:
        f.write(html)
    print(f"Rendered: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
