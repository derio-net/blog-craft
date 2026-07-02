"""P4.T1 — custom.css split: structural base always present + config palette."""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDERER = os.path.join(ROOT, "tools", "render-template")
TMPL = os.path.join(ROOT, "templates", "hugo-hextra", "assets", "css", "custom.css.tmpl")

STRUCTURAL = [".post-cover", ".screenshot", ".asciinema-container",
              ".site-track-banner", ".blog-series-cards", ".paper-post"]


def _render(cfg, tmp_path):
    src = tmp_path / "src"; src.mkdir()
    dst = tmp_path / "dst"; dst.mkdir()
    (src / "custom.css.tmpl").write_text(open(TMPL).read())
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(src), "--dst", str(dst), "--answers", str(ans)],
                   cwd=RENDERER, check=True, capture_output=True, text=True)
    return (dst / "custom.css").read_text()


def test_structural_classes_always_present(tmp_path):
    css = _render({"features": {}}, tmp_path)   # no css config at all
    for c in STRUCTURAL:
        assert c in css, f"structural class {c} missing"


def test_mermaid_palette_from_config(tmp_path):
    css = _render({"features": {"css": {"mermaid_palette":
                  {"node": "#111111", "stroke": "#222222", "edge": "#333333", "label": "#444444"}}}}, tmp_path)
    for v in ("#111111", "#222222", "#333333", "#444444"):
        assert v in css


def test_mermaid_palette_fallbacks(tmp_path):
    css = _render({"features": {}}, tmp_path)
    assert "#1f3a5f" in css   # node fallback
    assert "#eaf2ff" in css   # label fallback
