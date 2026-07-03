"""P7 — the papers validators ship INTO a papers blog (blog/scripts/), so a
plain-python CI / operator can run them without the blog-craft plugin."""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

SCRIPTS = ["dossier_parser.py", "validate_papers.py", "validate_dossier.py",
           "sync_dossier_to_data.py", "scaffold-paper.sh"]


def _bootstrap(cfg, tmp_path, name):
    ans = tmp_path / f"{name}.yaml"; ans.write_text(yaml.safe_dump(cfg))
    target = tmp_path / name
    r = subprocess.run(["bash", RENDER, str(ans), str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def test_validators_materialize_with_papers(tmp_path):
    blog = _bootstrap(yaml.safe_load(open(os.path.join(FIX, "answers-papers-v2.yaml"))), tmp_path, "on")
    for s in SCRIPTS:
        p = blog / "scripts" / s
        assert p.exists(), f"papers validator not shipped into blog/scripts/: {s}"
    # the shipped .py validators must be intact/valid python
    for s in SCRIPTS:
        if s.endswith(".py"):
            r = subprocess.run(["python3", "-m", "py_compile", str(blog / "scripts" / s)],
                               capture_output=True, text=True)
            assert r.returncode == 0, f"{s} did not compile: {r.stderr}"


def test_shipped_validator_matches_canonical(tmp_path):
    blog = _bootstrap(yaml.safe_load(open(os.path.join(FIX, "answers-papers-v2.yaml"))), tmp_path, "on")
    canon = open(os.path.join(ROOT, "tools", "validate_papers.py")).read()
    assert (blog / "scripts" / "validate_papers.py").read_text() == canon


def test_validators_absent_without_papers(tmp_path):
    cfg = yaml.safe_load(open(os.path.join(FIX, "stoa-v2.expected.yaml")))
    blog = _bootstrap(cfg, tmp_path, "off")  # stoa fixture has no papers content-type
    for s in SCRIPTS:
        assert not (blog / "scripts" / s).exists(), f"validator leaked into non-papers blog: {s}"
