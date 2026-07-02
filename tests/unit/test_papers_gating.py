"""P3.T1 — papers content-type gating.

When content_types.papers.enabled, the render materializes the papers shared
assets (shortcodes + cross-link partials); with a stoa-style config (no
content_types.papers) NONE of it materializes.
"""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

PAPERS_MARKERS = [
    "layouts/shortcodes/papers/landscape.html",
    "layouts/shortcodes/papers/capability-matrix.html",
    "layouts/shortcodes/papers/scar.html",
    "layouts/partials/papers-backlink.html",
]


def _bootstrap(answers, target):
    r = subprocess.run(["bash", RENDER, answers, str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def test_papers_materialized_when_enabled(tmp_path):
    blog = _bootstrap(os.path.join(FIX, "answers-papers-v2.yaml"), tmp_path / "blog")
    for m in PAPERS_MARKERS:
        assert (blog / m).exists(), f"expected papers asset materialized: {m}"


def test_papers_absent_for_non_papers_blog(tmp_path):
    # stoa-style v2 config: no content_types.papers -> nothing under content-type-papers
    stoa = yaml.safe_load(open(os.path.join(FIX, "stoa-v2.expected.yaml")))
    ans = tmp_path / "stoa-answers.yaml"
    ans.write_text(yaml.safe_dump(stoa))
    blog = _bootstrap(str(ans), tmp_path / "blog")
    assert not (blog / "layouts" / "shortcodes" / "papers").exists()
    for m in PAPERS_MARKERS:
        assert not (blog / m).exists(), f"papers asset leaked into non-papers blog: {m}"
