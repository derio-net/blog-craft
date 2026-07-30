"""P1 — relative path arguments work everywhere (blog-craft#59).

`/update`'s DOCUMENTED invocation is

    python <blog-craft>/tools/update.py --config .blog-craft.yaml --blog .

and it always failed: `--config` was threaded verbatim into
`bootstrap-render.sh`, which runs the Go renderer inside
`( cd "$RENDERER_DIR" && … )` subshells, so the repo-relative path no longer
existed by the time the renderer opened it. Absolute paths worked, which is why
this stayed latent — every successful run used one.

The audit found FOUR sites with this shape, not one: `reproduce.py`'s own
`--config` and `--scratch` carry the identical break and are not mentioned in
the issue. Each is covered below.
"""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "fixtures")
ANSWERS = os.path.join(FIX, "stoa-v2.expected.yaml")

pytestmark = pytest.mark.skipif(
    shutil.which("go") is None or shutil.which("hugo") is None,
    reason="bootstrap-render.sh needs the Go renderer and hugo",
)


def _blog(tmp_path):
    """A materialized blog whose .blog-craft.yaml sits at its root."""
    blog = tmp_path / "blog"
    subprocess.run(["bash", os.path.join(ROOT, "tools", "bootstrap-render.sh"),
                    ANSWERS, str(blog)], check=True, capture_output=True, text=True)
    shutil.copy(ANSWERS, blog / ".blog-craft.yaml")
    return blog


# --- the shell script, where the cd is ----------------------------------------

def test_bootstrap_render_accepts_relative_answers_and_target(tmp_path):
    shutil.copy(ANSWERS, tmp_path / "answers.yaml")
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "bootstrap-render.sh"),
                        "answers.yaml", "out"],
                       cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out" / "hugo.toml").exists()


def test_bootstrap_render_names_a_missing_answers_file(tmp_path):
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "bootstrap-render.sh"),
                        "nope.yaml", "out"],
                       cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode != 0
    assert "nope.yaml" in r.stderr, "the error must name the path the caller passed"


# --- the documented CLI invocations -------------------------------------------

def test_update_cli_accepts_the_documented_relative_invocation(tmp_path):
    """`--config .blog-craft.yaml --blog .` from the blog root — issue #59."""
    blog = _blog(tmp_path)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "update.py"),
                        "--config", ".blog-craft.yaml", "--blog", "."],
                       cwd=str(blog), capture_output=True, text=True)
    assert r.returncode == 0, f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    assert "dry-run" in r.stdout


def test_a_missing_config_is_named_not_tracebacked(tmp_path):
    """Found by driving #59's own post-merge Test Plan.

    A typo'd `--config` is the likeliest way to get the documented invocation
    wrong, and it arrived as a bare `FileNotFoundError` traceback out of
    `open()` — the same illegibility #59 is about, one step before the renderer
    is even reached. The message must name the RESOLVED path and the directory
    it was resolved from, because "a relative argument is not resolved where you
    assumed" is the whole subject of the issue.
    """
    blog = _blog(tmp_path)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "update.py"),
                        "--config", "nope.yaml", "--blog", "."],
                       cwd=str(blog), capture_output=True, text=True)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr, f"still a stdlib traceback:\n{r.stderr}"
    assert "nope.yaml" in r.stderr
    assert str(blog) in r.stderr, "must say where it resolved the path from"


def test_a_missing_blog_dir_is_named_too(tmp_path):
    blog = _blog(tmp_path)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "update.py"),
                        "--config", ".blog-craft.yaml", "--blog", "no-such-dir"],
                       cwd=str(blog), capture_output=True, text=True)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert "no-such-dir" in r.stderr


def test_reproduce_cli_accepts_relative_config_and_scratch(tmp_path):
    """The third and fourth instances of the same bug — never reported."""
    blog = _blog(tmp_path)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "reproduce.py"),
                        "--config", ".blog-craft.yaml", "--reference", ".",
                        "--scratch", "scratch"],
                       cwd=str(blog), capture_output=True, text=True)
    # Zero drift or listed drift are both fine — what must NOT happen is the
    # renderer failing because it could not open a relative path.
    assert "no such file or directory" not in (r.stdout + r.stderr).lower(), r.stderr
    assert (blog / "scratch" / "hugo.toml").exists()


# --- the library boundary, not just _main -------------------------------------

def test_render_staging_resolves_a_relative_config_from_the_callers_cwd(tmp_path, monkeypatch):
    """A library caller never touches argparse; the fix has to be lower down."""
    import update
    blog = _blog(tmp_path)
    monkeypatch.chdir(blog)
    staging = update.render_staging(".blog-craft.yaml", str(tmp_path / "stg"))
    assert (staging / "hugo.toml").exists()


def test_base_by_rerender_resolves_a_relative_config(tmp_path, monkeypatch):
    import update
    blog = _blog(tmp_path)
    monkeypatch.chdir(blog)
    # v0.10.0 is a real released tag; the point is that the CONFIG path resolves.
    base = update.base_by_rerender(".blog-craft.yaml", "v0.10.0", str(tmp_path / "base"))
    assert (base / "hugo.toml").exists()
