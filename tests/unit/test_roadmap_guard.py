"""P4.T3 — roadmap-as-data + banners + weight-zero guard."""
import glob
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _bootstrap(tmp_path):
    cfg = yaml.safe_load(open(os.path.join(FIX, "stoa-v2.expected.yaml")))
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = tmp_path / "blog"
    subprocess.run(["bash", RENDER, str(ans), str(blog)], check=True, capture_output=True, text=True)
    return blog


def test_weight_zero_guard_and_banner_ship(tmp_path):
    blog = _bootstrap(tmp_path)
    assert (blog / ".hookify.warn-hextra-weight-zero.md").exists()
    assert (blog / "layouts" / "partials" / "site-banner.html").exists()


def test_roadmap_renders_from_data(tmp_path):
    blog = _bootstrap(tmp_path)
    (blog / "data").mkdir(exist_ok=True)
    (blog / "data" / "roadmap.yaml").write_text(yaml.safe_dump(
        {"layers": [{"name": "L1 Alpha", "desc": "first layer"},
                    {"name": "L9 Omega", "desc": "future", "upcoming": True}]}))
    page = blog / "content" / "docs" / "forum" / "99-roadmap"
    page.mkdir(parents=True)
    (page / "index.md").write_text("---\ntitle: RM\nseries: [forum]\nweight: 99\n---\n{{< roadmap >}}\n")

    r = subprocess.run(["hugo", "--buildDrafts"], cwd=str(blog), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(str(blog / "public" / "**" / "99-roadmap" / "index.html"), recursive=True)
    assert hits, "roadmap page not built"
    html = open(hits[0]).read()
    assert "roadmap-layer" in html
    assert "L1 Alpha" in html and "L9 Omega" in html
    assert "layer-upcoming" in html   # the upcoming flag rendered
