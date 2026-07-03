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
        {"layers": [
            {"num": 1, "key": "hw", "title": "Hardware — Nodes",
             "sub_items": ["3x NUC", "2x Pi"], "tags": ["x86", "arm64"]},
            {"num": "—", "key": "upcoming", "title": "Virtual Machines — upcoming",
             "sub_items": ["KubeVirt"], "tags": ["KVM"]},
        ]}))
    page = blog / "content" / "docs" / "forum" / "99-roadmap"
    page.mkdir(parents=True)
    (page / "index.md").write_text("---\ntitle: RM\nseries: [forum]\nweight: 99\n---\n{{< roadmap >}}\n")

    r = subprocess.run(["hugo", "--buildDrafts"], cwd=str(blog), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(str(blog / "public" / "**" / "99-roadmap" / "index.html"), recursive=True)
    assert hits, "roadmap page not built"
    html = open(hits[0]).read()
    assert "roadmap-card layer-hw" in html          # per-layer accent class
    assert "Hardware — Nodes" in html
    assert "sub-item" in html and "3x NUC" in html   # sub-items rendered
    assert "tag" in html and "arm64" in html          # tags rendered
    assert "layer-upcoming" in html                   # upcoming key -> dashed class
