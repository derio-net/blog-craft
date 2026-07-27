"""ai-tells lint layer — lint_post() in validate_educational.py.

Warnings-first (spec §5): only AI-vocabulary hits fail by default; the density
metrics (em-dash, negative parallelism, triads), cliche conclusion openers, and
the mode-conditional what-transfers check warn. All matching runs on prose only
— fenced code blocks, inline code spans, and frontmatter never trip the lint.
"""
import os
import shutil
import subprocess
import sys

import yaml

from validate_educational import lint_post, split_frontmatter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALIDATOR = os.path.join(ROOT, "tools", "validate_educational.py")
AI_TELLS = os.path.join(
    ROOT, "skills", "educational-writing", "references", "ai-tells.md"
)

# A believable how-to: plain prose, one bash block that CONTAINS the word
# "delve" (pins code exclusion), zero tells in the prose itself.
CLEAN = """---
title: "Rotate the backup key"
reader_goal: "Rotate the borg repo key without losing old archives."
diataxis: [how-to]
---

## Steps

The repo key lives on the NAS. Rotation keeps old archives readable
because borg wraps the master key rather than re-encrypting data.
Run the rotation from the client that owns the repo.

```bash
borg key change-passphrase /mnt/backup/repo
grep -R "delve" notes/   # a command mentioning delve must never trip the lint
```

## Verify

Mount the latest archive and read one file back. If the mount works
with the new passphrase, the rotation took. Keep the old passphrase
in the password manager until the first successful verify, then
delete it.

A restore drill once a quarter catches key drift long before an
emergency does. Schedule it with the same cron user that runs the
backup itself, so permissions match the real path.
"""

# Deliberately tell-laden: "delve" twice + "a testament to" (vocabulary),
# 5 em-dashes in well under 200 words, two "not X, but Y" sentences, three
# triads, a cliche conclusion opener, and NO what-transfers heading.
LADEN = """---
title: "A tour of the pipeline"
reader_goal: "Understand the deploy pipeline end to end."
diataxis: [tutorial]
---

## The journey

Let us delve into the pipeline — the part everyone fears — because to
delve here is a testament to real curiosity. Speed, safety, and grace
define the rollout. The gains were real, measured, and durable. The
design is not about speed, but about correctness. The rollback is not
about panic, but about practice.

The stages felt clean, tested, and boring — exactly the goal — and the
crew shipped it — twice.

In conclusion, the pipeline rewards patience.
"""


def _fixture(text):
    return split_frontmatter(text)


def test_clean_post_lints_clean():
    fm, body = _fixture(CLEAN)
    assert lint_post(fm, body) == ([], [])


def test_laden_post_vocabulary_fails_by_default():
    fm, body = _fixture(LADEN)
    failures, _ = lint_post(fm, body)
    assert any("delve" in f for f in failures), failures
    assert any("a testament to" in f for f in failures), failures


def test_laden_post_density_and_conclusion_warn():
    fm, body = _fixture(LADEN)
    _, warnings = lint_post(fm, body)
    assert any("em-dash" in w for w in warnings), warnings
    assert any("negative" in w for w in warnings), warnings
    assert any("triad" in w for w in warnings), warnings
    assert any("conclusion" in w for w in warnings), warnings


def test_severity_override_moves_vocabulary_to_warnings():
    fm, body = _fixture(LADEN)
    failures, warnings = lint_post(fm, body, {"severities": {"vocabulary": "warn"}})
    assert failures == []
    assert any("delve" in w for w in warnings), warnings


def test_severity_off_drops_the_check_entirely():
    fm, body = _fixture(LADEN)
    failures, warnings = lint_post(fm, body, {"severities": {"em_dash": "off"}})
    assert not any("em-dash" in x for x in failures + warnings)


# --- mode-conditional what-transfers check (keys off `diataxis` ONLY — never
# series names; series names are per-blog and carry no mode semantics) --------

def test_tutorial_without_transfer_heading_warns():
    fm, body = _fixture(LADEN)
    _, warnings = lint_post(fm, body)
    assert any("what-transfers" in w for w in warnings), warnings


def test_howto_reference_never_needs_transfer_heading():
    fm, body = _fixture(LADEN)
    fm = dict(fm, diataxis=["how-to", "reference"])
    failures, warnings = lint_post(fm, body)
    assert not any("what-transfers" in x for x in failures + warnings)


def test_tutorial_with_transfer_heading_passes():
    fm, body = _fixture(LADEN)
    body += "\n## What transfers\n\nAlert on the resource you exhaust first.\n"
    _, warnings = lint_post(fm, body)
    assert not any("what-transfers" in w for w in warnings)


def test_explanation_without_transfer_heading_warns():
    fm, body = _fixture(LADEN)
    fm = dict(fm, diataxis=["explanation"])
    _, warnings = lint_post(fm, body)
    assert any("what-transfers" in w for w in warnings), warnings


def test_code_and_frontmatter_are_excluded_from_matching():
    fm, body = _fixture(
        """---
title: "A testament to delving"
diataxis: [how-to]
---

The config key is named `delve` and the fixture below spells out a tell.

```text
this block is a testament to nothing — code is never linted — truly
```

Plain prose closes the post without any pattern in it.
"""
    )
    assert lint_post(fm, body) == ([], [])


# --- CLI wiring: severities, exit codes, output ------------------------------

# Gate-satisfying scaffold so CLI exit codes isolate the LINT contribution:
# actionable heading + command block + mermaid diagram.
GATE_SCAFFOLD = """
## Steps

```bash
echo ok
```

```mermaid
flowchart TD; A-->B
```
"""


def _write_post(path, fixture, extra_body="", fm_extra=None):
    fm, body = _fixture(fixture)
    if fm_extra:
        fm.update(fm_extra)
    path.write_text("---\n" + yaml.safe_dump(fm) + "---\n\n" + body + extra_body)


def _cfg(tmp_path, quality):
    c = tmp_path / ".blog-craft.yaml"
    c.write_text(yaml.safe_dump({
        "series": [{"key": "building", "content_type": "posts"}],
        "quality": quality,
    }))
    return c


def _run(validator, cfg, *paths):
    return subprocess.run(
        [sys.executable, str(validator), "--config", str(cfg), *map(str, paths)],
        capture_output=True, text=True,
    )


def test_cli_lint_defaults_fail_laden_post(tmp_path):
    cfg = _cfg(tmp_path, {"gate": {"min_command_blocks": 1}})  # no quality.lint
    p = tmp_path / "laden.md"
    _write_post(p, LADEN, extra_body=GATE_SCAFFOLD)
    r = _run(VALIDATOR, cfg, p)
    assert r.returncode != 0
    assert f"LINT FAIL: {p}" in r.stdout, r.stdout
    assert f"LINT WARN: {p}" in r.stdout, r.stdout


def test_cli_lint_enabled_false_is_gate_only(tmp_path):
    cfg = _cfg(tmp_path, {"gate": {"min_command_blocks": 1},
                          "lint": {"enabled": False}})
    p = tmp_path / "laden.md"
    _write_post(p, LADEN, extra_body=GATE_SCAFFOLD)
    r = _run(VALIDATOR, cfg, p)
    assert r.returncode == 0, r.stderr
    assert "LINT" not in r.stdout


def test_cli_clean_post_exits_zero_no_lint_lines(tmp_path):
    cfg = _cfg(tmp_path, {"gate": {"min_command_blocks": 1}})
    p = tmp_path / "clean.md"
    _write_post(p, CLEAN, fm_extra={"diagram_exempt": "key rotation has no topology"})
    r = _run(VALIDATOR, cfg, p)
    assert r.returncode == 0, r.stderr
    assert "LINT" not in r.stdout


# --- blog-side data resolution (materialized blogs have no skills/ tree): the
# validator ships with a sibling scripts/ai-tells.md; when neither the plugin
# path nor the sibling exists, lint is SKIPPED loudly and the gate still runs.

def _blog_copy(tmp_path, with_data):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    v = scripts / "validate_educational.py"
    shutil.copy(VALIDATOR, v)
    if with_data:
        shutil.copy(AI_TELLS, scripts / "ai-tells.md")
    return v


def test_blog_copy_lints_via_sibling_ai_tells(tmp_path):
    v = _blog_copy(tmp_path, with_data=True)
    cfg = _cfg(tmp_path, {"gate": {"min_command_blocks": 1}})
    p = tmp_path / "laden.md"
    _write_post(p, LADEN, extra_body=GATE_SCAFFOLD)
    r = _run(v, cfg, p)
    assert r.returncode != 0
    assert f"LINT FAIL: {p}" in r.stdout, r.stdout


def test_blog_copy_without_ai_tells_skips_lint_loudly(tmp_path):
    v = _blog_copy(tmp_path, with_data=False)
    cfg = _cfg(tmp_path, {"gate": {"min_command_blocks": 1}})
    p = tmp_path / "clean.md"
    _write_post(p, CLEAN, fm_extra={"diagram_exempt": "key rotation has no topology"})
    r = _run(v, cfg, p)
    assert r.returncode == 0, r.stderr
    assert "LINT SKIPPED" in r.stdout, r.stdout
    assert "LINT FAIL" not in r.stdout
