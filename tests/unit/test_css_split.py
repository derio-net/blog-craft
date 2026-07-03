"""P4.T1 / P7 — custom.css: structural base always present; the read-marker and
the FULL papers surface are gated; an optional mermaid-palette override appends.

P7 replaces the old minified papers subset with frank's full .paper-post surface,
shipped verbatim and gated on content_types.papers.enabled (a non-papers blog
carries none of it). The palette is baked from frank; the config knob only adds
an override block for rebrands.
"""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDERER = os.path.join(ROOT, "tools", "render-template")
TMPL = os.path.join(ROOT, "templates", "hugo-hextra", "assets", "css", "custom.css.tmpl")

STRUCTURAL = [".post-cover", ".screenshot", ".asciinema-container",
              ".site-track-banner", ".blog-series-cards"]


def _render(cfg, tmp_path):
    src = tmp_path / "src"; src.mkdir(exist_ok=True)
    dst = tmp_path / "dst"; dst.mkdir(exist_ok=True)
    (src / "custom.css.tmpl").write_text(open(TMPL).read())
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(src), "--dst", str(dst), "--answers", str(ans)],
                   cwd=RENDERER, check=True, capture_output=True, text=True)
    return (dst / "custom.css").read_text()


def test_structural_classes_always_present(tmp_path):
    css = _render({"features": {}}, tmp_path)   # no gated features at all
    for c in STRUCTURAL:
        assert c in css, f"structural class {c} missing"
    # gated surfaces stay off
    assert ".read-marker" not in css
    assert ".paper-post" not in css


def test_read_marker_gated_on_read_tracker(tmp_path):
    assert ".read-marker" not in _render({"features": {}}, tmp_path)
    assert ".read-marker" in _render({"features": {"read_tracker": True}}, tmp_path)


def test_papers_surface_gated_and_rich(tmp_path):
    off = _render({"content_types": {"papers": {"enabled": False}}}, tmp_path)
    assert ".paper-post" not in off
    on = _render({"content_types": {"papers": {"enabled": True}}}, tmp_path)
    # the FULL frank surface, not a minified subset
    for c in (".paper-post .paper-capability-matrix",
              ".paper-post .mermaid .quadrantChart",
              ".paper-post .paper-prev-next",
              ".paper-reference-chip--vendor-docs"):
        assert c in on, f"rich papers class {c} missing"
    assert "#1f3a5f" in on   # frank's baked mermaid node fill


def test_mermaid_palette_override_when_set(tmp_path):
    css = _render({"content_types": {"papers": {"enabled": True}},
                   "features": {"css": {"mermaid_palette":
                     {"node": "#111111", "stroke": "#222222",
                      "edge": "#333333", "label": "#444444"}}}}, tmp_path)
    assert "CONFIG palette override" in css
    for v in ("#111111", "#222222", "#333333", "#444444"):
        assert v in css
    assert "#1f3a5f" in css   # base papers palette retained; override wins by order


def test_palette_override_absent_without_config(tmp_path):
    css = _render({"content_types": {"papers": {"enabled": True}}}, tmp_path)
    assert "CONFIG palette override" not in css
    assert "#1f3a5f" in css   # baked palette still present
