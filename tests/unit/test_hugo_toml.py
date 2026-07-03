"""P7 — hugo.toml knobs: title decoupled from the slug; optional GitHub nav link."""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDERER = os.path.join(ROOT, "tools", "render-template")
TMPL = os.path.join(ROOT, "templates", "hugo-hextra", "hugo.toml.tmpl")

BASE = {
    "project": {"name": "Frank", "tagline": "t", "base_url": "u", "base_path": "/frank/"},
    "series": [{"key": "building", "title": "Building"},
               {"key": "papers", "title": "Papers"}],
}


def _render(cfg, tmp_path):
    src = tmp_path / "src"; src.mkdir(exist_ok=True)
    dst = tmp_path / "dst"; dst.mkdir(exist_ok=True)
    (src / "hugo.toml.tmpl").write_text(open(TMPL).read())
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(src), "--dst", str(dst), "--answers", str(ans)],
                   cwd=RENDERER, check=True, capture_output=True, text=True)
    return (dst / "hugo.toml").read_text()


def test_title_defaults_to_name(tmp_path):
    toml = _render(BASE, tmp_path)
    assert 'title = "Frank"' in toml


def test_title_overrides_name_when_set(tmp_path):
    cfg = {**BASE, "project": {**BASE["project"], "title": "Frank, the Talos Cluster"}}
    toml = _render(cfg, tmp_path)
    assert 'title = "Frank, the Talos Cluster"' in toml   # display title
    # the slug (project.name) is unchanged and still drives other identifiers


def test_project_slug_param(tmp_path):
    # projectSlug (from project.name) backs per-blog captions e.g. the dossier chip
    assert 'projectSlug = "Frank"' in _render(BASE, tmp_path)


def test_github_nav_gated_on_repo_url(tmp_path):
    assert 'name = "GitHub"' not in _render(BASE, tmp_path)
    cfg = {**BASE, "project": {**BASE["project"], "repo_url": "https://github.com/derio-net/frank"}}
    toml = _render(cfg, tmp_path)
    assert 'name = "GitHub"' in toml
    assert 'url = "https://github.com/derio-net/frank"' in toml
    assert 'icon = "github"' in toml
    # the repo link sits LAST — after Search (matches frank's nav order)
    assert toml.index('name = "Search"') < toml.index('name = "GitHub"')
    assert toml.index('name = "Papers"') < toml.index('name = "Search"')


def test_search_weight_is_stable(tmp_path):
    # 2 series -> Search always at weight 3 (n+1); GitHub, when present, is n+2
    assert "weight = 3\n  [menu.main.params]\n    type = \"search\"" in _render(BASE, tmp_path)
    cfg = {**BASE, "project": {**BASE["project"], "repo_url": "x"}}
    toml = _render(cfg, tmp_path)
    assert "weight = 3\n  [menu.main.params]\n    type = \"search\"" in toml
    assert "weight = 4\n  [menu.main.params]\n    icon = \"github\"" in toml
