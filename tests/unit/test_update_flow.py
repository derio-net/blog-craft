"""P6.T2 — 3-way-merge update flow (staging classify + diff3, no auto-resolve)."""
from pathlib import Path

from update import apply_plan, default_manifest, dry_run_diff, plan_update, three_way

M = default_manifest()


def _mk(root: Path, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def _plan(tmp_path, base, blog, stg):
    _mk(tmp_path / "base", base)
    _mk(tmp_path / "blog", blog)
    _mk(tmp_path / "stg", stg)
    return plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M)


def test_framework_replace_and_content_left(tmp_path):
    plan = _plan(
        tmp_path,
        base={"layouts/x.html": "A\n", "content/p.md": "c\n"},
        blog={"layouts/x.html": "A\n", "content/p.md": "LOCAL\n"},
        stg={"layouts/x.html": "B\n", "content/p.md": "INC\n"},
    )
    by = {e["path"]: e for e in plan}
    assert by["layouts/x.html"]["action"] == "replace"   # framework changed -> overwrite
    assert "content/p.md" not in by                      # content is left alone


def test_merged_clean_3way(tmp_path):
    # hugo.toml is 'merged'; local unchanged from base, incoming changed -> clean merge
    plan = _plan(
        tmp_path,
        base={"hugo.toml": "line1\nline2\n"},
        blog={"hugo.toml": "line1\nline2\n"},
        stg={"hugo.toml": "line1-new\nline2\n"},
    )
    e = {x["path"]: x for x in plan}["hugo.toml"]
    assert e["action"] == "merge"
    assert b"line1-new" in e["merged"] and b"<<<<<<<" not in e["merged"]


def test_merged_conflict_surfaced(tmp_path):
    plan = _plan(
        tmp_path,
        base={"hugo.toml": "shared\n"},
        blog={"hugo.toml": "LOCAL-EDIT\n"},
        stg={"hugo.toml": "INCOMING-EDIT\n"},
    )
    e = {x["path"]: x for x in plan}["hugo.toml"]
    assert e["action"] == "conflict"


def test_add_new_framework_file(tmp_path):
    plan = _plan(
        tmp_path,
        base={},
        blog={},
        stg={"layouts/new.html": "N\n"},
    )
    assert {x["path"]: x for x in plan}["layouts/new.html"]["action"] == "add"


def test_dry_run_and_apply(tmp_path):
    plan = _plan(
        tmp_path,
        base={"layouts/x.html": "A\n"},
        blog={"layouts/x.html": "A\n"},
        stg={"layouts/x.html": "B\n"},
    )
    assert "REPLACE" in dry_run_diff(plan)
    conflicts = apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert conflicts == []
    assert (tmp_path / "blog" / "layouts" / "x.html").read_text() == "B\n"   # applied


def test_three_way_helper_direct(tmp_path):
    _mk(tmp_path, {"b": "x\n", "l": "x\n", "i": "y\n"})
    merged, conflict = three_way(tmp_path / "b", tmp_path / "l", tmp_path / "i")
    assert not conflict and merged == b"y\n"
