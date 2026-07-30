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

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "tools", "blog-post-create.sh")
TPL_SCRIPTS = os.path.join(ROOT, "templates", "hugo-hextra", "scripts")

SCENE = "Frank kneels beside an open server chassis, torch in hand."


def _mk_blog(tmp_path, cfg: dict, site_dir: str = ".", prompts_seed: str = "images:\n"):
    """`prompts_seed` seeds the entries file — override it to seed a REAL entry.

    The default `"images:\\n"` is an EMPTY sequence, which is exactly why six
    passing tests coexisted with a file-corrupting append (#65 item 1): an empty
    sequence parses identically at any indentation and establishes no convention
    to detect. Every indent-fidelity assertion passes a real seeded entry.
    """
    blog = tmp_path / "blog-root"
    site = blog / site_dir
    (site / "scripts").mkdir(parents=True)
    for f in ("generate-images.py", "compose.py", "blog_config.py"):
        shutil.copy(os.path.join(TPL_SCRIPTS, f), site / "scripts" / f)
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump(cfg))
    prompts_rel = (cfg.get("image") or {}).get("prompts_file", "prompt_for_images.yaml")
    (blog / prompts_rel).parent.mkdir(parents=True, exist_ok=True)
    (blog / prompts_rel).write_text(prompts_seed)
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

# frank-shaped blogs opt into layer colour-coding, so this config carries the
# `series_index.layers` registry that --layer is validated against (#65 item 2,
# spec D4). DEFAULT_CFG deliberately declares none — the two halves of that rule
# (`layer: TODO` vs no `layer` key at all) need both shapes to be visible.
FRANK_CFG = {
    "version": 4, "project": {"name": "frank"}, "series": [], "voice": "v",
    "site_dir": "blog",
    "series_index": {"layers": [{"code": "obs", "name": "Observability"},
                                {"code": "bld", "name": "Build"}]},
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


# --- the append is indent-faithful and verified (#65 item 1, spec D1/D2) -------
#
# Seeded with a real entry, because that is the shape that broke: the hard-coded
# `  - key:` made the new item a continuation of the previous entry's mapping, so
# `yaml.safe_load` raised ParserError while the scaffolder still exited 0.

SEED_COL0 = """images:
- key: existing-01
  output: static/images/existing.png
  composition:
    scene: |
      an existing scene
"""

SEED_2SPACE = """images:
  - key: existing-01
    output: static/images/existing.png
    composition:
      scene: |
        an existing scene
"""


def _scaffold(tmp_path, seed, number="07", slug="appended"):
    blog = _mk_blog(tmp_path, DEFAULT_CFG, prompts_seed=seed)
    inp = _inputs(tmp_path)
    r = _run(blog, ["--no-generate"],
             ["building", number, slug, "Appended",
              str(inp / "scene.txt"), str(inp / "body.md"), str(inp / "summary.txt")])
    return blog, r


def _assert_appended(blog, r, key):
    """The file still parses, grew by exactly one entry, and kept the old one."""
    assert r.returncode == 0, r.stderr + r.stdout
    text = (blog / "prompt_for_images.yaml").read_text()
    entries = yaml.safe_load(text)["images"]     # ParserError here == the bug
    assert len(entries) == 2, f"expected the seeded entry plus one, got {entries}"
    assert entries[0]["key"] == "existing-01"
    assert entries[0]["composition"]["scene"].strip() == "an existing scene"
    assert entries[1]["key"] == key
    assert entries[1]["composition"]["scene"].strip() == SCENE
    return text


def test_append_onto_column0_sequence(tmp_path):
    # The exact reproduction in #65: `images:` at column 0, which is what
    # bootstrap plus 88 hand-written entries produced in the reporting blog.
    blog, r = _scaffold(tmp_path, SEED_COL0)
    text = _assert_appended(blog, r, "building-07")
    assert text.startswith(SEED_COL0), "every byte above the insertion point stays put (D1)"


def test_append_onto_two_space_sequence(tmp_path):
    blog, r = _scaffold(tmp_path, SEED_2SPACE, number="08", slug="two-space")
    text = _assert_appended(blog, r, "building-08")
    assert text.startswith(SEED_2SPACE), "every byte above the insertion point stays put (D1)"


def test_append_onto_file_with_no_trailing_newline(tmp_path):
    # Without seam normalisation the last seeded line and the first appended one
    # fuse into `...existing scene  - key: building-09`.
    blog, r = _scaffold(tmp_path, SEED_COL0.rstrip("\n"), number="09", slug="no-newline")
    _assert_appended(blog, r, "building-09")


def test_broken_entries_file_fails_loudly_and_is_left_alone(tmp_path):
    # A file that already does not parse is refused before it is touched — the
    # old shell append made it worse and still exited 0.
    broken = SEED_COL0 + "  - key: already-broken\n    output: x.png\n"
    blog, r = _scaffold(tmp_path, broken, number="10", slug="broken")
    assert r.returncode != 0, "a prompts file that does not parse must fail the scaffold"
    assert (blog / "prompt_for_images.yaml").read_text() == broken, "bytes must be untouched"
    assert "building-10" not in (blog / "prompt_for_images.yaml").read_text()


# A refused append must leave NOTHING behind (F3). The page bundle used to be
# written first, so a refusal exited 2 with content/docs/<series>/<NN>-<slug>/
# index.md already on disk and no matching entry — an operator had to know to go
# and delete it. The prompts file is checked for appendability BEFORE anything is
# created, which makes the scaffold all-or-nothing.

def test_a_refused_append_leaves_no_half_scaffolded_post(tmp_path):
    broken = SEED_COL0 + "  - key: already-broken\n    output: x.png\n"
    blog, r = _scaffold(tmp_path, broken, number="11", slug="all-or-nothing")
    assert r.returncode != 0
    assert (blog / "prompt_for_images.yaml").read_text() == broken, "bytes must be untouched"
    bundle = blog / "content" / "docs" / "building" / "11-all-or-nothing"
    assert not bundle.exists(), \
        "a refused append must not leave a page bundle behind — the scaffold is all-or-nothing"


def test_a_trailing_top_level_key_is_refused_up_front_with_an_accurate_message(tmp_path):
    # `images:` must be the LAST top-level key, because the entry is placed at end
    # of file. A hand-edited file with anything after it used to abort every
    # scaffold with `expected <block end>, but found '-'` — blaming the append for
    # the file's layout, after the bundle was already written (F7).
    seed = SEED_COL0 + "settings:\n  quality: high\n"
    blog, r = _scaffold(tmp_path, seed, number="12", slug="trailing-key")
    assert r.returncode != 0
    assert (blog / "prompt_for_images.yaml").read_text() == seed, "bytes must be untouched"
    assert not (blog / "content" / "docs" / "building" / "12-trailing-key").exists()
    assert "settings" in r.stderr, f"stderr must name the offending key: {r.stderr!r}"
    assert "last" in r.stderr, f"stderr must explain the layout rule: {r.stderr!r}"


# An entries file whose content legally continues at COLUMN 0 is ordinary, not a
# trailing top-level key: `images:` last is asked of PyYAML's parse, not of the
# columns. A line scanner refused this file — a `description:` an operator wrapped by
# hand — and so killed every scaffold on such a blog (V1).

SEED_HAND_WRAPPED = ('images:\n'
                     '- key: existing-01\n'
                     '  output: static/images/existing.png\n'
                     '  description: "a long cover description that the\n'
                     'operator wrapped by hand"\n')


def test_a_hand_wrapped_description_does_not_block_the_scaffold(tmp_path):
    assert yaml.safe_load(SEED_HAND_WRAPPED)["images"], "the seed must be VALID to begin with"
    blog, r = _scaffold(tmp_path, SEED_HAND_WRAPPED, number="14", slug="hand-wrapped")
    assert r.returncode == 0, r.stderr + r.stdout
    entries = yaml.safe_load((blog / "prompt_for_images.yaml").read_text())["images"]
    assert len(entries) == 2, "a column-0 continuation line is not a trailing top-level key"
    assert entries[-1]["key"] == "building-14"
    assert (blog / "content" / "docs" / "building" / "14-hand-wrapped").is_dir()


# Every `images:` shape is all-or-nothing (V2). `check` used to model less than the
# real append — not the indent resolution, not the parse verification — so these five
# files passed it and were then refused by `append`, with the page bundle already on
# disk. `check` now runs the whole append in memory, so the two answers are the same
# answer: a flow-style value is refused before anything is created, and a quoted
# `images` key scaffolds at the file's own column instead of being mis-indented.

SHAPES = {
    "flow-empty": "images: []\n",
    "flow-item": "images: [{key: existing-01, output: static/images/existing.png}]\n",
    "flow-spaced": "images: [ ]\n",
    "quoted-key": '"images":\n- key: existing-01\n  output: static/images/existing.png\n',
    "single-quoted-key": "'images':\n- key: existing-01\n  output: static/images/existing.png\n",
}


@pytest.mark.parametrize("name,seed", sorted(SHAPES.items()))
def test_every_images_shape_scaffolds_all_or_nothing(tmp_path, name, seed):
    blog, r = _scaffold(tmp_path, seed, number="15", slug="shape")
    prompts = blog / "prompt_for_images.yaml"
    bundle = blog / "content" / "docs" / "building" / "15-shape"
    if r.returncode == 0:
        assert yaml.safe_load(prompts.read_text())["images"][-1]["key"] == "building-15", \
            f"{name}: a scaffold that reported success must have appended the entry"
        assert bundle.is_dir(), f"{name}: a successful scaffold must leave the bundle"
    else:
        assert prompts.read_text() == seed, \
            f"{name}: a refused scaffold must leave the prompts file byte-identical"
        assert not bundle.exists(), \
            f"{name}: a refused scaffold must leave no page bundle — it is all-or-nothing"


@pytest.mark.parametrize("name", ["flow-empty", "flow-item", "flow-spaced"])
def test_a_flow_style_images_value_is_refused_before_anything_is_created(tmp_path, name):
    blog, r = _scaffold(tmp_path, SHAPES[name], number="16", slug="flow")
    assert r.returncode != 0
    assert "flow" in r.stderr.lower(), f"stderr must name the flow-style value: {r.stderr!r}"
    assert (blog / "prompt_for_images.yaml").read_text() == SHAPES[name]
    assert not (blog / "content" / "docs" / "building" / "16-flow").exists()


def test_the_preflight_is_handed_the_real_entry_block(tmp_path):
    """The pre-flight must model the bytes that will actually be appended (V2).

    `check` falls back to a synthetic entry when it is given none, which exercises
    the indent/concatenate/parse path but not the composed block's own bytes. The
    scaffolder composes the block before it creates anything, so it passes the real
    one. Asserted structurally: every field of the block is bare-or-escaped by
    construction, so nothing reachable through the CLI makes the two answers differ
    today — the ORDER is what would rot silently, and the order is the promise.
    """
    src = open(SCRIPT).read().splitlines()

    def only(pred, what):
        hits = [n for n, line in enumerate(src) if pred(line)]
        assert len(hits) == 1, f"expected exactly one {what} line, found {hits}"
        return hits[0]

    compose = only(lambda ln: ln.startswith('} > "$ENTRY_BLOCK"'), "entry-block composition")
    check = only(lambda ln: '"$PROMPTS_APPEND" check' in ln, "check invocation")
    bundle = only(lambda ln: ln.startswith('mkdir -p "$BUNDLE_DIR"'), "bundle mkdir")
    append = only(lambda ln: '"$PROMPTS_APPEND" append' in ln, "append invocation")
    assert '--entry-file "$ENTRY_BLOCK"' in src[check] and '--key "$KEY"' in src[check], \
        f"the pre-flight must be given the real key and block: {src[check]!r}"
    assert compose < check < bundle < append, \
        "order must be: compose the block, pre-flight it, create the bundle, then append"


@pytest.mark.parametrize("name", ["quoted-key", "single-quoted-key"])
def test_a_quoted_images_key_scaffolds_at_the_files_own_indent(tmp_path, name):
    blog, r = _scaffold(tmp_path, SHAPES[name], number="17", slug="quoted")
    assert r.returncode == 0, r.stderr + r.stdout
    text = (blog / "prompt_for_images.yaml").read_text()
    assert len(yaml.safe_load(text)["images"]) == 2, f"{name} did not round-trip:\n{text}"
    assert "\n- key: building-17" in text, f"{name}: the entry belongs at column 0:\n{text}"


# --- frontmatter fidelity: series always, layer + tags visible (#65 item 2) ----
#
# The frontmatter the reporting blog got was `title/date/draft/tags: []/summary/
# weight` — no `series`, so `{{< series-index >}}` (page-derived from `series`)
# silently never listed the post, while skills/blog-post/SKILL.md Step 8 promises
# it does. Field ORDER is asserted alongside presence: the blog's convention IS an
# order, and a diff against sibling posts is how an author reviews a scaffold.

FRONT_ORDER = ["title", "series", "layer", "date", "draft", "tags",
               "summary", "weight", "reader_goal", "diataxis"]


def _fm_run(tmp_path, cfg, extra=(), tail=(), site_dir=".",
            series="building", number="20", slug="fm-post", title="FM Post"):
    """Scaffold a post and hand back (result, index.md path). No image generation."""
    blog = _mk_blog(tmp_path, cfg, site_dir=site_dir)
    inp = _inputs(tmp_path)
    r = _run(blog, ["--no-generate", *extra],
             [series, number, slug, title, str(inp / "scene.txt"),
              str(inp / "body.md"), str(inp / "summary.txt"), *tail])
    site = blog if site_dir == "." else blog / site_dir
    return r, site / "content" / "docs" / series / f"{number}-{slug}" / "index.md"


def _front_text(idx):
    """The raw frontmatter block, between the --- fences."""
    return idx.read_text().split("---")[1]


def _front_keys(text):
    """Top-level frontmatter keys, in the order they were emitted."""
    return [ln.split(":", 1)[0] for ln in text.splitlines()
            if ln and not ln[0].isspace() and not ln.startswith("#") and ":" in ln]


def _tags_line(text):
    return next(ln for ln in text.splitlines() if ln.startswith("tags:"))


def test_series_always_emitted_default_shaped(tmp_path):
    r, idx = _fm_run(tmp_path, DEFAULT_CFG)
    assert r.returncode == 0, r.stderr + r.stdout
    front = yaml.safe_load(_front_text(idx))
    assert front["series"] == ["building"], "series-index is page-derived from `series` (D3)"


def test_series_always_emitted_frank_shaped(tmp_path):
    r, idx = _fm_run(tmp_path, FRANK_CFG, site_dir="blog")
    assert r.returncode == 0, r.stderr + r.stdout
    front = yaml.safe_load(_front_text(idx))
    assert front["series"] == ["building"]


def test_frontmatter_field_order_minimal(tmp_path):
    # No layer registry, no reader_goal/diataxis: the required spine, in order.
    r, idx = _fm_run(tmp_path, DEFAULT_CFG)
    assert r.returncode == 0, r.stderr + r.stdout
    assert _front_keys(_front_text(idx)) == [
        "title", "series", "date", "draft", "tags", "summary", "weight"]



# --- --layer, validated against the blog's own registry (spec D4) --------------
#
# Not a hard failure when omitted: the helper must stay usable on a blog mid-setup.
# `layer: TODO` over a comment because it matches tools/scaffold-paper.sh:59, it is
# greppable, and it is INERT — series-index.html:79-80 looks the code up in
# data/layer_palette.yaml behind a `with` guard, so an unmatched code renders
# exactly like no layer: a neutral card with no badge.


def test_layer_flag_emitted_when_code_is_registered(tmp_path):
    r, idx = _fm_run(tmp_path, FRANK_CFG, site_dir="blog", extra=["--layer", "obs"])
    assert r.returncode == 0, r.stderr + r.stdout
    text = _front_text(idx)
    assert yaml.safe_load(text)["layer"] == "obs"
    assert "layer: obs" in text, "unquoted and greppable, like scaffold-paper.sh"


def test_unknown_layer_code_is_an_error_naming_the_valid_ones(tmp_path):
    r, idx = _fm_run(tmp_path, FRANK_CFG, site_dir="blog", extra=["--layer", "nope"])
    assert r.returncode != 0, "an unregistered layer code must fail the scaffold"
    assert "obs" in r.stderr and "bld" in r.stderr, f"stderr must list the valid codes: {r.stderr!r}"
    assert not idx.exists(), "the scaffold must fail before it writes the bundle"


def test_layer_omitted_with_registry_is_todo_and_warns(tmp_path):
    r, idx = _fm_run(tmp_path, FRANK_CFG, site_dir="blog")
    assert r.returncode == 0, r.stderr + r.stdout
    text = _front_text(idx)
    assert yaml.safe_load(text)["layer"] == "TODO"
    assert "layer: TODO" in text
    assert "layer" in r.stderr.lower(), f"omitting --layer on a layered blog must warn: {r.stderr!r}"


def test_layer_omitted_without_registry_emits_no_layer_key(tmp_path):
    r, idx = _fm_run(tmp_path, DEFAULT_CFG)
    assert r.returncode == 0, r.stderr + r.stdout
    front = yaml.safe_load(_front_text(idx))
    assert "layer" not in front, "a blog that declares no layers gets no layer key at all"


def test_layer_without_registry_is_accepted_verbatim(tmp_path):
    # Nothing to validate against — a blog may add the registry later.
    r, idx = _fm_run(tmp_path, DEFAULT_CFG, extra=["--layer", "obs"])
    assert r.returncode == 0, r.stderr + r.stdout
    assert yaml.safe_load(_front_text(idx))["layer"] == "obs"


def test_layer_value_is_yaml_safe(tmp_path):
    # "Verbatim" is about not REJECTING an unknown code, not about emitting bytes
    # that break the parser: every interpolated value goes through yaml_escape.
    layer = 'odd: "code" \\ still'
    r, idx = _fm_run(tmp_path, DEFAULT_CFG, extra=["--layer", layer])
    assert r.returncode == 0, r.stderr + r.stdout
    assert yaml.safe_load(_front_text(idx))["layer"] == layer

# --- --tag, repeatable; no tags means an EMPTY list plus a comment (spec D5) ---
#
# Deliberately NOT the sibling scaffolders' `tags: ["TODO"]`: scaffold-paper.sh /
# scaffold-explainer.sh also emit `draft: true`, this one emits `draft: false`, so
# a literal TODO tag would publish a bogus taxonomy term on the next build.


def test_tag_flag_is_repeatable_and_ordered(tmp_path):
    r, idx = _fm_run(tmp_path, DEFAULT_CFG, extra=["--tag", "operations", "--tag", "slo"])
    assert r.returncode == 0, r.stderr + r.stdout
    assert yaml.safe_load(_front_text(idx))["tags"] == ["operations", "slo"]


def test_tag_values_yaml_safe(tmp_path):
    tag = 'quoted "and" back\\slashed'
    r, idx = _fm_run(tmp_path, DEFAULT_CFG, extra=["--tag", tag, "--tag", "plain"])
    assert r.returncode == 0, r.stderr + r.stdout
    assert yaml.safe_load(_front_text(idx))["tags"] == [tag, "plain"]


def test_no_tags_emits_empty_list_with_a_todo_comment(tmp_path):
    r, idx = _fm_run(tmp_path, DEFAULT_CFG)
    assert r.returncode == 0, r.stderr + r.stdout
    text = _front_text(idx)
    line = _tags_line(text)
    assert line.startswith("tags: []"), line
    assert "TODO" in line, f"the empty list must carry a TODO comment: {line!r}"
    assert yaml.safe_load(text)["tags"] == [], "a literal TODO tag would publish a bogus term"


def test_frontmatter_field_order_full(tmp_path):
    # Every optional field present at once — the full convention order.
    rg = tmp_path / "reader-goal.txt"
    rg.write_text("The reader can name the failure mode\n")
    r, idx = _fm_run(tmp_path, FRANK_CFG, site_dir="blog",
                     extra=["--layer", "obs", "--tag", "operations"],
                     tail=[str(rg), "how-to,reference"])
    assert r.returncode == 0, r.stderr + r.stdout
    assert _front_keys(_front_text(idx)) == FRONT_ORDER


# --- the entry key: an explicit override, never a detected convention (#65 item 3)
#
# The reporting blog's 88 entries are keyed `<abbrev>-NN-slug` (`ops-30-silent-
# failure`), which needs an `operating` → `ops` map that exists in no config key —
# `series[]` carries {key, title, description, content_type} and nothing else. So
# detection is rejected (spec D6) and `--key` is the honest answer: the default
# stays byte-compatible, and the value is guarded because it reaches a shortcode
# and a `--only` CLI argument downstream (like --entry-field keys at :51-52).

def _key_run(tmp_path, extra, seed="images:\n", cfg=DEFAULT_CFG, site_dir=".",
             generate=False, series="operating", number="30", slug="silent-failure"):
    blog = _mk_blog(tmp_path, cfg, site_dir=site_dir, prompts_seed=seed)
    inp = _inputs(tmp_path)
    r = _run(blog, ([] if generate else ["--no-generate"]) + list(extra),
             [series, number, slug, "Silent Failure", str(inp / "scene.txt"),
              str(inp / "body.md"), str(inp / "summary.txt")])
    prompts = blog / (cfg.get("image") or {})["prompts_file"]
    return blog, r, prompts


def _last_entry(prompts):
    return yaml.safe_load(prompts.read_text())["images"][-1]


def test_key_override_names_entry_hint_and_cover(tmp_path):
    blog, r, prompts = _key_run(tmp_path, ["--key", "ops-30-silent-failure"],
                                seed=SEED_COL0)
    assert r.returncode == 0, r.stderr + r.stdout
    e = _last_entry(prompts)
    assert e["key"] == "ops-30-silent-failure"
    assert e["output"] == "static/images/ops-30-silent-failure-cover.png", \
        "the default cover filename derives from the RESOLVED key"
    assert "ops-30-silent-failure" in r.stdout, \
        f"the --only/--print-prompt hint must name the resolved key: {r.stdout!r}"
    assert "operating-30" not in r.stdout, \
        f"nothing printed may re-derive <series>-<number>: {r.stdout!r}"


def test_key_defaults_to_series_number(tmp_path):
    # Byte-compatible default: no --key changes nothing about today's output.
    blog, r, prompts = _key_run(tmp_path, [], seed=SEED_COL0)
    assert r.returncode == 0, r.stderr + r.stdout
    e = _last_entry(prompts)
    assert e["key"] == "operating-30"
    assert e["output"] == "static/images/operating-30-cover.png"


def test_bad_key_rejected(tmp_path):
    # The key is a shortcode and a `--only` argument downstream, so it is guarded
    # exactly like an --entry-field key: plain slug or nothing.
    for n, bad in enumerate(("ops 30", 'ops"30', "ops/30", "$(id)", "-ops")):
        case = tmp_path / f"case{n}"
        case.mkdir()
        blog, r, prompts = _key_run(case, ["--key", bad], seed=SEED_COL0)
        assert r.returncode != 0, f"--key {bad!r} must be rejected"
        # returncode alone cannot tell the GUARD from an unparsed flag (any unknown
        # flag also exits 2) — the message has to name the flag it is about (F6).
        assert "--key" in r.stderr, \
            f"--key {bad!r} must be rejected by a message naming the flag: {r.stderr!r}"
        assert prompts.read_text() == SEED_COL0, \
            f"--key {bad!r} must fail before the prompts file is touched"


def test_key_that_yaml_would_retype_is_rejected(tmp_path):
    # These all pass the plain-slug shape and are then emitted BARE, so YAML reads
    # them back as a float / int / bool / null rather than the key the caller asked
    # for. The verification then fails with a message about the prompts file, which
    # blames the file for the flag's value — so the flag is where they are rejected
    # (F4). A key needs at least one letter and must not be YAML 1.1 boolean-ish.
    for n, bad in enumerate(("1.5", "123", "no", "on", "y", "true", "0x1f", "null")):
        case = tmp_path / f"retype{n}"
        case.mkdir()
        blog, r, prompts = _key_run(case, ["--key", bad], seed=SEED_COL0)
        assert r.returncode != 0, f"--key {bad!r} must be rejected"
        assert "--key" in r.stderr, \
            f"--key {bad!r} must be rejected by a message naming the flag: {r.stderr!r}"
        assert prompts.read_text() == SEED_COL0, \
            f"--key {bad!r} must fail before the prompts file is touched"


def test_a_key_with_digits_and_dots_is_still_accepted(tmp_path):
    # The retyping guard must not cost the shapes real blogs use: a version-ish
    # segment is fine as long as the key is not itself a number.
    blog, r, prompts = _key_run(tmp_path, ["--key", "ops-1.5-silent"], seed=SEED_COL0)
    assert r.returncode == 0, r.stderr + r.stdout
    assert _last_entry(prompts)["key"] == "ops-1.5-silent"


# The guard covered the FLAG, not the resolved key (V5). `KEY=${KEY_OVERRIDE:-"$SERIES
# -$NUMBER"}` means the positionals reach the entry unvalidated, so `2026-07 27` yielded
# the key `2026-07-27` — which YAML retypes to a datetime.date — and the failure message
# blamed the prompts file for the caller's arguments, with the bundle already written.
# The guard now runs on the RESOLVED key and names where the bad value came from.

def test_a_derived_key_yaml_would_retype_is_rejected_naming_the_positionals(tmp_path):
    blog, r, prompts = _key_run(tmp_path, [], seed=SEED_COL0, series="2026-07", number="27")
    assert r.returncode != 0, "a derived key YAML retypes must be rejected too"
    assert "ERROR: --key" not in r.stderr, \
        f"this value came from the positionals, so the error must not blame --key: {r.stderr!r}"
    assert "<series>-<number>" in r.stderr, \
        f"stderr must name where the bad key came from: {r.stderr!r}"
    assert "2026-07-27" in r.stderr, f"stderr must show the offending key: {r.stderr!r}"
    assert prompts.read_text() == SEED_COL0, "the prompts file must be untouched"
    assert not (blog / "content" / "docs" / "2026-07" / "27-silent-failure").exists(), \
        "a rejected key must fail before the page bundle is created"


# The guard must not tighten: every one of these survives a YAML round-trip today and
# has to keep working. `0o17` and `1e5` are NOT YAML 1.1 numbers (the int resolver has
# no `0o` form, the float resolver requires a dot and a signed exponent), and
# `no-cache` / `on-call` are not the boolean words themselves.
STILL_ACCEPTED = ["0o17", "1.5e3", "1e5", "no-cache", "on-call", "ops-1.5-silent",
                  "k" + "9" * 299]


@pytest.mark.parametrize("key", STILL_ACCEPTED)
def test_the_resolved_key_guard_accepts_every_key_it_used_to(tmp_path, key):
    blog, r, prompts = _key_run(tmp_path, ["--key", key], seed=SEED_COL0)
    assert r.returncode == 0, f"--key {key!r} was accepted before: {r.stderr}"
    assert _last_entry(prompts)["key"] == key, \
        f"--key {key!r} must survive the round-trip as a string"


# `weight: $WEIGHT` under `set -u` (V6). A non-numeric <number> made the arithmetic at
# :201 leave WEIGHT unset, and the failure landed at the heredoc — `line 278: WEIGHT:
# unbound variable`, exit 1, page bundle already on disk. <number>'s shape is already
# documented (skills/blog-post/SKILL.md Step 3: `^[0-9]{2,3}$`), so it is validated
# before anything is written.

@pytest.mark.parametrize("number", ["f", "7", "1234", "0x1", "-1", "07x"])
def test_a_non_numeric_number_is_refused_before_anything_is_written(tmp_path, number):
    blog, r, prompts = _key_run(tmp_path, [], seed=SEED_COL0, series="building",
                                number=number, slug="weightless")
    assert r.returncode != 0, f"<number> {number!r} must be rejected"
    assert "unbound variable" not in r.stderr, \
        f"<number> {number!r} must be reported, not crash on $WEIGHT: {r.stderr!r}"
    assert "<number>" in r.stderr, \
        f"stderr must name the offending argument: {r.stderr!r}"
    assert prompts.read_text() == SEED_COL0, "the prompts file must be untouched"
    assert not (blog / "content" / "docs" / "building").exists(), \
        "a rejected <number> must fail before the page bundle is created"


# --- the `output:` default follows the entries file's own convention (spec D7) ---
#
# Asymmetric with the key on purpose: here the FILE states the answer, so nothing
# is guessed. The reporting blog keeps covers INSIDE the page bundle
# (blog/content/docs/operating/30-silent-failure/cover.png); the bootstrap default
# keeps them in image.output_dir. Both are legitimate, and a wrong default puts the
# cover somewhere Hugo's page-resources lookup will never find it. Ties, no entries
# and an unparseable file all answer output_dir (tests/unit/test_prompts_append.py),
# so every blog in the field keeps today's behaviour.

def _seed_with_outputs(*outputs: str) -> str:
    """An entries file at column 0 whose entries establish an output convention."""
    lines = ["images:"]
    for n, out in enumerate(outputs, start=1):
        lines += [f"- key: existing-{n:02d}", f"  output: {out}",
                  "  composition:", "    scene: |", f"      scene {n}"]
    return "\n".join(lines) + "\n"


SEED_BUNDLE = _seed_with_outputs("content/docs/operating/28-a/cover.png",
                                 "content/docs/operating/29-b/cover.png")
SEED_BUNDLE_FRANK = _seed_with_outputs("blog/content/docs/operating/28-a/cover.png",
                                       "blog/content/docs/operating/29-b/cover.png")
SEED_STATIC = _seed_with_outputs("static/images/operating-28-cover.png",
                                 "static/images/operating-29-cover.png")


def test_output_default_is_the_bundle_when_the_file_says_so(tmp_path):
    # Generation is NOT skipped: the resolved path must be somewhere the generator
    # can actually write, not just a string in the YAML.
    blog, r, prompts = _key_run(tmp_path, [], seed=SEED_BUNDLE, generate=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert _last_entry(prompts)["output"] == \
        "content/docs/operating/30-silent-failure/cover.png"
    cover = blog / "content" / "docs" / "operating" / "30-silent-failure" / "cover.png"
    assert cover.is_file(), "the cover must LAND in the bundle this run just created"


def test_output_default_is_the_bundle_under_site_dir(tmp_path):
    # frank-shaped: the path the entry carries is config-root-relative, so it keeps
    # the site_dir prefix. (This blog declares layers, hence a `layer: TODO` warning
    # on stderr — not this test's business.)
    blog, r, prompts = _key_run(tmp_path, [], cfg=FRANK_CFG, site_dir="blog",
                                seed=SEED_BUNDLE_FRANK, generate=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert _last_entry(prompts)["output"] == \
        "blog/content/docs/operating/30-silent-failure/cover.png"
    cover = (blog / "blog" / "content" / "docs" / "operating" / "30-silent-failure"
             / "cover.png")
    assert cover.is_file(), "the cover must land inside the bundle under site_dir"


def test_output_default_stays_output_dir_for_a_static_blog(tmp_path):
    blog, r, prompts = _key_run(tmp_path, [], seed=SEED_STATIC, generate=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert _last_entry(prompts)["output"] == "static/images/operating-30-cover.png"
    assert (blog / "static" / "images" / "operating-30-cover.png").is_file()


def test_output_default_stays_output_dir_with_no_entries(tmp_path):
    # The bootstrap shape: nothing to detect, so nothing changes.
    blog, r, prompts = _key_run(tmp_path, [], seed="images:\n")
    assert r.returncode == 0, r.stderr + r.stdout
    assert _last_entry(prompts)["output"] == "static/images/operating-30-cover.png"


def test_output_flag_beats_detection_in_both_shapes(tmp_path):
    for n, seed in enumerate((SEED_BUNDLE, SEED_STATIC)):
        case = tmp_path / f"shape{n}"
        case.mkdir()
        blog, r, prompts = _key_run(case, ["--output", "static/images/chosen.png"],
                                    seed=seed)
        assert r.returncode == 0, r.stderr + r.stdout
        assert _last_entry(prompts)["output"] == "static/images/chosen.png"


def test_bundle_default_and_key_override_compose(tmp_path):
    # The bundle path is per-post, so a --key that no longer matches
    # <series>-<number> must not leak back into it.
    blog, r, prompts = _key_run(tmp_path, ["--key", "ops-30-silent-failure"],
                                seed=SEED_BUNDLE)
    assert r.returncode == 0, r.stderr + r.stdout
    e = _last_entry(prompts)
    assert e["key"] == "ops-30-silent-failure"
    assert e["output"] == "content/docs/operating/30-silent-failure/cover.png"
