"""broadsheet --style, per-style Mermaid, and --embed-fonts (#22)."""
import os
import re

from render_explainer import (
    _THEMES,
    _embed_fonts_css,
    _mermaid_init,
    _resolve_fonts_dir,
    render,
    resolve_style,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUNDLED = os.path.join(ROOT, "templates", "content-type-explainers", "shared",
                       "fonts", "broadsheet")

MD = "---\ntitle: T\n---\n\n## How it works\n\n```mermaid\nflowchart TD; A-->B\n```\n\ntext\n"


# --- broadsheet style ------------------------------------------------------

def test_broadsheet_registered():
    assert "broadsheet" in _THEMES


def test_broadsheet_css_uses_display_serif_and_accents():
    css = resolve_style("broadsheet")
    assert "Fraunces" in css and "Newsreader" in css
    assert "--brass:#e0a24e" in css and "--teal:#5fb9b0" in css


def test_render_broadsheet_applies_theme_and_reveal():
    html = render(MD, style="broadsheet", strict=True)
    assert "Fraunces" in html
    assert "IntersectionObserver" in html  # reveal observer for broadsheet only
    assert '<pre class="mermaid">' in html  # fence still converts


def test_reveal_observer_absent_for_other_styles():
    assert "IntersectionObserver" not in render(MD, style="dark", strict=True)


# --- per-style Mermaid palette --------------------------------------------

def test_mermaid_palette_is_per_style():
    light = _mermaid_init("light")
    broad = _mermaid_init("broadsheet")
    assert light != broad
    assert "#e0a24e" in broad  # brass border, broadsheet-specific
    assert "#e0a24e" not in light


def test_mermaid_unknown_style_falls_back_to_light():
    assert _mermaid_init("no-such-style") == _mermaid_init("light")


# --- font embedding --------------------------------------------------------

def _fixture_fonts(tmp_path):
    d = tmp_path / "fonts"
    d.mkdir()
    (d / "x-latin-roman-abc.woff2").write_bytes(b"wOF2\x00fake-font-bytes")
    (d / "broadsheet-fonts.css").write_text(
        "@font-face{font-family:'Fraunces';"
        "src:url(x-latin-roman-abc.woff2) format('woff2');}\n"
    )
    return str(d)


def test_embed_inlines_base64_and_drops_local_url(tmp_path):
    out = _embed_fonts_css(_fixture_fonts(tmp_path))
    assert "url(data:font/woff2;base64," in out
    assert "x-latin-roman-abc.woff2" not in out  # local ref replaced
    assert not re.search(r"url\([^)]*\.woff2\)\s*format", out)


def test_render_embed_fonts_flag(tmp_path):
    html = render(MD, style="broadsheet", strict=True,
                  embed_fonts=True, fonts_dir=_fixture_fonts(tmp_path))
    assert "data:font/woff2;base64," in html


def test_embed_fonts_missing_dir_falls_back(tmp_path):
    # Non-existent fonts dir → no crash, no data URI, page still renders.
    html = render(MD, style="broadsheet", strict=True,
                  embed_fonts=True, fonts_dir=str(tmp_path / "nope"))
    assert "data:font/woff2;base64," not in html
    assert "Fraunces" in html  # theme still applied


def test_resolve_fonts_dir_prefers_explicit(tmp_path):
    d = _fixture_fonts(tmp_path)
    assert _resolve_fonts_dir(d) == d
    assert _resolve_fonts_dir(str(tmp_path / "missing")) is None


# --- bundled fonts sanity (guards the committed fetch output) --------------

def test_bundled_fonts_present_and_referenced():
    css_path = os.path.join(BUNDLED, "broadsheet-fonts.css")
    assert os.path.isfile(css_path), "run tools/fetch_broadsheet_fonts.py"
    css = open(css_path).read()
    refs = re.findall(r"url\(([^)]+\.woff2)\)", css)
    assert refs, "no woff2 referenced in broadsheet-fonts.css"
    for f in refs:
        assert os.path.isfile(os.path.join(BUNDLED, f)), f"missing bundled font {f}"
    assert os.path.isfile(os.path.join(BUNDLED, "OFL.txt")), "OFL license required"


def test_bundled_fonts_embed_end_to_end():
    # The real bundled fonts inline without error.
    out = _embed_fonts_css(BUNDLED)
    assert out.count("data:font/woff2;base64,") >= 4
