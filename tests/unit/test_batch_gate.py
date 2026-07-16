"""batch-gate.sh — reproducible per-batch gate (validate + hugo build check).

The batch rewrite workflow (#26) gates each batch of posts with one command:
run the educational gate over the batch, then a hugo build check. The build
step auto-skips (BATCH_GATE_SKIP_BUILD=1) so the validate/orchestration path is
unit-testable without a Hugo/Go toolchain.
"""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GATE = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "batch-gate.sh")

GOOD_FM = {"title": "x", "series": ["building"], "reader_goal": "do the thing",
           "diataxis": ["how-to"]}
GOOD_BODY = "## Runbook\n\n```bash\nls\n```\n\n```mermaid\nflowchart TD; A-->B\n```\n"


def _blog(tmp_path):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump({
        "series": [{"key": "building", "content_type": "posts"}],
        "quality": {"enabled": True, "gate": {"min_command_blocks": 1}},
    }))
    d = tmp_path / "content" / "docs" / "building"
    d.mkdir(parents=True)
    return d


def _post(dir_, slug, fm, body):
    p = dir_ / slug
    p.mkdir()
    idx = p / "index.md"
    idx.write_text("---\n" + yaml.safe_dump(fm) + "---\n\n" + body)
    return idx


def _run(*posts, skip_build="1"):
    # Pin the validator's interpreter to this venv (has pyyaml); real blogs use python3.
    env = dict(os.environ, BATCH_GATE_SKIP_BUILD=skip_build, PYTHON=sys.executable)
    return subprocess.run(["bash", GATE, *map(str, posts)],
                          capture_output=True, text=True, env=env)


def test_good_batch_passes(tmp_path):
    d = _blog(tmp_path)
    p = _post(d, "01-a", GOOD_FM, GOOD_BODY)
    r = _run(p)
    assert r.returncode == 0, r.stderr
    assert "BATCH GATE PASS" in r.stdout


def test_bad_batch_fails(tmp_path):
    d = _blog(tmp_path)
    p = _post(d, "01-bad", {"title": "x", "series": ["building"]}, "prose only\n")
    r = _run(p)
    assert r.returncode == 1
    assert "BATCH GATE FAILED" in (r.stdout + r.stderr)


def test_mixed_batch_fails(tmp_path):
    d = _blog(tmp_path)
    good = _post(d, "01-a", GOOD_FM, GOOD_BODY)
    bad = _post(d, "02-b", {"title": "y", "series": ["building"]}, "prose only\n")
    r = _run(good, bad)
    assert r.returncode == 1


def test_skip_build_env_honored(tmp_path):
    # With BATCH_GATE_SKIP_BUILD=1 the script must not require hugo/go.
    d = _blog(tmp_path)
    p = _post(d, "01-a", GOOD_FM, GOOD_BODY)
    r = _run(p, skip_build="1")
    assert r.returncode == 0
    assert "build check skipped" in (r.stdout + r.stderr).lower()


def test_skill_documents_batch_mode():
    text = open(os.path.join(ROOT, "skills", "post-rewrite", "SKILL.md")).read()
    assert "Batch" in text, "no batch/campaign section in post-rewrite SKILL.md"
    assert "batch-gate.sh" in text, "batch section must reference the batch gate script"
    assert "hugo-serve.sh" in text, "batch section must reference the live-preview script"
