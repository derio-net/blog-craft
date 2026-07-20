"""tools/blog-post-create.sh reads the config it requires (#39 items 1, 2, 4).

Two blog shapes drive the scaffolder end-to-end in BLOG_CRAFT_TEST_MODE:
  (a) default-shaped (site_dir absent, stock paths) — today's behaviour minus
      the forced static/images/reference.png (the generator's own reference
      precedence decides; no reference present must NOT abort the scaffold);
  (b) frank-shaped (site_dir: blog, prompts_file under blog/, custom
      output_dir) — bundle lands under blog/content/docs, the entry lands in
      blog/prompt_for_images.yaml carrying `series:` + every --entry-field,
      and the entry `prompt:` is the SCENE ONLY (the engine composes layers
      around it — writing a pre-composed prompt would double-compose, #39
      item 2).
"""
import os
import shutil
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "tools", "blog-post-create.sh")
TPL_SCRIPTS = os.path.join(ROOT, "templates", "hugo-hextra", "scripts")

SCENE = "Frank kneels beside an open server chassis, torch in hand."


def _mk_blog(tmp_path, cfg: dict, site_dir: str = "."):
    blog = tmp_path / "blog-root"
    site = blog / site_dir
    (site / "scripts").mkdir(parents=True)
    for f in ("generate-images.py", "compose.py", "blog_config.py"):
        shutil.copy(os.path.join(TPL_SCRIPTS, f), site / "scripts" / f)
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    prompts_rel = (cfg.get("image") or {}).get("prompts_file", "prompt_for_images.yaml")
    (blog / prompts_rel).parent.mkdir(parents=True, exist_ok=True)
    (blog / prompts_rel).write_text("images:\n")
    return blog


def _inputs(tmp_path):
    p = tmp_path / "in"
    p.mkdir()
    (p / "scene.txt").write_text(SCENE + "\n")
    (p / "body.md").write_text("## Body\n\ntext\n")
    (p / "summary.txt").write_text("A one-line summary\n")
    return p


def _run(blog, extra, args, cwd=None):
    # the script shells out to `python3`; make it resolve to THIS python (yaml+PIL)
    env = dict(os.environ, BLOG_CRAFT_TEST_MODE="1",
               PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"])
    return subprocess.run(
        ["bash", SCRIPT, *extra, str(blog), *args],
        capture_output=True, text=True, env=env, cwd=cwd or str(blog),
    )


DEFAULT_CFG = {
    "version": 4, "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {"prompts_file": "prompt_for_images.yaml", "output_dir": "static/images",
              "composition_order": ["base_style", "scene"],
              "layers": {"base_style": "STYLE"}},
}

FRANK_CFG = {
    "version": 4, "project": {"name": "frank"}, "series": [], "voice": "v",
    "site_dir": "blog",
    "image": {"prompts_file": "blog/prompt_for_images.yaml",
              "output_dir": "blog/static/images",
              "reference_pool": ".reference-pool",
              "composition_order": ["base_character", "torso", "mood", "scene"],
              "layers": {"base_character": "CHAR",
                         "torso": {"_select": [["torso", "series"], "torso_variant"],
                                   "building": ["t0", "t1"]},
                         "mood": {"cautious": "MOOD-C"}}},
}


def test_default_blog_scaffolds_without_reference(tmp_path):
    blog = _mk_blog(tmp_path, DEFAULT_CFG)
    inp = _inputs(tmp_path)
    r = _run(blog, [], ["building", "01", "first-post", "First Post",
                       str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
    assert r.returncode == 0, r.stderr + r.stdout
    idx = blog / "content" / "docs" / "building" / "01-first-post" / "index.md"
    assert idx.is_file(), "bundle must land in <root>/content/docs for a default blog"
    assert "title: \"First Post\"" in idx.read_text()
    entries = yaml.safe_load((blog / "prompt_for_images.yaml").read_text())["images"]
    assert entries[0]["key"] == "building-01"
    assert entries[0]["composition"]["modifiers"]["series"] == "building"
    cover = blog / "static" / "images" / "building-01-cover.png"
    assert cover.is_file(), "cover generated even with no reference image anywhere"


def test_frank_shaped_blog_scene_only_entry(tmp_path):
    blog = _mk_blog(tmp_path, FRANK_CFG, site_dir="blog")
    inp = _inputs(tmp_path)
    r = _run(blog, ["--entry-field", "mood=cautious", "--entry-field", "torso_variant=1",
                    "--output", "blog/static/images/building-02-cover.png"],
             ["building", "02", "second-post", "Second Post",
              str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
    assert r.returncode == 0, r.stderr + r.stdout
    idx = blog / "blog" / "content" / "docs" / "building" / "02-second-post" / "index.md"
    assert idx.is_file(), "bundle must land under site_dir"
    entries = yaml.safe_load((blog / "blog" / "prompt_for_images.yaml").read_text())["images"]
    e = entries[0]
    assert e["key"] == "building-02"
    assert e["output"] == "blog/static/images/building-02-cover.png"
    mods = e["composition"]["modifiers"]
    assert mods["series"] == "building"
    assert mods["mood"] == "cautious"
    assert mods["torso_variant"] == 1
    # scene-only: the entry scene is exactly the brief, no composed layers
    assert e["composition"]["scene"].strip() == SCENE
    assert "CHAR" not in e["composition"]["scene"]
    cover = blog / "blog" / "static" / "images" / "building-02-cover.png"
    assert cover.is_file()


def test_entry_field_numbers_stay_numbers(tmp_path):
    blog = _mk_blog(tmp_path, FRANK_CFG, site_dir="blog")
    inp = _inputs(tmp_path)
    r = _run(blog, ["--entry-field", "torso_variant=0"],
             ["building", "03", "third", "Third",
              str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
    assert r.returncode == 0, r.stderr + r.stdout
    entries = yaml.safe_load((blog / "blog" / "prompt_for_images.yaml").read_text())["images"]
    assert entries[0]["composition"]["modifiers"]["torso_variant"] == 0, "int selector must not become a string"


def test_title_and_field_values_yaml_safe(tmp_path):
    blog = _mk_blog(tmp_path, DEFAULT_CFG)
    inp = _inputs(tmp_path)
    title = 'Why "torso" died \\ hard'
    r = _run(blog, ["--entry-field", 'mood=quoted "and" back\\slashed',
                    "--entry-field", "note=a=b=c"],
             ["building", "04", "yaml-safe", title,
              str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
    assert r.returncode == 0, r.stderr + r.stdout
    idx = blog / "content" / "docs" / "building" / "04-yaml-safe" / "index.md"
    front = idx.read_text().split("---")[1]
    assert yaml.safe_load(front)["title"] == title
    entries = yaml.safe_load((blog / "prompt_for_images.yaml").read_text())["images"]
    mods = entries[0]["composition"]["modifiers"]
    assert mods["mood"] == 'quoted "and" back\\slashed'
    assert mods["note"] == "a=b=c", "value may contain = (split on first only)"


def test_bad_entry_field_key_rejected(tmp_path):
    blog = _mk_blog(tmp_path, DEFAULT_CFG)
    inp = _inputs(tmp_path)
    for bad in ("mo od=x", "output=/etc/evil.png", "prompt=injected"):
        r = _run(blog, ["--entry-field", bad],
                 ["building", "05", "badkey", "Bad",
                  str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
        assert r.returncode != 0, f"key {bad!r} must be rejected"


def test_no_generate_skips_image_generation(tmp_path):
    blog = _mk_blog(tmp_path, DEFAULT_CFG)
    inp = _inputs(tmp_path)
    r = _run(blog, ["--no-generate"],
             ["building", "06", "preview", "Preview",
              str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
    assert r.returncode == 0, r.stderr + r.stdout
    entries = yaml.safe_load((blog / "prompt_for_images.yaml").read_text())["images"]
    assert entries[0]["key"] == "building-06"       # entry appended
    assert not (blog / "static" / "images" / "building-06-cover.png").exists()
