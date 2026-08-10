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


# ==============================================================================
# P7 — the THIRD migration axis: a CAPABILITY ABSORPTION (stk-5)
# ==============================================================================
# The two axes above are about a path blog-craft ALREADY shipped moving house.
# This one is different in kind: `scripts/build-sheets.py` and
# `scripts/generate-stickers.py` were never shipped before — they lived in one
# operator's private directory (`blog/_private/frank-stickers/`) and blog-craft
# has now absorbed the capability. The same table retires them, which is the
# point: no new machinery, one declaration.
#
# Two things about this axis are NOT like the first two, and both are asserted
# below because both are easy to get wrong from the outside:
#
#   * The row is ARMED FOR EVERY BLOG. `_private/frank-stickers/x` can never
#     equal `scripts/x`, so unlike the CI-workflow row the equality-drop in
#     `legacy_dests()` never fires here. Inertness for gondor and stoa comes
#     from `plan_update`'s `(blog / d).exists()` test (update.py:161) — the file
#     simply is not there — and, one layer earlier, from the feature gate: a
#     blog with `features.stickers.enabled` false has no such path in staging at
#     all.
#
#   * `scripts/**` is FRAMEWORK, so the realistic case is REPLACE, not RELOCATE.
#     `relocate` needs the legacy copy to be byte-identical to the staged one;
#     the shipped scripts are a port with deliberate fixes, so a real frank-
#     shaped blog plans `replace` — blog-craft's copy lands and the operator's
#     is retired, which is what `framework` MEANS. Both actions retire the
#     legacy copy; only the dry-run wording differs. Both are pinned.

BUILD_SHEETS = "scripts/build-sheets.py"
GEN_STICKERS = "scripts/generate-stickers.py"
LEGACY_DIR = "_private/frank-stickers"


# --- resolving the legacy destinations ----------------------------------------

def test_both_sticker_scripts_have_a_legacy_dest_under_the_private_dir():
    assert legacy_dests(BUILD_SHEETS, SITE_CFG, M) == \
        ["blog/_private/frank-stickers/build-sheets.py"]
    assert legacy_dests(GEN_STICKERS, SITE_CFG, M) == \
        ["blog/_private/frank-stickers/generate-stickers.py"]


def test_the_sticker_rows_expand_site_for_a_config_root_site():
    """`{site}/` is the site prefix, which is empty when the site IS the root."""
    assert legacy_dests(BUILD_SHEETS, ROOT_CFG, M) == \
        ["_private/frank-stickers/build-sheets.py"]
    assert legacy_dests(GEN_STICKERS, ROOT_CFG, M) == \
        ["_private/frank-stickers/generate-stickers.py"]


def test_the_sticker_rows_are_armed_for_every_blog_not_dropped_by_equality():
    """Unlike the CI-workflow row, the equality-drop can never fire here.

    A private directory is not the scripts directory under any `site_dir`, so
    both cfgs keep the row. This is the assertion that stops a later reader
    believing the equality-drop is what makes stickers inert for other blogs —
    it is not; the missing FILE is.
    """
    for cfg in (SITE_CFG, ROOT_CFG):
        for p in (BUILD_SHEETS, GEN_STICKERS):
            assert legacy_dests(p, cfg, M), f"{p} must stay armed for {cfg}"
            assert legacy_dests(p, cfg, M)[0] != map_dest(p, cfg, M)


def test_the_scripts_are_still_framework_and_site_rooted():
    """Phase 4 asserted this; P7's planned actions depend on it, so it is pinned
    here too — a class change would silently turn `replace` into a 3-way merge."""
    from update import classify, root_of
    for p in (BUILD_SHEETS, GEN_STICKERS):
        assert classify(p, M) == "framework"
        assert root_of(p, M) == "site"
        assert map_dest(p, SITE_CFG, M) == "blog/" + p


# --- planning: the operator's copy is retired, not left beside a new one ------

def test_frank_shaped_blog_plans_replace_for_a_DIFFERING_private_copy(tmp_path):
    """The realistic case. frank's scripts are not the shipped port's bytes."""
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED PORT\n", GEN_STICKERS: "SHIPPED SHIM\n"})
    _mk(tmp_path / "blog", {f"blog/{LEGACY_DIR}/build-sheets.py": "frank's 59 lines\n",
                            f"blog/{LEGACY_DIR}/generate-stickers.py": "frank's generator\n"})
    plan = {e["path"]: e for e in
            plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)}

    for p, name in ((BUILD_SHEETS, "build-sheets.py"), (GEN_STICKERS, "generate-stickers.py")):
        e = plan[p]
        assert e["action"] == "replace", \
            f"framework + differing bytes is a replace, not a relocate (got {e['action']})"
        assert e["dest"] == "blog/" + p
        assert e["legacy"] == f"blog/{LEGACY_DIR}/{name}"
        assert e["legacy_floor"] == "blog", "pruning must stop at the site dir"


def test_a_byte_identical_private_copy_is_a_pure_move(tmp_path):
    """The degenerate case the word `relocate` is reserved for."""
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SAME\n"})
    _mk(tmp_path / "blog", {f"blog/{LEGACY_DIR}/build-sheets.py": "SAME\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[BUILD_SHEETS]
    assert e["action"] == "relocate"
    assert e["legacy"] == f"blog/{LEGACY_DIR}/build-sheets.py"


def test_a_correct_copy_at_BOTH_paths_prunes_only_the_stale_duplicate(tmp_path):
    """Half-migrated: someone already copied the shipped script into scripts/."""
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED\n"})
    _mk(tmp_path / "blog", {"blog/scripts/build-sheets.py": "SHIPPED\n",
                            f"blog/{LEGACY_DIR}/build-sheets.py": "the stale one\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    e = {x["path"]: x for x in plan}[BUILD_SHEETS]
    assert e["action"] == "prune"

    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / "blog/scripts/build-sheets.py").read_text() == "SHIPPED\n"
    assert not (tmp_path / "blog" / "blog" / "_private").exists()


# --- applying: the private directory goes, the site directory never does -------

def test_apply_retires_both_scripts_and_prunes_the_emptied_private_dir(tmp_path):
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED PORT\n", GEN_STICKERS: "SHIPPED SHIM\n"})
    _mk(tmp_path / "blog", {f"blog/{LEGACY_DIR}/build-sheets.py": "frank's\n",
                            f"blog/{LEGACY_DIR}/generate-stickers.py": "frank's\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    assert apply_plan(tmp_path / "blog", tmp_path / "stg", plan) == []

    blog = tmp_path / "blog"
    assert (blog / "blog/scripts/build-sheets.py").read_text() == "SHIPPED PORT\n"
    assert (blog / "blog/scripts/generate-stickers.py").read_text() == "SHIPPED SHIM\n"
    assert not (blog / "blog" / LEGACY_DIR).exists(), "the private dir is retired"
    assert not (blog / "blog" / "_private").exists(), "and so is the dir it emptied"
    assert (blog / "blog").is_dir(), "but NEVER the operator's site directory"


def test_the_private_dir_SURVIVES_while_it_still_holds_operator_files(tmp_path):
    """frank's real tree, and the reason the runbook cannot promise a clean dir.

    Measured on frank 2026-08-03: `blog/_private/frank-stickers/` holds
    stickers.yaml, README.md, images/, sheets/, .DS_Store and __pycache__/
    alongside the two scripts. /update retires the scripts and stops — the rest
    is `content` (or noise) and tools/migrate_stickers.py is their path.
    """
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED\n", GEN_STICKERS: "SHIPPED\n"})
    _mk(tmp_path / "blog", {f"blog/{LEGACY_DIR}/build-sheets.py": "frank's\n",
                            f"blog/{LEGACY_DIR}/generate-stickers.py": "frank's\n",
                            f"blog/{LEGACY_DIR}/stickers.yaml": "frank's prose\n",
                            f"blog/{LEGACY_DIR}/README.md": "frank's readme\n",
                            f"blog/{LEGACY_DIR}/images/sticker-01-wave.png": "PNG\n",
                            f"blog/{LEGACY_DIR}/.DS_Store": "\x00"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)

    legacy = tmp_path / "blog" / "blog" / LEGACY_DIR
    assert not (legacy / "build-sheets.py").exists()
    assert not (legacy / "generate-stickers.py").exists()
    assert (legacy / "stickers.yaml").exists(), "content is never touched by /update"
    assert (legacy / "README.md").exists()
    assert (legacy / "images" / "sticker-01-wave.png").exists()
    assert legacy.is_dir(), "so the directory itself stays — nothing was emptied"


def test_no_content_row_exists_for_the_sticker_data(tmp_path):
    """A guard against a later reader `completing` the table.

    stickers.yaml / images/ / sheets/ are the operator's irreplaceable
    artifacts. `plan_update` skips `content` outright (update.py:153), so a
    legacy_dests row keyed on one of them is inert AND misleading — it reads
    like a promise that /update retires the file, and it retires nothing.

    Asserted STRUCTURALLY (no key may classify `content`) rather than by name.
    Measured 2026-08-03: a name-based version of this guard — checking the keys
    for `stickers.yaml` / `/images/` / `/sheets/` — stayed GREEN against a
    planted `prompt_for_images.yaml` row pointing at the legacy stickers.yaml,
    because the misleading half is the VALUE and the content-ness is in the KEY.
    The class is the property that actually makes such a row a lie.
    """
    from update import classify
    table = M.get("legacy_dests") or {}
    assert table, "the table must not be empty, or this guard is vacuous"
    for k in table:
        assert classify(k, M) != "content", \
            f"legacy_dests row for a `content` path is inert and misleading: {k}"
        assert classify(k, M) is not None, f"unclassified legacy_dests key: {k}"


def test_re_running_after_apply_plans_nothing_for_the_scripts(tmp_path):
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED\n", GEN_STICKERS: "SHIPPED\n"})
    _mk(tmp_path / "blog", {f"blog/{LEGACY_DIR}/build-sheets.py": "frank's\n",
                            f"blog/{LEGACY_DIR}/generate-stickers.py": "frank's\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    again = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG)
    assert [e for e in again if e["path"] in (BUILD_SHEETS, GEN_STICKERS)] == []


def test_the_dry_run_names_the_private_copy_it_is_about_to_delete(tmp_path):
    """The dry-run IS the migration notice — the operator must see WHICH file goes."""
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED\n"})
    _mk(tmp_path / "blog", {f"blog/{LEGACY_DIR}/build-sheets.py": "frank's\n"})
    out = dry_run_diff(plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=SITE_CFG))
    assert "REPLACE" in out
    assert f"blog/{LEGACY_DIR}/build-sheets.py -> blog/scripts/build-sheets.py" in out


# --- the promise to gondor and stoa -------------------------------------------

def test_a_blog_that_never_had_them_sees_no_legacy_no_relocate_no_prune(tmp_path):
    """stk-5's inertness promise, stated precisely.

    A gondor/stoa-shaped blog that ENABLES stickers gets a plain `add` — the
    scripts are new to it. What it must NEVER get is a `legacy` key, a
    relocate, or a prune: nothing is moved and nothing is deleted, because
    `_private/frank-stickers/` does not exist there.
    """
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED\n", GEN_STICKERS: "SHIPPED\n"})
    (tmp_path / "blog").mkdir()
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=ROOT_CFG)

    assert {e["action"] for e in plan} == {"add"}
    assert not any("legacy" in e for e in plan), "nothing to move on a blog that never had it"
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert not (tmp_path / "blog" / "_private").exists(), "and nothing is created either"


def test_a_blog_already_up_to_date_plans_literally_nothing(tmp_path):
    """The second /update on such a blog: the row stays armed and stays silent."""
    _mk(tmp_path / "stg", {BUILD_SHEETS: "SHIPPED\n", GEN_STICKERS: "SHIPPED\n"})
    _mk(tmp_path / "blog", {BUILD_SHEETS: "SHIPPED\n", GEN_STICKERS: "SHIPPED\n"})
    assert plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=ROOT_CFG) == []


def test_a_blog_with_stickers_DISABLED_never_reaches_the_row(tmp_path):
    """One layer earlier than the exists() test: the feature gate.

    bootstrap-render.sh renders templates/features/stickers/ only when
    `features.stickers.enabled` is true, so a blog that never asked for
    stickers has no such path in staging and `plan_update` never iterates it.
    """
    _mk(tmp_path / "stg", {"layouts/baseof.html": "L\n"})       # no sticker scripts
    _mk(tmp_path / "blog", {"layouts/baseof.html": "L\n",
                            # even a same-named private dir is untouched
                            f"{LEGACY_DIR}/build-sheets.py": "someone else's\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=ROOT_CFG)
    assert plan == []
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / LEGACY_DIR / "build-sheets.py").exists()
