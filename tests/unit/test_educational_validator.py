"""educational-writing gate — validate_educational.py (structural checks)."""
import subprocess
import sys

import yaml

from validate_educational import (
    _count_command_blocks,
    _normalize_modes,
    split_frontmatter,
    validate_post,
)

ROOT = __import__("os").path.dirname(
    __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
)
VALIDATOR = __import__("os").path.join(ROOT, "tools", "validate_educational.py")

GOOD_FM = {
    "title": "Graceful shutdown",
    "reader_goal": "Make the homelab shut down cleanly before the UPS battery dies.",
    "diataxis": ["how-to", "reference"],
}
GOOD_BODY = """
## Reproduce

```bash
upsc myups battery.charge
```

The charge threshold is 30%.
"""


def test_good_post_passes():
    assert validate_post(GOOD_FM, GOOD_BODY) == []


def test_missing_reader_goal_fails():
    fm = dict(GOOD_FM); del fm["reader_goal"]
    fails = validate_post(fm, GOOD_BODY)
    assert any("reader_goal" in f for f in fails)


def test_blank_reader_goal_fails():
    fm = dict(GOOD_FM, reader_goal="   ")
    assert any("reader_goal" in f for f in validate_post(fm, GOOD_BODY))


def test_missing_diataxis_fails():
    fm = dict(GOOD_FM); del fm["diataxis"]
    assert any("diataxis" in f for f in validate_post(fm, GOOD_BODY))


def test_invalid_diataxis_value_fails():
    fm = dict(GOOD_FM, diataxis=["tutorial", "nonsense"])
    fails = validate_post(fm, GOOD_BODY)
    assert any("invalid" in f and "nonsense" in f for f in fails)


def test_diataxis_aliases_normalize():
    assert _normalize_modes("howto, ref") == ["how-to", "reference"]
    assert _normalize_modes("How-To") == ["how-to"]
    assert _normalize_modes(["Explanation"]) == ["explanation"]
    # a string with alias passes validation
    assert validate_post(dict(GOOD_FM, diataxis="how_to"), GOOD_BODY) == []


def test_no_command_block_fails():
    body = "## Steps\n\nJust prose, no code at all.\n"
    assert any("evidence" in f for f in validate_post(GOOD_FM, body))


def test_mermaid_does_not_count_as_command_block():
    body = "## Steps\n\n```mermaid\ngraph TD; A-->B\n```\n"
    fails = validate_post(GOOD_FM, body)
    assert any("evidence" in f for f in fails)


def test_min_command_blocks_configurable():
    body = "## Verify\n\n```bash\nls\n```\n"
    assert validate_post(GOOD_FM, body, gate={"min_command_blocks": 2})
    assert validate_post(GOOD_FM, body, gate={"min_command_blocks": 1}) == []


def test_no_actionable_section_fails():
    body = "## Background\n\nSome context.\n\n```bash\nls\n```\n"
    assert any("actionable" in f for f in validate_post(GOOD_FM, body))


def test_actionable_headings_recognized():
    for h in ("Reproduce", "Runbook", "Recover", "Verify", "Try it yourself",
              "Step-by-step", "Rollback", "Procedure"):
        body = f"## {h}\n\n```bash\nls\n```\n"
        assert validate_post(GOOD_FM, body) == [], h


def test_count_command_blocks_tilde_fences():
    body = "~~~\ncode\n~~~\n"
    assert _count_command_blocks(body) == 1


def test_split_frontmatter_roundtrip():
    fm, body = split_frontmatter('---\ntitle: "X"\n---\n\nhello\n')
    assert fm["title"] == "X"
    assert body.strip() == "hello"


# --- CLI: content-type routing + exit codes -------------------------------

def _write(p, fm, body):
    p.write_text("---\n" + yaml.safe_dump(fm) + "---\n\n" + body)


def _run(cfg_path, *paths):
    return subprocess.run(
        [sys.executable, VALIDATOR, "--config", str(cfg_path), *map(str, paths)],
        capture_output=True, text=True,
    )


def _cfg(tmp_path):
    c = tmp_path / ".blog-craft.yaml"
    c.write_text(yaml.safe_dump({
        "series": [
            {"key": "building", "content_type": "posts"},
            {"key": "papers", "content_type": "papers"},
        ],
        "quality": {"enabled": True, "gate": {"min_command_blocks": 1}},
    }))
    return c


def test_cli_fails_on_bad_posts_post(tmp_path):
    cfg = _cfg(tmp_path)
    p = tmp_path / "bad.md"
    _write(p, {"title": "x", "series": ["building"]}, "narrative, no evidence\n")
    r = _run(cfg, p)
    assert r.returncode == 1
    assert "GATE FAILED" in r.stderr


def test_cli_skips_papers_series(tmp_path):
    cfg = _cfg(tmp_path)
    p = tmp_path / "paper.md"
    _write(p, {"title": "x", "series": ["papers"]}, "no gate fields at all\n")
    r = _run(cfg, p)
    assert r.returncode == 0
    assert "1 skipped" in r.stdout


def test_cli_respects_quality_exempt(tmp_path):
    cfg = _cfg(tmp_path)
    p = tmp_path / "ann.md"
    _write(p, {"title": "x", "series": ["building"], "quality_exempt": "announcement"},
           "just an announcement\n")
    r = _run(cfg, p)
    assert r.returncode == 0


def test_cli_passes_good_post(tmp_path):
    cfg = _cfg(tmp_path)
    p = tmp_path / "good.md"
    _write(p, {"title": "x", "series": ["building"],
               "reader_goal": "do the thing", "diataxis": ["how-to"]},
           "## Runbook\n\n```bash\nls\n```\n")
    r = _run(cfg, p)
    assert r.returncode == 0, r.stderr
    assert "1 post(s) checked" in r.stdout
