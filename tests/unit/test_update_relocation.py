"""P4 — /update relocates stale copies instead of re-adding dead files (#61).

#61's sharpest point is that fixing `map_dest` alone does not settle the
problem:

    plan_update classifies an absent managed path as `add`. So deleting the
    inert copy and putting a correct workflow at the repo root does not settle
    it: the next /update re-adds the dead file.

So the manifest declares, per path, where earlier releases put it
(`legacy_dests:`), and the planner MOVES the operator's file rather than adding
a blank one beside it. `{site}/` expands to `<site_dir>/`, and to nothing when
the site IS the config root — so a legacy destination that coincides with the
current one is simply not a relocation.

One table covers both migration axes, which is why it is a table and not a
boolean:
  - a ROOT change  — `.github/**` moved out from under site_dir;
  - a RENAME       — the hookify rule moved to `.claude/…local.md`.
"""
from pathlib import Path

from update import (apply_plan, default_manifest, dry_run_diff, legacy_dests, map_dest,
                    plan_update)

M = default_manifest()

SITE_CFG = {"site_dir": "blog"}
ROOT_CFG = {}                       # site IS the config root

CI = ".github/workflows/blog-ci.yml"
HOOKIFY = ".claude/hookify.warn-hextra-weight-zero.local.md"


def _mk(root: Path, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


# --- resolving the legacy destinations ----------------------------------------

def test_ci_workflow_legacy_dest_is_under_site_dir():
    assert legacy_dests(CI, SITE_CFG, M) == ["blog/.github/workflows/blog-ci.yml"]


def test_no_legacy_dest_when_it_would_equal_the_current_one():
    """site_dir '.' → the workflow was already at the repo root. Nothing to move."""
    assert legacy_dests(CI, ROOT_CFG, M) == []
    assert map_dest(CI, ROOT_CFG, M) == CI


def test_hookify_legacy_dest_applies_to_every_blog():
    """A rename, not a root change — so even a site_dir-less blog has a stale copy."""
    assert legacy_dests(HOOKIFY, ROOT_CFG, M) == [".hookify.warn-hextra-weight-zero.md"]
    assert legacy_dests(HOOKIFY, SITE_CFG, M) == ["blog/.hookify.warn-hextra-weight-zero.md"]


def test_a_path_with_no_legacy_row_has_none():
    assert legacy_dests("layouts/baseof.html", SITE_CFG, M) == []


# --- planning + applying ------------------------------------------------------

def test_identical_stale_copy_is_a_pure_move(tmp_path):
    _mk(tmp_path / "stg", {CI: "WORKFLOW\n"})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": "WORKFLOW\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[CI]
    assert e["action"] == "relocate"
    assert e["dest"] == CI
    assert e["legacy"] == "blog/.github/workflows/blog-ci.yml"

    assert apply_plan(tmp_path / "blog", tmp_path / "stg", plan) == []
    assert (tmp_path / "blog" / CI).read_text() == "WORKFLOW\n"
    assert not (tmp_path / "blog" / "blog" / ".github" / "workflows" / "blog-ci.yml").exists()


def test_operator_edits_survive_the_move(tmp_path):
    """The whole point: their file MOVES, it is not re-added blank beside it.

    `.github/**` is `merged`, so a non-conflicting local edit 3-way-merges into
    the file at the NEW destination.
    """
    def wf(name, extra):
        return f"name: {name}\n\non: push\n\njobs:\n  a:\n    runs-on: x\n\n{extra}\n"

    _mk(tmp_path / "base", {CI: wf("blog", "# base")})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": wf("OPERATOR RENAMED", "# base")})
    _mk(tmp_path / "stg", {CI: wf("blog", "# shipped in the new release")})

    plan = plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[CI]
    assert e["action"] == "merge"
    assert e["legacy"] == "blog/.github/workflows/blog-ci.yml"

    assert apply_plan(tmp_path / "blog", tmp_path / "stg", plan) == []
    landed = (tmp_path / "blog" / CI).read_text()
    assert "OPERATOR RENAMED" in landed          # their edit survived the move
    assert "shipped in the new release" in landed  # and the new release landed
    assert not (tmp_path / "blog" / "blog" / ".github").exists()


def test_framework_class_relocation_replaces_and_prunes(tmp_path):
    _mk(tmp_path / "stg", {HOOKIFY: "NEW RULE\n"})
    _mk(tmp_path / "blog", {"blog/.hookify.warn-hextra-weight-zero.md": "OLD RULE\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[HOOKIFY]
    assert e["action"] == "replace"
    assert e["legacy"] == "blog/.hookify.warn-hextra-weight-zero.md"

    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / HOOKIFY).read_text() == "NEW RULE\n"
    assert not (tmp_path / "blog" / "blog" / ".hookify.warn-hextra-weight-zero.md").exists()


def test_a_merge_that_keeps_local_still_MOVES_a_relocated_file(tmp_path):
    """Where #60's NOOP and #61's relocation collide.

    #60 added `noop` for a merge that resolves entirely in local's favour:
    writing it back would rewrite the file with the bytes already in it. But on
    a RELOCATED path, `local` is the copy at the OLD destination — so writing it
    is not a no-op, it is the move. Reporting NOOP here would strand the file
    where nothing reads it and leave the stale copy in place, which is exactly
    the state #61 exists to end.
    """
    def wf(extra):
        return f"name: blog\n\non: push\n\njobs:\n  a:\n    runs-on: x\n\n{extra}\n"

    # local == base + an operator edit; incoming == base. diff3 keeps local.
    _mk(tmp_path / "base", {CI: wf("# base")})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": wf("# operator's line")})
    _mk(tmp_path / "stg", {CI: wf("# base")})

    plan = plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[CI]
    assert e["action"] == "relocate", f"a relocated path must never report noop (got {e['action']})"

    assert apply_plan(tmp_path / "blog", tmp_path / "stg", plan) == []
    landed = (tmp_path / "blog" / CI).read_text()
    assert "# operator's line" in landed, "the merge result must land, not the staged bytes"
    assert not (tmp_path / "blog" / "blog" / ".github").exists()


def test_noop_still_applies_when_there_is_no_relocation(tmp_path):
    """#60's behaviour is untouched for ordinary paths."""
    def wf(extra):
        return f"name: blog\n\non: push\n\njobs:\n  a:\n    runs-on: x\n\n{extra}\n"

    _mk(tmp_path / "base", {CI: wf("# base")})
    _mk(tmp_path / "blog", {CI: wf("# operator's line")})
    _mk(tmp_path / "stg", {CI: wf("# base")})

    plan = plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M, cfg=ROOT_CFG)
    e = {x["path"]: x for x in plan}[CI]
    assert e["action"] == "noop"
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / CI).read_text() == wf("# operator's line")


def test_a_conflict_writes_nothing_and_removes_nothing(tmp_path):
    """/update never auto-resolves — and never destroys the evidence."""
    _mk(tmp_path / "base", {CI: "shared\n"})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": "LOCAL-EDIT\n"})
    _mk(tmp_path / "stg", {CI: "INCOMING-EDIT\n"})

    plan = plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[CI]
    assert e["action"] == "conflict"

    conflicts = apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert not (tmp_path / "blog" / CI).exists(), "nothing is written on a conflict"
    stale = tmp_path / "blog" / "blog" / ".github" / "workflows" / "blog-ci.yml"
    assert stale.read_text() == "LOCAL-EDIT\n", "and nothing is removed"
    joined = " ".join(conflicts)
    assert CI in joined and "blog/.github/workflows/blog-ci.yml" in joined, \
        "both paths must be named — the operator has to know there are two"


def test_stale_duplicate_under_an_up_to_date_dest_is_pruned(tmp_path):
    """The half-migrated repo: someone already put a correct file at the root."""
    _mk(tmp_path / "stg", {CI: "WORKFLOW\n"})
    _mk(tmp_path / "blog", {CI: "WORKFLOW\n",
                            "blog/.github/workflows/blog-ci.yml": "the inert one\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[CI]
    assert e["action"] == "prune"

    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / CI).read_text() == "WORKFLOW\n"   # untouched
    assert not (tmp_path / "blog" / "blog" / ".github").exists()


def test_re_running_after_apply_plans_nothing(tmp_path):
    """#61's 'the next /update re-adds the dead file' loop, closed."""
    _mk(tmp_path / "stg", {CI: "WORKFLOW\n"})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": "WORKFLOW\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)

    again = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    assert [e for e in again if e["path"] == CI] == []


# --- pruning is careful -------------------------------------------------------

def test_directories_left_empty_by_the_move_are_removed(tmp_path):
    _mk(tmp_path / "stg", {CI: "W\n"})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": "W\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert not (tmp_path / "blog" / "blog" / ".github" / "workflows").exists()
    assert not (tmp_path / "blog" / "blog" / ".github").exists()
    assert (tmp_path / "blog" / "blog").exists(), "never prune above the moved file's own dirs"


def test_a_directory_holding_operator_files_is_kept(tmp_path):
    _mk(tmp_path / "stg", {CI: "W\n"})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": "W\n",
                            "blog/.github/workflows/operators-own.yml": "theirs\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / "blog" / ".github" / "workflows" / "operators-own.yml").exists()


# --- the dry-run IS the migration notice --------------------------------------

def test_dry_run_names_both_sides(tmp_path):
    _mk(tmp_path / "stg", {CI: "W\n"})
    _mk(tmp_path / "blog", {"blog/.github/workflows/blog-ci.yml": "W\n"})
    out = dry_run_diff(plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG))
    assert "RELOCATE" in out
    assert "blog/.github/workflows/blog-ci.yml" in out and "-> .github/workflows/blog-ci.yml" in out


def test_dry_run_explains_a_prune(tmp_path):
    _mk(tmp_path / "stg", {CI: "W\n"})
    _mk(tmp_path / "blog", {CI: "W\n", "blog/.github/workflows/blog-ci.yml": "stale\n"})
    out = dry_run_diff(plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG))
    assert "PRUNE" in out
    assert "blog/.github/workflows/blog-ci.yml" in out
    assert ".github/workflows/blog-ci.yml" in out.split("PRUNE", 1)[1]


# --- no effect on blogs that never had the problem ----------------------------

def test_a_site_dir_less_blog_sees_no_relocation_for_the_workflow(tmp_path):
    _mk(tmp_path / "stg", {CI: "W\n"})
    _mk(tmp_path / "blog", {CI: "W\n"})
    assert plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=ROOT_CFG) == []
