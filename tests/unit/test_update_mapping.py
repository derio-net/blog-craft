"""/update generalization (spec D6): site_dir path mapping + --only scoping.

`map_dest(path, cfg)` maps a STAGING-relative materialized path to its
blog-relative destination:
  - `.reference-pool/**`     -> under `image.reference_pool` (config-rooted)
  - `prompt_for_images.yaml` -> `image.prompts_file`
  - `.blog-craft.yaml`       -> itself (config root)
  - everything else          -> under `site_dir`
Identity when site_dir is absent and the defaults hold — every existing blog's
plan is unchanged (the pre-existing test_update_flow.py is the regression
guard). Classification still runs on the STAGING-relative path (the manifest
stays site-shaped); the plan applies to the mapped destination.

`only=[glob,...]` filters the plan to matching staging-relative paths — what
makes "migrate the image machinery only" expressible on a real blog.
"""
from pathlib import Path

from update import apply_plan, default_manifest, map_dest, plan_update

M = default_manifest()

FRANK_CFG = {
    "site_dir": "blog",
    "image": {"reference_pool": ".reference-pool",
              "prompts_file": "blog/prompt_for_images.yaml"},
}


def test_map_dest_identity_without_config():
    for p in ("scripts/generate-images.py", "layouts/x.html", ".reference-pool/README.md",
              "prompt_for_images.yaml", ".blog-craft.yaml", "content/docs/a/index.md"):
        assert map_dest(p, {}) == p


def test_map_dest_site_dir_prefixes_site_paths():
    assert map_dest("scripts/generate-images.py", FRANK_CFG) == "blog/scripts/generate-images.py"
    assert map_dest("layouts/x.html", FRANK_CFG) == "blog/layouts/x.html"
    assert map_dest("content/docs/a/index.md", FRANK_CFG) == "blog/content/docs/a/index.md"


def test_map_dest_config_rooted_paths_not_site_prefixed():
    # the reference pool + config live at the CONFIG root, not under site_dir
    assert map_dest(".reference-pool/README.md", FRANK_CFG) == ".reference-pool/README.md"
    assert map_dest(".blog-craft.yaml", FRANK_CFG) == ".blog-craft.yaml"


def test_map_dest_relocates_pool_and_prompts_by_config():
    cfg = {"site_dir": "blog",
           "image": {"reference_pool": "assets/pool",
                     "prompts_file": "blog/prompts.yaml"}}
    assert map_dest(".reference-pool/README.md", cfg) == "assets/pool/README.md"
    assert map_dest("prompt_for_images.yaml", cfg) == "blog/prompts.yaml"


def _mk(root: Path, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_plan_compares_and_applies_at_mapped_dest(tmp_path):
    # staged scripts/x replaces the blog's copy at blog/scripts/x (site_dir)
    _mk(tmp_path / "stg", {"scripts/generate-images.py": "NEW\n"})
    _mk(tmp_path / "blog", {"blog/scripts/generate-images.py": "OLD\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=FRANK_CFG)
    e = {x["path"]: x for x in plan}["scripts/generate-images.py"]
    assert e["action"] == "replace"
    assert e["dest"] == "blog/scripts/generate-images.py"
    apply_plan(tmp_path / "blog", tmp_path / "stg", plan)
    assert (tmp_path / "blog" / "blog" / "scripts" / "generate-images.py").read_text() == "NEW\n"


def test_plan_unchanged_mapped_dest_skipped(tmp_path):
    _mk(tmp_path / "stg", {"scripts/x.py": "SAME\n"})
    _mk(tmp_path / "blog", {"blog/scripts/x.py": "SAME\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, cfg=FRANK_CFG)
    assert plan == []


def test_only_filters_plan_to_matching_staging_paths(tmp_path):
    _mk(tmp_path / "stg", {"scripts/x.py": "N\n", "layouts/y.html": "N\n"})
    _mk(tmp_path / "blog", {"scripts/x.py": "O\n", "layouts/y.html": "O\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M, only=["scripts/**"])
    assert [e["path"] for e in plan] == ["scripts/x.py"]


def test_only_multiple_globs_or(tmp_path):
    _mk(tmp_path / "stg", {"scripts/x.py": "N\n", "layouts/y.html": "N\n", ".gitignore": "N\n"})
    _mk(tmp_path / "blog", {"scripts/x.py": "O\n", "layouts/y.html": "O\n", ".gitignore": "O\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", None, M,
                       only=["scripts/**", "layouts/**"])
    assert sorted(e["path"] for e in plan) == ["layouts/y.html", "scripts/x.py"]
