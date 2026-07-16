"""build-time Mermaid syntax linter — validate_mermaid.py (#27)."""
import os
import subprocess
import sys

import yaml

from validate_mermaid import find_mermaid_blocks, lint_mermaid_block, validate_file

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALIDATOR = os.path.join(ROOT, "tools", "validate_mermaid.py")

CLEAN = """flowchart TD
  subgraph db [Database]
    pg[(Postgres)]
  end
  A["node with <br/> break"] -->|logs| pg
"""


# --- lint_mermaid_block ----------------------------------------------------

def test_clean_diagram_no_findings():
    assert lint_mermaid_block(CLEAN) == []


def test_init_directive_clean():
    src = '%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%\nflowchart TD\n  A-->B\n'
    assert lint_mermaid_block(src) == []


def test_subgraph_targeting_edge_flagged():
    src = "flowchart TD\n subgraph db\n  pg[x]\n end\n A --> db\n"
    assert any("subgraph" in m.lower() for _, m in lint_mermaid_block(src))


def test_edge_to_real_node_in_subgraph_clean():
    src = "flowchart TD\n subgraph db\n  pg[x]\n end\n A -->|logs| pg\n"
    assert lint_mermaid_block(src) == []


def test_bare_br_flagged():
    assert any("br" in m.lower() for _, m in lint_mermaid_block('flowchart TD\n A["x<br>y"]\n'))


def test_self_closed_br_clean():
    assert lint_mermaid_block('flowchart TD\n A["x<br/>y"]\n B["z<br />w"]\n') == []


def test_unbalanced_bracket_flagged():
    # A genuinely unbalanced count (two '[', no ']') — an unquoted bracket left
    # open in a label. (Balanced-but-misplaced brackets are a stray-token error,
    # out of scope for this conservative count-based check.)
    issues = lint_mermaid_block("flowchart TD\n A[label with [ unclosed\n")
    assert any("bracket" in m.lower() for _, m in issues)


def test_bracket_in_quotes_clean():
    assert lint_mermaid_block('flowchart TD\n A["text with ] in quotes"]\n') == []


# --- block discovery + line numbers ---------------------------------------

def test_find_blocks_line_numbers():
    md = "---\ntitle: t\n---\n\ntext\n\n```mermaid\nflowchart TD\n A-->B\n```\n"
    blocks = find_mermaid_blocks(md)
    assert len(blocks) == 1
    start, src = blocks[0]
    assert start == 8  # 1-based line of the first content line inside the fence
    assert "flowchart" in src


def test_validate_file_reports_path_and_line():
    md = "---\nt: 1\n---\n\n```mermaid\nflowchart TD\n subgraph db\n end\n A --> db\n```\n"
    fails = validate_file("post.md", md)
    assert fails and fails[0].startswith("post.md:")
    assert ": " in fails[0]


# --- CLI + flag ------------------------------------------------------------

BAD = "```mermaid\nflowchart TD\n subgraph db\n  x[y]\n end\n A --> db\n```\n"


def _cfg(tmp_path, mermaid_syntax=None):
    q = {"enabled": True}
    if mermaid_syntax is not None:
        q["mermaid_syntax"] = mermaid_syntax
    c = tmp_path / ".blog-craft.yaml"
    c.write_text(yaml.safe_dump({"quality": q}))
    return c


def _post(tmp_path, body):
    p = tmp_path / "index.md"
    p.write_text("---\ntitle: t\n---\n\n" + body)
    return p


def _run(cfg, *paths):
    return subprocess.run(
        [sys.executable, VALIDATOR, "--config", str(cfg), *map(str, paths)],
        capture_output=True, text=True,
    )


def test_cli_fails_on_bad(tmp_path):
    r = _run(_cfg(tmp_path), _post(tmp_path, BAD))
    assert r.returncode == 1
    assert "index.md:" in (r.stdout + r.stderr)


def test_cli_on_by_default_when_flag_absent(tmp_path):
    r = _run(_cfg(tmp_path), _post(tmp_path, BAD))  # no mermaid_syntax key
    assert r.returncode == 1


def test_cli_disabled_flag(tmp_path):
    r = _run(_cfg(tmp_path, mermaid_syntax=False), _post(tmp_path, BAD))
    assert r.returncode == 0
    assert "disabled" in (r.stdout + r.stderr).lower()


def test_cli_clean_passes(tmp_path):
    r = _run(_cfg(tmp_path), _post(tmp_path, "```mermaid\nflowchart TD\n A-->B\n```\n"))
    assert r.returncode == 0, r.stderr
