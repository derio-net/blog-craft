"""P7 enabler — render-identity check (prove zero VISUAL change)."""
import os
import shutil

import yaml

from reproduce import apply, render_and_diff

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "fixtures")


def _blog(tmp_path, name):
    cfg = tmp_path / f"{name}.yaml"
    cfg.write_text(open(os.path.join(FIX, "answers-papers-v2.yaml")).read())
    blog = apply(str(cfg), str(tmp_path / name))
    (blog / "data").mkdir(exist_ok=True)
    (blog / "data" / "roadmap.yaml").write_text(yaml.safe_dump(
        {"layers": [{"name": "L1", "desc": "one"}]}))
    page = blog / "content" / "docs" / "building" / "01-x"
    page.mkdir(parents=True)
    (page / "index.md").write_text("---\ntitle: X\nseries: [building]\nweight: 2\n---\n{{< roadmap >}}\n")
    return blog


def test_identical_trees_zero_render_diff(tmp_path):
    a = _blog(tmp_path, "a")
    b = tmp_path / "b"
    shutil.copytree(a, b)
    assert render_and_diff(a, b) == []


def test_layout_change_is_detected(tmp_path):
    a = _blog(tmp_path, "a")
    b = tmp_path / "b"
    shutil.copytree(a, b)
    (b / "layouts" / "shortcodes" / "roadmap.html").write_text("<div>TAMPERED ROADMAP</div>")
    diffs = render_and_diff(a, b)
    assert any("building/01-x" in d for d in diffs), diffs
