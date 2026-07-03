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


def test_github_nav_gated_on_repo_url(tmp_path):
    assert 'name = "GitHub"' not in _render(BASE, tmp_path)
    cfg = {**BASE, "project": {**BASE["project"], "repo_url": "https://github.com/derio-net/frank"}}
    toml = _render(cfg, tmp_path)
    assert 'name = "GitHub"' in toml
    assert 'url = "https://github.com/derio-net/frank"' in toml
    assert 'icon = "github"' in toml
    # GitHub sits after the series menus, before Search
    assert toml.index('name = "GitHub"') < toml.index('name = "Search"')
    assert toml.index('name = "Papers"') < toml.index('name = "GitHub"')


def test_search_weight_accounts_for_github(tmp_path):
    # 2 series -> Search at weight 3 without GitHub, 4 with it
    assert "weight = 3\n  [menu.main.params]\n    type = \"search\"" in _render(BASE, tmp_path)
    cfg = {**BASE, "project": {**BASE["project"], "repo_url": "x"}}
    assert "weight = 4\n  [menu.main.params]\n    type = \"search\"" in _render(cfg, tmp_path)
