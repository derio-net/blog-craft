"""P5.T4.S1 — shipped blog CI template renders config-dependent steps."""
import os
import subprocess

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDERER = os.path.join(ROOT, "tools", "render-template")
TMPL = os.path.join(ROOT, "templates", "hugo-hextra", ".github", "workflows", "blog-ci.yml.tmpl")

#: The template exactly as it stood before the site_dir work (blog-craft#61),
#: kept as a fixture rather than read from git history: a revision reference
#: stops being a guard the moment this branch merges, and a checked-in copy
#: pins the output every already-synced blog has on disk.
PRE_SITE_DIR_TMPL = os.path.join(ROOT, "tests", "fixtures", "blog-ci.pre-site-dir.yml.tmpl")


def _render(cfg, tmp_path):
    src = tmp_path / "src" / ".github" / "workflows"
    src.mkdir(parents=True)
    (src / "blog-ci.yml.tmpl").write_text(open(TMPL).read())
    dst = tmp_path / "dst"; dst.mkdir()
    ans = tmp_path / "a.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(tmp_path / "src"), "--dst", str(dst), "--answers", str(ans)],
                   cwd=RENDERER, check=True, capture_output=True, text=True)
    return (dst / ".github" / "workflows" / "blog-ci.yml").read_text()


def test_papers_blog_gets_dossier_step_and_container_deploy(tmp_path):
    cfg = {"content_types": {"papers": {"dossier_dir": "docs/papers-dossiers"}},
           "ci": {"deploy": {"kind": "container_pages"}}}
    y = _render(cfg, tmp_path)
    assert "Validate papers" in y
    assert "docs/papers-dossiers" in y
    assert "container image" in y   # deploy tail selected by ci.deploy.kind


def test_non_papers_none_deploy_prunes_steps(tmp_path):
    cfg = {"ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "Validate papers" not in y   # no papers -> no dossier step
    assert "deploy:" not in y            # kind none -> no deploy job
    assert "Hugo build" in y             # validation core always present


# --- glossary gate (docs/CONFIG.md §9) ---------------------------------------

def test_glossary_enabled_wires_the_validator_step(tmp_path):
    cfg = {"features": {"glossary": {"enabled": True}},
           "ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "Validate glossary" in y
    assert "scripts/validate_glossary.py" in y
    yaml.safe_load(y)   # still parses


def test_glossary_disabled_prunes_the_step(tmp_path):
    cfg = {"features": {"glossary": {"enabled": False}},
           "ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "Validate glossary" not in y
    yaml.safe_load(y)


def test_no_glossary_key_prunes_the_step(tmp_path):
    cfg = {"features": {"read_tracker": True}, "ci": {"deploy": {"kind": "none"}}}
    y = _render(cfg, tmp_path)
    assert "Validate glossary" not in y
    yaml.safe_load(y)


# --- site_dir blogs (blog-craft#61) ------------------------------------------
# The workflow is repo-rooted — GitHub Actions loads it from
# <repo>/.github/workflows/ only. So for a blog whose Hugo site lives under
# site_dir, CI's cwd is the REPOSITORY root, not the site root, and the paths
# the workflow passes have to say so. Moving the file to the right place without
# this leaves it unable to run — #61's closing point, and independently proven:
# the pre-fix template invoked `--config .blog-craft.yaml` and `scripts/…`
# relative to the site root while map_dest's own allowlist put the config at the
# repo root. The file could not have passed had GitHub ever run it.

FULL_CFG = {
    "content_types": {"papers": {"dossier_dir": "docs/papers-dossiers"}},
    "quality": {"enabled": True},
    "features": {"glossary": {"enabled": True}},
    "ci": {"deploy": {"kind": "none"}},
}


def test_site_dir_prefixes_the_scripts_it_invokes(tmp_path):
    y = _render({**FULL_CFG, "site_dir": "blog"}, tmp_path)
    for script in ("validate_mermaid.py", "validate_images.py", "validate_glossary.py",
                   "validate_educational.py", "validate_papers.py",
                   "sync_dossier_to_data.py", "validate_dossier.py"):
        assert f"blog/scripts/{script}" in y, script
        assert f" scripts/{script}" not in y, f"unprefixed {script} would not resolve"


def test_site_dir_prefixes_the_content_globs(tmp_path):
    y = _render({**FULL_CFG, "site_dir": "blog"}, tmp_path)
    assert "blog/content/docs/*/*/index.md" in y
    assert " content/docs/*/*/index.md" not in y


def test_the_config_path_is_never_prefixed(tmp_path):
    """.blog-craft.yaml is repo-rooted — CI's cwd IS the config root."""
    y = _render({**FULL_CFG, "site_dir": "blog"}, tmp_path)
    assert "--config .blog-craft.yaml" in y
    assert "blog/.blog-craft.yaml" not in y


def test_the_dossier_glob_is_never_prefixed(tmp_path):
    """sync_dossier_to_data resolves dossier_dir against the CONFIG's directory."""
    y = _render({**FULL_CFG, "site_dir": "blog"}, tmp_path)
    assert "docs/papers-dossiers/*/dossier.md" in y
    assert "blog/docs/papers-dossiers" not in y


def test_hugo_builds_from_the_site_root(tmp_path):
    y = _render({**FULL_CFG, "site_dir": "blog"}, tmp_path)
    doc = yaml.safe_load(y)
    steps = doc["jobs"]["validate"]["steps"]
    hugo = [s for s in steps if s.get("name") == "Hugo build"][0]
    assert hugo["working-directory"] == "blog", "hugo needs the site root (and its go.mod)"


def test_site_dir_workflow_still_parses(tmp_path):
    yaml.safe_load(_render({**FULL_CFG, "site_dir": "blog"}, tmp_path))


def test_a_blog_without_site_dir_renders_byte_identically(tmp_path):
    """Every existing blog must see NO change — the regression guard."""
    a = _render(FULL_CFG, tmp_path / "a")
    b = _render({**FULL_CFG, "site_dir": "."}, tmp_path / "b")
    assert a == b, "an explicit site_dir: . must render exactly like an absent one"
    assert "working-directory" not in a, "no empty working-directory key for site-rooted blogs"
    assert "blog/" not in a


@pytest.mark.parametrize("deploy", ["none", "pages", "container_pages"])
def test_site_dir_less_render_matches_the_pre_site_dir_template(tmp_path, deploy):
    """The site-prefix machinery is inert without site_dir — proven against the
    template as it stood before #61, across every deploy shape.

    A `$site` that renders empty and a conditional working-directory are easy to
    get subtly wrong (a stray newline, an empty key). This pins the output to
    the version every already-synced blog has on disk, so /update plans no
    spurious change for them.
    """
    cfg = {**FULL_CFG, "ci": {"deploy": {"kind": deploy}}}
    new = _render(cfg, tmp_path / "new")

    src = tmp_path / "old" / ".github" / "workflows"
    src.mkdir(parents=True)
    (src / "blog-ci.yml.tmpl").write_text(open(PRE_SITE_DIR_TMPL).read())
    dst = tmp_path / "olddst"; dst.mkdir()
    ans = tmp_path / "old.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(tmp_path / "old"), "--dst", str(dst),
                    "--answers", str(ans)], cwd=RENDERER, check=True, capture_output=True, text=True)
    old = (dst / ".github" / "workflows" / "blog-ci.yml").read_text()

    assert new == old, f"a site_dir-less blog's CI changed ({deploy} deploy)"
