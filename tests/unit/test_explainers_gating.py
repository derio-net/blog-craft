"""P1.T1 — explainers content-type gating.

Mirrors test_papers_scripts.py's shape: explainers ships scripts only (no
shortcodes/partials), so its gating test is about scripts/ materialization.
"""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

SCRIPTS = ["scaffold-explainer.sh", "validate_explainers.py"]


def _bootstrap(answers, target):
    r = subprocess.run(["bash", RENDER, answers, str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def test_scripts_materialize_with_explainers(tmp_path):
    blog = _bootstrap(os.path.join(FIX, "answers-explainers-v2.yaml"), tmp_path / "blog")
    for s in SCRIPTS:
        p = blog / "scripts" / s
        assert p.exists(), f"expected explainers script materialized: {s}"
    r = subprocess.run(["python3", "-m", "py_compile", str(blog / "scripts" / "validate_explainers.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_scripts_absent_without_explainers(tmp_path):
    # stoa-style v2 config: no content_types.explainers -> nothing ships
    stoa = yaml.safe_load(open(os.path.join(FIX, "stoa-v2.expected.yaml")))
    ans = tmp_path / "stoa-answers.yaml"
    ans.write_text(yaml.safe_dump(stoa))
    blog = _bootstrap(str(ans), tmp_path / "blog")
    for s in SCRIPTS:
        assert not (blog / "scripts" / s).exists(), f"explainers script leaked into non-explainers blog: {s}"
