"""Phase 4 review findings p4-r1 and p4-r3: the blog config's writing-standard
keys read the same way in validate_config and in the checker's --config."""
import os
import re

import pytest
import yaml

import validate_writing_standard as vws
from validate_config import validate_config

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def _valid():
    with open(os.path.join(FIXTURES, "valid-v2.blog-craft.yaml")) as f:
        return yaml.safe_load(f)


def _config_md_example() -> str:
    """The §15 example block in docs/CONFIG.md, as text."""
    text = open(os.path.join(ROOT, "docs", "CONFIG.md")).read()
    s15 = text[text.index("## §15"):]
    block = next(b for b in re.findall(r"```yaml\n(.*?)```", s15, re.S)
                 if "quality:" in b and "severities:" in b)
    return block


def _page(tmp_path, body):
    p = tmp_path / "p.md"
    p.write_text(body)
    return str(p)


# p4-r1: a bare `off` is YAML 1.1 for False -----------------------------------

def test_r1_config_md_example_passes_validate_config():
    example = yaml.safe_load(_config_md_example())
    assert example["quality"]["writing_standard"]["severities"]["ste.paragraph_length"] is False
    cfg = _valid()
    cfg["quality"] = example["quality"]
    cfg["series"][0]["writing_standard"] = example["series"][0]["writing_standard"]
    assert validate_config(cfg) == []


def test_r1_config_md_example_passes_the_checker_config_and_turns_the_check_off(tmp_path, capsys):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(_config_md_example())
    long_paragraph = " ".join(f"Open valve {i}." for i in range(12)) + "\n"
    page = _page(tmp_path, long_paragraph)
    assert vws.main(["--default", "ste", page]) == 0
    assert "paragraph_length" in capsys.readouterr().out  # warns by default
    assert vws.main(["--config", str(cfg), "--default", "ste", page]) == 0
    assert "paragraph_length" not in capsys.readouterr().out


def test_r1_parse_severity_overrides_maps_false_to_off_and_refuses_true():
    assert vws.parse_severity_overrides({"contractions": False}, "x") == {"contractions": "off"}
    with pytest.raises(vws.ConfigError, match="boolean true"):
        vws.parse_severity_overrides({"contractions": True}, "x")


def test_r1_a_bare_on_is_refused_with_a_clear_message(tmp_path, capsys):
    cfg = _valid()
    cfg["quality"] = yaml.safe_load("writing_standard: {severities: {contractions: on}}")
    assert any("boolean true" in e for e in validate_config(cfg))
    f = tmp_path / ".blog-craft.yaml"
    f.write_text("quality:\n  writing_standard:\n    severities:\n      contractions: on\n")
    assert vws.main(["--config", str(f), "--default", "ste", _page(tmp_path, "Fine.\n")]) == 2
    assert "boolean true" in capsys.readouterr().err


# p4-r3: unknown keys and null, refused by both --------------------------------

@pytest.mark.parametrize("block, needle", [
    ("writing_standard: {enable: true}", "unknown key 'enable'"),
    ("writing_standard:", "must be a mapping"),
])
def test_r3_both_validators_refuse(tmp_path, capsys, block, needle):
    cfg = _valid()
    cfg["quality"] = yaml.safe_load(block)
    assert any(needle in e for e in validate_config(cfg)), validate_config(cfg)
    f = tmp_path / ".blog-craft.yaml"
    f.write_text("quality:\n  " + block + "\n")
    assert vws.main(["--config", str(f), "--default", "ste", _page(tmp_path, "Fine.\n")]) == 2
    assert needle in capsys.readouterr().err
