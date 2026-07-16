#!/usr/bin/env python3
"""Render an explainer markdown file to a standalone, self-contained HTML page.

Usage:
    python render_explainer.py <input.md> \
        [--style light|dark|minimal|broadsheet|<css-path>] [--embed-fonts]

Wraps the explainer content in a styled HTML page with inline CSS.
Mermaid diagrams render client-side via embedded mermaid.js, themed per --style.
`--embed-fonts` inlines the broadsheet web fonts (Fraunces + Newsreader) as
base64 @font-face data URIs for a truly self-contained page.
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

# A bespoke editorial theme — warm dark, display+body serif, a disciplined
# two-accent system (brass = human/attention, teal = automated/verified). Its
# distinctive type needs web fonts; pair with `--embed-fonts` for a truly
# self-contained page (else it falls back to system serifs). Component classes
# (.eyebrow/.pull/.ledger/.rv) are available for custom-HTML explainers.
_THEMES["broadsheet"] = """
:root{
--ink:#0b0c10;--ink-2:#101218;--panel:#13151d;
--paper:#e7e1d3;--paper-dim:#c3bda7;--muted:#8f897a;--faint:#5d5a51;
--line:#23262f;--line-2:#2d313c;
--brass:#e0a24e;--teal:#5fb9b0;--rust:#cf6d47;
--display:"Fraunces","Hoefler Text",Georgia,serif;
--serif:"Newsreader",Palatino,Georgia,serif;
--mono:ui-monospace,"SF Mono","Cascadia Code",monospace}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:17px;line-height:1.75;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
body{font-family:var(--serif);color:var(--paper);background:var(--ink);padding:3rem 1.25rem}
.explainer{max-width:720px;margin:0 auto}
header{margin-bottom:3rem;padding-bottom:1.75rem;border-bottom:1px solid var(--line-2)}
h1{font-family:var(--display);font-optical-sizing:auto;font-weight:600;font-size:2.75rem;line-height:1.1;letter-spacing:-.01em;color:var(--paper);margin-bottom:.75rem}
.meta{font-family:var(--mono);font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:flex;gap:1.25rem;flex-wrap:wrap}
.tldr{font-family:var(--display);font-size:1.15rem;font-style:italic;color:var(--paper-dim);border-left:2px solid var(--brass);padding:.5rem 0 .5rem 1.25rem;margin-top:1.5rem}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--teal);display:block;margin-bottom:.35rem}
.content h2,.sec-head{font-family:var(--display);font-weight:600;font-size:1.9rem;line-height:1.15;color:var(--paper);margin:3rem 0 1rem;padding-top:1.25rem;border-top:1px solid var(--line)}
.content h3{font-family:var(--display);font-weight:600;font-size:1.35rem;color:var(--paper);margin:2rem 0 .6rem}
.content p{margin-bottom:1.15rem}
.content ul,.content ol{margin:0 0 1.15rem;padding-left:1.4rem}
.content li{margin-bottom:.4rem}
.content a{color:var(--brass);text-decoration:none;border-bottom:1px solid rgba(224,162,78,.35)}
.content a:hover{border-bottom-color:var(--brass)}
.content blockquote{font-family:var(--display);font-style:italic;color:var(--paper-dim);border-left:2px solid var(--teal);margin:1.5rem 0;padding:.25rem 0 .25rem 1.25rem}
.pull{font-family:var(--display);font-weight:500;font-size:1.6rem;line-height:1.25;color:var(--paper);border-top:1px solid var(--line-2);border-bottom:1px solid var(--line-2);padding:1.25rem 0;margin:2rem 0}
.content code{font-family:var(--mono);font-size:.82em;background:var(--ink-2);color:var(--paper-dim);padding:.1rem .35rem;border-radius:3px}
.content pre{background:var(--ink-2);border:1px solid var(--line);padding:1.1rem 1.25rem;border-radius:6px;overflow-x:auto;margin-bottom:1.25rem;font-size:.82rem;line-height:1.6}
.content pre code{padding:0;background:transparent;color:var(--paper)}
.content img{max-width:100%;height:auto;border-radius:6px;margin:1.25rem 0}
.content table{width:100%;border-collapse:collapse;margin:1.25rem 0;font-size:.9rem}
.content th,.content td{padding:.55rem .8rem;border-bottom:1px solid var(--line);text-align:left}
.content th{font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--teal);font-weight:500}
.ledger{list-style:none;counter-reset:l;padding:0}
.ledger>li{counter-increment:l;position:relative;padding-left:2.5rem;margin-bottom:1rem}
.ledger>li::before{content:counter(l,decimal-leading-zero);position:absolute;left:0;top:.1rem;font-family:var(--mono);font-size:.8rem;color:var(--brass)}
.content hr{margin:2.5rem 0;border:none;border-top:1px solid var(--line)}
.content .mermaid{text-align:center;margin:2rem 0}
.rv{opacity:0;transform:translateY(12px);transition:opacity .6s ease,transform .6s ease}
.rv.in{opacity:1;transform:none}
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
    embed_fonts: bool = False,
    fonts_dir: str | None = None,
) -> str:
    """Convert explainer markdown to a standalone HTML page.

    Args:
        md_text: Full markdown text (may include YAML frontmatter).
        style: Theme name or path to custom CSS file.
        strict: If True, raise ImportError when markdown library is missing.
        style_explicit: If True, CLI `--style` was explicitly given and
            frontmatter `standalone_style` must NOT override it.
        embed_fonts: If True, inline the bundled broadsheet web fonts as base64
            @font-face data URIs so the page is truly self-contained.
        fonts_dir: Override the bundled fonts directory (default: auto-located).

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

    # Extract mermaid fences BEFORE markdown runs: the codehilite extension wraps
    # fenced code in highlight <span>s, so a post-hoc regex never matches and the
    # diagram would render as a code block. Stash → render → re-insert as
    # <pre class="mermaid"> (what mermaid.js looks for).
    mermaid_blocks: list[str] = []

    def _stash(m):
        mermaid_blocks.append(m.group(1).strip())
        return f"\n\nMERMAIDBLOCK{len(mermaid_blocks) - 1}ENDMERMAID\n\n"

    body = re.sub(r'```mermaid\s*\n(.*?)```', _stash, body, flags=re.DOTALL)

    html_body = _md.markdown(
        body,
        extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
    )

    for i, blk in enumerate(mermaid_blocks):
        html_body = html_body.replace(
            f"<p>MERMAIDBLOCK{i}ENDMERMAID</p>",
            f'<pre class="mermaid">{blk}</pre>',
        )

    font_css = ""
    if embed_fonts:
        resolved = _resolve_fonts_dir(fonts_dir)
        if resolved is None:
            print("--embed-fonts: no bundled fonts found — run "
                  "tools/fetch_broadsheet_fonts.py or pass --fonts-dir. "
                  "Falling back to system fonts.", file=sys.stderr)
        else:
            font_css = _embed_fonts_css(resolved)

    return _wrap(title, html_body, css, archetype, date, tldr, style, font_css)


# Mermaid theme variables per --style, so standalone diagrams look *designed*
# rather than default. Each style themes its own diagrams; unknown styles fall
# back to `light`. (Previously keyed on an is_dark boolean, which gave a warm
# theme like `broadsheet` the wrong palette — #22.)
_MERMAID_LIGHT = {
    "primaryColor": "#dde9ff", "primaryBorderColor": "#1f6feb",
    "primaryTextColor": "#0d1b2a", "lineColor": "#198754",
    "textColor": "#1a1a2e", "clusterBkg": "#eef2f6",
    "clusterBorder": "#1f6feb", "edgeLabelBackground": "#f8f9fa",
}
_MERMAID_VARS = {
    "light": _MERMAID_LIGHT,
    "minimal": _MERMAID_LIGHT,
    "dark": {
        "primaryColor": "#1f3a5f", "primaryBorderColor": "#4dabf7",
        "primaryTextColor": "#eaf2ff", "lineColor": "#51cf66",
        "textColor": "#c9d1d9", "clusterBkg": "#161b22",
        "clusterBorder": "#4dabf7", "edgeLabelBackground": "#0d1117",
    },
    "broadsheet": {  # warm dark — brass nodes, teal edges
        "primaryColor": "#13151d", "primaryBorderColor": "#e0a24e",
        "primaryTextColor": "#e7e1d3", "lineColor": "#5fb9b0",
        "textColor": "#e7e1d3", "clusterBkg": "#101218",
        "clusterBorder": "#5fb9b0", "edgeLabelBackground": "#0b0c10",
    },
}


def _mermaid_init(style: str) -> str:
    import json
    vars_ = _MERMAID_VARS.get(style, _MERMAID_LIGHT)
    cfg = {"startOnLoad": True, "theme": "base", "themeVariables": vars_}
    return "mermaid.initialize(" + json.dumps(cfg) + ")"


# ------------------------------------------------------------- font embedding

def _resolve_fonts_dir(explicit: str | None) -> str | None:
    """Locate the bundled broadsheet fonts dir (or the explicit one)."""
    import os
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (
        os.path.join(here, "..", "fonts", "broadsheet"),                 # materialized blog layout
        os.path.join(here, "..", "content-type-explainers", "shared", "fonts", "broadsheet"),
        os.path.join(here, "..", "templates", "content-type-explainers", "shared", "fonts", "broadsheet"),  # plugin tools/ layout
    ):
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return None


def _embed_fonts_css(fonts_dir: str) -> str:
    """Read <fonts_dir>/broadsheet-fonts.css and inline each woff2 as a base64
    data URI, so the page carries its fonts with no external requests."""
    import base64
    import os
    css_path = os.path.join(fonts_dir, "broadsheet-fonts.css")
    with open(css_path) as f:
        css = f.read()

    def _inline(m):
        fname = m.group(1)
        with open(os.path.join(fonts_dir, fname), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        return f"url(data:font/woff2;base64,{b64}) format('woff2')"

    return re.sub(r"url\(([^)]+\.woff2)\)\s*format\('woff2'\)", _inline, css)


def _wrap(
    title: str,
    html_body: str,
    css: str,
    archetype: str = "",
    date: str = "",
    tldr: str = "",
    style: str = "light",
    font_css: str = "",
) -> str:
    tldr_html = f"<div class=\"tldr\">{tldr}</div>" if tldr else ""
    mermaid_init = _mermaid_init(style)
    archetype_tag = f"<span class=\"archetype\">{archetype}</span>" if archetype else ""
    date_tag = f"<span class=\"date\">{date}</span>" if date else ""
    meta_parts = " ".join(p for p in (archetype_tag, date_tag) if p)
    meta = f"<p class=\"meta\">{meta_parts}</p>" if meta_parts else ""
    font_style = f"<style>\n{font_css}\n</style>\n" if font_css else ""
    # Scroll-reveal for .rv elements (broadsheet's editorial motion). Harmless
    # no-op when no .rv nodes exist.
    reveal_js = (
        "(function(){var o=new IntersectionObserver(function(es){es.forEach("
        "function(e){if(e.isIntersecting)e.target.classList.add('in')})},"
        "{threshold:.12});document.querySelectorAll('.rv').forEach("
        "function(n){o.observe(n)})})();"
        if style == "broadsheet" else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)} — Explainer</title>
{font_style}<style>
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
(function(){{var e=document.querySelectorAll(".mermaid");if(e.length>0){{var s=document.createElement("script");s.src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";s.onload=function(){{{mermaid_init}}};document.head.appendChild(s)}}}})()
{reveal_js}
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
                    help="Theme: light, dark, minimal, broadsheet, or a custom CSS file path")
    ap.add_argument("--embed-fonts", action="store_true",
                    help="Inline the broadsheet web fonts as base64 @font-face (self-contained)")
    ap.add_argument("--fonts-dir", default=None,
                    help="Override the bundled broadsheet fonts directory")
    ap.add_argument("-o", "--output", default=None,
                    help="Output HTML path (default: <input>.html)")
    a = ap.parse_args(argv)

    with open(a.input) as f:
        md_text = f.read()

    style_explicit = any(p.startswith("--style") for p in argv)
    html = render(md_text, style=a.style, strict=False, style_explicit=style_explicit,
                  embed_fonts=a.embed_fonts, fonts_dir=a.fonts_dir)

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
