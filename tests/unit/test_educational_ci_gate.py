"""The shipped blog CI wires the educational-writing gate iff quality.enabled."""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDERER = os.path.join(ROOT, "tools", "render-template")
TMPL = os.path.join(ROOT, "templates", "hugo-hextra", ".github", "workflows", "blog-ci.yml.tmpl")


def _render(cfg, tmp_path):
    src = tmp_path / "src" / ".github" / "workflows"
    src.mkdir(parents=True)
    (src / "blog-ci.yml.tmpl").write_text(open(TMPL).read())
    dst = tmp_path / "dst"; dst.mkdir()
    ans = tmp_path / "a.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(tmp_path / "src"), "--dst", str(dst), "--answers", str(ans)],
                   cwd=RENDERER, check=True, capture_output=True, text=True)
    return (dst / ".github" / "workflows" / "blog-ci.yml").read_text()


def test_quality_enabled_wires_gate_step(tmp_path):
    cfg = {"quality": {"enabled": True}, "ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "Validate post quality" in y
    assert "scripts/validate_educational.py" in y


def test_quality_absent_no_gate_step(tmp_path):
    cfg = {"ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "validate_educational.py" not in y
    assert "Hugo build" in y  # core still present


def test_quality_disabled_no_gate_step(tmp_path):
    cfg = {"quality": {"enabled": False}, "ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "validate_educational.py" not in y
