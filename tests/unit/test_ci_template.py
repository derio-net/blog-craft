"""P5.T4.S1 — shipped blog CI template renders config-dependent steps."""
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


def test_papers_blog_gets_dossier_step_and_container_deploy(tmp_path):
    cfg = {"content_types": {"papers": {"dossier_dir": "docs/papers-dossiers"}},
           "ci": {"deploy": {"kind": "container_pages"}}}
    y = _render(cfg, tmp_path)
    assert "Validate papers" in y
    assert "docs/papers-dossiers" in y
    assert "container image" in y   # deploy tail selected by ci.deploy.kind


def test_non_papers_none_deploy_prunes_steps(tmp_path):
    cfg = {"ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "Validate papers" not in y   # no papers -> no dossier step
    assert "deploy:" not in y            # kind none -> no deploy job
    assert "Hugo build" in y             # validation core always present
