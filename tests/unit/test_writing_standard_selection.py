"""Which standard a page is checked against (R5)."""
import os

import validate_writing_standard as vws

CLEAN = "This page is short and plain.\n"
DIRTY = "We don't stop.\n"          # a contraction: fails under ste


def _page(dirpath, name, fm, body):
    path = os.path.join(str(dirpath), name)
    lines = ["---"] + [f"{k}: {v}" for k, v in fm.items()] + ["---", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines) + body)
    return path


def _config(dirpath, series, quality=""):
    path = os.path.join(str(dirpath), ".blog-craft.yaml")
    lines = ["series:"]
    for key, std in series.items():
        lines.append(f"  - key: {key}")
        if std:
            lines.append(f"    writing_standard: {std}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n" + quality)
    return path


# ---- pure resolution

def test_front_matter_beats_series_beats_default():
    cfg = {"series": [{"key": "guides", "writing_standard": "ste"}]}
    assert vws.resolve_standard({"writing_standard": "other", "series": "guides"}, cfg, "x") == "other"
    assert vws.resolve_standard({"series": "guides"}, cfg, "x") == "ste"
    assert vws.resolve_standard({"series": "notes"}, cfg, "x") == "x"
    assert vws.resolve_standard({}, None, None) is None


def test_none_opts_out():
    assert vws.resolve_standard({"writing_standard": "none"}, None, "ste") is None


def test_series_as_comma_string_or_list():
    cfg = {"series": [{"key": "a", "writing_standard": "ste"}, {"key": "b"}]}
    assert vws.resolve_standard({"series": "b, a"}, cfg, None) == "ste"
    assert vws.resolve_standard({"series": ["b", "a"]}, cfg, None) == "ste"


def test_two_series_with_different_defaults_is_an_error():
    cfg = {"series": [{"key": "a", "writing_standard": "ste"},
                      {"key": "b", "writing_standard": "plain"}]}
    try:
        vws.resolve_standard({"series": ["a", "b"]}, cfg, None)
    except vws.ConfigError as e:
        assert "a" in str(e) and "b" in str(e)
    else:
        raise AssertionError("expected ConfigError")


# ---- through the CLI

def test_front_matter_beats_series_default_on_the_cli(tmp_path, capsys):
    cfg = _config(tmp_path, {"guides": "none"})
    page = _page(tmp_path, "p.md", {"series": "guides", "writing_standard": "ste"}, DIRTY)
    assert vws.main(["--config", cfg, page]) == 1


def test_series_default_beats_cli_default(tmp_path, capsys):
    cfg = _config(tmp_path, {"guides": "ste"})
    page = _page(tmp_path, "p.md", {"series": "guides"}, DIRTY)
    assert vws.main(["--config", cfg, "--default", "none", page]) == 1
    page2 = _page(tmp_path, "q.md", {"series": "notes"}, DIRTY)
    assert vws.main(["--config", cfg, page2]) == 0


def test_default_applies_and_none_skips(tmp_path, capsys):
    a = _page(tmp_path, "a.md", {"title": "A"}, CLEAN)
    b = _page(tmp_path, "b.md", {"writing_standard": "none"}, DIRTY)
    c = os.path.join(str(tmp_path), "c.md")
    with open(c, "w") as f:
        f.write(CLEAN)                                   # no front matter at all
    assert vws.main(["--default", "ste", a, b, c]) == 0
    assert "2 checked, 1 skipped" in capsys.readouterr().out


def test_no_standard_skips(tmp_path, capsys):
    a = _page(tmp_path, "a.md", {"title": "A"}, DIRTY)
    assert vws.main([a]) == 0
    assert "0 checked, 1 skipped" in capsys.readouterr().out


def test_two_series_defaults_exit_2(tmp_path, capsys):
    cfg = _config(tmp_path, {"a": "ste", "b": "none"})
    page = _page(tmp_path, "p.md", {"series": "a, b"}, CLEAN)
    assert vws.main(["--config", cfg, page]) == 2
    assert "p.md" in capsys.readouterr().err


def test_unknown_standard_exits_2_naming_the_page(tmp_path, capsys):
    page = _page(tmp_path, "p.md", {"writing_standard": "klingon"}, CLEAN)
    assert vws.main([page]) == 2
    err = capsys.readouterr().err
    assert "p.md" in err and "klingon" in err
