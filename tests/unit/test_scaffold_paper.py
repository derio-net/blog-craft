"""P3.T1.S3 — scaffold-paper.sh produces a valid bundle + dossier."""
import os
import subprocess
import sys

from dossier_parser import parse_dossier, section
from validate_papers import parse_frontmatter, validate_paper

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "scaffold-paper.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
ENV = dict(os.environ, PYTHON=sys.executable)  # venv python has pyyaml


def test_scaffold_paper(tmp_path):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(open(os.path.join(FIX, "answers-papers-v2.yaml")).read())
    r = subprocess.run(["bash", TOOL, "--config", str(cfg), "7", "self-hosted"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr

    idx = tmp_path / "content" / "docs" / "papers" / "07-self-hosted" / "index.md"
    assert idx.exists()
    fm = parse_frontmatter(idx.read_text())
    assert fm["paper_number"] == 7
    assert fm["weight"] == 8          # 7 + weight_offset(1)
    assert fm["series"] == ["papers"]
    # weight invariant + required fields hold on a fresh scaffold
    assert validate_paper(fm, weight_offset=1) == []

    doss = tmp_path / "docs" / "papers-dossiers" / "07-self-hosted" / "dossier.md"
    assert doss.exists()
    data = parse_dossier(doss.read_text())
    # H2-section dossier: located by token, tolerant of the parenthetical annotation
    assert isinstance(section(data, "vendors"), list) and section(data, "vendors")
    assert section(data, "primary_sources", "sources") and section(data, "artefacts")


def test_scaffold_refuses_duplicate(tmp_path):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(open(os.path.join(FIX, "answers-papers-v2.yaml")).read())
    subprocess.run(["bash", TOOL, "--config", str(cfg), "7", "x"], capture_output=True, text=True, env=ENV, check=True)
    r2 = subprocess.run(["bash", TOOL, "--config", str(cfg), "7", "x"], capture_output=True, text=True, env=ENV)
    assert r2.returncode != 0
