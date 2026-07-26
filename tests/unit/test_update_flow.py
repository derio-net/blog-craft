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


# --- glossary adoption via /update (GL-8) ------------------------------------
# A blog that turns features.glossary.enabled on and runs /update must RECEIVE
# the shortcodes + stylesheet, and must never have its own curated definitions
# touched. Both halves are properties of the manifest + planner, so they are
# checkable here rather than only by hand.

GLOSSARY_SHIPPED = ("layouts/shortcodes/abbr.html",
                    "layouts/shortcodes/glossary-index.html",
                    "assets/css/glossary.css")


def test_glossary_files_arrive_as_clean_adds(tmp_path):
    plan = _plan(
        tmp_path,
        base={},                                        # not present at the recorded version
        blog={"content/p.md": "post\n"},                # blog has never had the feature
        stg={rel: "shipped\n" for rel in GLOSSARY_SHIPPED},
    )
    by = {e["path"]: e for e in plan}
    for rel in GLOSSARY_SHIPPED:
        assert by[rel]["action"] == "add", f"{rel} should arrive as a clean add"
    assert not any(e["action"] == "conflict" for e in plan)


def test_operator_definitions_are_never_touched(tmp_path):
    plan = _plan(
        tmp_path,
        base={"data/glossary.yaml": "NUT: {}\n"},
        blog={"data/glossary.yaml": "NUT:\n  name: My own words\n"},
        stg={"data/glossary.yaml": "NUT: {}\n"},
    )
    assert "data/glossary.yaml" not in {e["path"] for e in plan}, \
        "the registry is content-class — /update must never plan an action on it"


def test_a_tweaked_stylesheet_merges_rather_than_being_clobbered(tmp_path):
    # assets/css/** is 'merged', so a blog that recoloured the panel keeps it.
    # Separated by context lines: git merge-file folds ADJACENT changed lines
    # into one hunk and conflicts, which is diff3 behaviour rather than anything
    # about this feature. A real stylesheet has rules between these two.
    def css(panel, index):
        return (f".abbr-trigger {{ cursor: help; }}\n\n"
                f".abbr-panel {{ color: {panel}; }}\n\n"
                f".abbr-name {{ font-weight: 600; }}\n\n"
                f".glossary-index {{ margin: {index}; }}\n")
    plan = _plan(
        tmp_path,
        base={"assets/css/glossary.css": css("black", "1rem 0")},
        blog={"assets/css/glossary.css": css("rebeccapurple", "1rem 0")},
        stg={"assets/css/glossary.css": css("black", "2rem 0")},
    )
    e = {x["path"]: x for x in plan}["assets/css/glossary.css"]
    assert e["action"] == "merge"
    assert b"rebeccapurple" in e["merged"]      # the operator's tweak survives
    assert b"2rem 0" in e["merged"]             # and the shipped change lands
    assert b"<<<<<<<" not in e["merged"]
