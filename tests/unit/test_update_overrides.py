"""Consumer-declared framework divergences are durable update inputs (#88)."""
from pathlib import Path

import pytest

import update
from update import (default_manifest, load_overrides, overrides_now_upstream,
                    overrides_path)

M = default_manifest()


def _overrides(blog: Path, text: str) -> None:
    overrides_path(blog).write_text(text)


def test_load_overrides_accepts_a_declared_framework_path(tmp_path):
    _overrides(tmp_path, """\
overrides:
  - path: layouts/_default/home.html
    reason: Add the publication's mobile navigation
    diverged_from: v0.22.2
""")

    got = load_overrides(tmp_path, M)
    assert got["layouts/_default/home.html"]["reason"] == "Add the publication's mobile navigation"


@pytest.mark.parametrize("text, error", [
    ("overrides: {}\n", "must be a list"),
    ("overrides:\n  - path: layouts/x.html\n    reason: why\n", "exactly path, reason, and diverged_from"),
    ("overrides:\n  - path: hugo.toml\n    reason: why\n    diverged_from: v0.22.2\n", "not a framework path"),
    ("overrides:\n  - path: ../layouts/x.html\n    reason: why\n    diverged_from: v0.22.2\n", "staging-relative"),
])
def test_load_overrides_rejects_invalid_declarations(tmp_path, text, error):
    _overrides(tmp_path, text)
    with pytest.raises(ValueError, match=error):
        load_overrides(tmp_path, M)


def test_overrides_now_upstream_reports_a_redundant_declaration(tmp_path):
    path = "layouts/x.html"
    (tmp_path / "layouts").mkdir()
    (tmp_path / "layouts" / "x.html").write_text("same\n")
    staging = tmp_path / "staging"
    (staging / "layouts").mkdir(parents=True)
    (staging / path).write_text("same\n")
    overrides = {path: {"path": path, "reason": "Temporary local patch", "diverged_from": "v0.22.2"}}

    assert overrides_now_upstream(tmp_path, staging, M, {}, overrides) == [path]


def test_main_reports_declared_divergences_and_upstream_matches(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("version: 5\n")
    _overrides(tmp_path, """\
overrides:
  - path: layouts/x.html
    reason: Temporary local patch
    diverged_from: v0.22.2
""")
    staging = tmp_path / "staging"
    (staging / "layouts").mkdir(parents=True)
    (staging / "layouts" / "x.html").write_text("same\n")
    (tmp_path / "layouts").mkdir()
    (tmp_path / "layouts" / "x.html").write_text("same\n")
    monkeypatch.setattr(update, "render_staging", lambda c, d: staging)

    assert update._main(["--config", str(cfg), "--blog", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "1 declared divergence(s)" in out
    assert "layouts/x.html" in out
    assert "now matches upstream" in out


def test_main_refuses_invalid_override_before_rendering(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("version: 5\n")
    _overrides(tmp_path, "overrides: {}\n")
    monkeypatch.setattr(update, "render_staging", lambda c, d: pytest.fail("must not render"))

    assert update._main(["--config", str(cfg), "--blog", str(tmp_path)]) == 2
    assert "must be a list" in capsys.readouterr().err
