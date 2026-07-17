"""Controlled versioning — bump_version.py + check_version_bump_needed.py (#18)."""
import json
import pathlib

import bump_version as bv
import check_version_bump_needed as guard

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _mk_repo(tmp_path, version="0.5.0", uvlock_version=None):
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "blog-craft"\nversion = "{version}"\n')
    pd = tmp_path / ".claude-plugin"
    pd.mkdir()
    (pd / "plugin.json").write_text(
        json.dumps({"name": "blog-craft", "version": version}, indent=2) + "\n")
    (pd / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "blog-craft", "version": version}]}, indent=2) + "\n")
    if uvlock_version is not None:
        # Line 1 `version = 1` is the lockfile SCHEMA version — must never be
        # touched by a bump; only the blog-craft package block's version is.
        (tmp_path / "uv.lock").write_text(
            "version = 1\n"
            "revision = 3\n"
            'requires-python = ">=3.11"\n\n'
            "[[package]]\n"
            'name = "blog-craft"\n'
            f'version = "{uvlock_version}"\n'
            'source = { virtual = "." }\n\n'
            "[[package]]\n"
            'name = "pyyaml"\n'
            'version = "6.0.2"\n'
        )
    return tmp_path


# --- bump_version ----------------------------------------------------------

def test_compute_new_arithmetic():
    assert bv.compute_new("0.5.0", "patch") == "0.5.1"
    assert bv.compute_new("0.5.0", "minor") == "0.6.0"
    assert bv.compute_new("0.5.9", "major") == "1.0.0"
    assert bv.compute_new("0.5.0", "1.2.3") == "1.2.3"


def test_bump_syncs_every_surface(tmp_path):
    root = _mk_repo(tmp_path, "0.5.0")
    bv.main(["minor"], root=root)
    assert set(bv.versions(root).values()) == {"0.6.0"}


def test_check_passes_when_synced(tmp_path):
    assert bv.check(_mk_repo(tmp_path, "0.5.0")) == 0


def test_check_fails_on_drift(tmp_path):
    root = _mk_repo(tmp_path, "0.5.0")
    pj = root / ".claude-plugin" / "plugin.json"
    d = json.loads(pj.read_text())
    d["version"] = "0.4.0"          # manual drift
    pj.write_text(json.dumps(d, indent=2) + "\n")
    assert bv.check(root) == 1


def test_committed_repo_is_self_consistent():
    # Tripwire: the real repo's manifests must match pyproject.toml.
    assert bv.check(ROOT) == 0, "committed versions drifted — run tools/bump_version.py"


# --- uv.lock lockstep ------------------------------------------------------

def test_versions_includes_uvlock_when_present(tmp_path):
    root = _mk_repo(tmp_path, "0.5.0", uvlock_version="0.5.0")
    vs = bv.versions(root)
    assert vs.get("uv.lock") == "0.5.0"


def test_versions_omits_uvlock_when_absent(tmp_path):
    # A materialized blog has no uv.lock — must not crash, must not add a key.
    vs = bv.versions(_mk_repo(tmp_path, "0.5.0"))
    assert "uv.lock" not in vs
    assert set(vs.values()) == {"0.5.0"}


def test_check_fails_on_drifted_uvlock(tmp_path):
    root = _mk_repo(tmp_path, "0.5.0", uvlock_version="0.4.0")  # only uv.lock lags
    assert bv.check(root) == 1


def test_bump_updates_uvlock_but_not_schema_version(tmp_path):
    root = _mk_repo(tmp_path, "0.5.0", uvlock_version="0.5.0")
    bv.main(["minor"], root=root)
    assert set(bv.versions(root).values()) == {"0.6.0"}
    lock = (root / "uv.lock").read_text()
    assert 'name = "blog-craft"\nversion = "0.6.0"' in lock
    assert lock.startswith("version = 1\n")          # schema version untouched
    assert 'name = "pyyaml"\nversion = "6.0.2"' in lock  # other packages untouched


def test_bump_works_without_uvlock(tmp_path):
    root = _mk_repo(tmp_path, "0.5.0")  # no lockfile
    bv.main(["minor"], root=root)
    assert set(bv.versions(root).values()) == {"0.6.0"}


def test_uvlock_format_change_fails_closed(tmp_path):
    # A blog-craft package whose version line is NOT adjacent (a hypothetical
    # uv reformat) must raise, not silently skip the lockfile (fail-closed).
    import pytest
    root = _mk_repo(tmp_path, "0.5.0")
    (root / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "blog-craft"\n'
        'source = { virtual = "." }\nversion = "0.5.0"\n'  # version not adjacent
    )
    with pytest.raises(SystemExit):
        bv.versions(root)


# --- check_version_bump_needed --------------------------------------------

def test_requires_bump_paths():
    assert guard.requires_bump("templates/hugo-hextra/x.tmpl")
    assert guard.requires_bump("tools/foo.py")
    assert guard.requires_bump("skills/blog-post/SKILL.md")
    assert guard.requires_bump(".claude-plugin/plugin.json")
    assert not guard.requires_bump("docs/CONFIG.md")
    assert not guard.requires_bump("tests/unit/test_x.py")
    assert not guard.requires_bump("docs/superpowers/specs/x-design.md")


def test_guard_fails_when_behavior_changed_without_bump():
    assert guard.guard_fails(["templates/x", "docs/y.md"], "0.5.0", "0.5.0")


def test_guard_passes_when_version_bumped():
    assert not guard.guard_fails(["templates/x"], "0.5.0", "0.6.0")


def test_guard_passes_for_docs_only():
    assert not guard.guard_fails(["docs/x.md", "tests/unit/t.py"], "0.5.0", "0.5.0")
