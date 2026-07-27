"""P2 — the 3-way base must be rendered from the config as of the LAST SYNC.

The regression behind blog-craft#60. `update.py` re-rendered the templates at
the recorded `blog_craft_version` but fed them the config the operator had just
edited, so a newly-enabled feature's contribution was already present in the
base. `diff3` saw base=has-it, local=lacks-it, incoming=has-it and read local as
a deliberate deletion — keeping the deletion and dropping the feature, under a
printed `MERGE` and an `update applied`.

The first two tests pin the mechanism with synthetic trees over a real
`merged`-class path, no git tags and no Hugo. The rest pin the base-config
selection: snapshot wins, absent falls back with a warning, and a snapshot that
will not render degrades to the live config instead of killing the run.
"""
import pytest

import sync_state
from update import base_config, default_manifest, plan_update, render_base

M = default_manifest()

CI_PATH = ".github/workflows/blog-ci.yml"          # 'merged' per templates/manifest.yaml
GLOSSARY_STEP = "      - name: Validate glossary\n"

_CI_HEAD = "jobs:\n  build:\n    steps:\n      - name: Build\n        run: hugo\n"
_CI_TAIL = "      - name: Link check\n        run: lychee .\n"


def _ci(with_glossary: bool) -> str:
    return _CI_HEAD + (GLOSSARY_STEP if with_glossary else "") + _CI_TAIL


def _tree(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def _plan_with_base(tmp_path, base_has_glossary):
    """The blog was synced with the feature OFF; the operator has just turned it ON.

    `base_has_glossary` is the whole story: False renders the base from the
    pre-toggle config (honest), True renders it from the post-toggle config
    (what update.py used to do).
    """
    base = _tree(tmp_path / "base", {CI_PATH: _ci(base_has_glossary)})
    blog = _tree(tmp_path / "blog", {CI_PATH: _ci(False)})       # on disk, synced pre-toggle
    stg = _tree(tmp_path / "stg", {CI_PATH: _ci(True)})          # rendered with the new config
    return {e["path"]: e for e in plan_update(blog, stg, base, M)}[CI_PATH]


def test_honest_base_lands_the_newly_enabled_feature(tmp_path):
    e = _plan_with_base(tmp_path, base_has_glossary=False)
    assert e["action"] == "merge"
    assert GLOSSARY_STEP in e["merged"].decode()
    assert "<<<<<<<" not in e["merged"].decode()


def test_base_rendered_with_the_post_toggle_config_drops_it(tmp_path):
    # The defect, pinned: a base built from the CURRENT config makes the feature
    # look like something the operator deliberately deleted.
    e = _plan_with_base(tmp_path, base_has_glossary=True)
    assert GLOSSARY_STEP not in e["merged"].decode()
    # ...and it is no longer allowed to masquerade as a MERGE that did something
    assert e["action"] == "noop"


# --- which config the base is rendered from -----------------------------------

def _config(tmp_path, name="live.yaml", text="features: {glossary: {enabled: true}}\n"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_base_config_prefers_the_snapshot(tmp_path):
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    sync_state.write_snapshot(_config(tmp_path, "old.yaml", "features: {}\n"), blog)

    chosen, warning = base_config(live, blog)
    assert chosen == sync_state.snapshot_path(blog)
    assert warning is None


def test_base_config_falls_back_to_the_live_config_with_a_warning(tmp_path):
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()

    chosen, warning = base_config(live, blog)
    assert chosen == live
    assert warning and "#60" in warning
    # the warning has to say what is actually at risk, not just "no snapshot"
    assert "merged" in warning and "current" in warning.lower()


def test_base_config_ignores_an_unusable_snapshot(tmp_path):
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    sync_state.snapshot_path(blog).write_text("# header only, no config\n")

    chosen, warning = base_config(live, blog)
    assert chosen == live and warning


def test_render_base_uses_the_snapshot_and_stays_quiet(tmp_path):
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    snap = sync_state.write_snapshot(_config(tmp_path, "old.yaml", "features: {}\n"), blog)
    seen, warned = [], []

    out = render_base(live, blog, "v0.13.0", str(tmp_path / "b"),
                      render=lambda c, v, d: seen.append((c, v)) or d,
                      warn=warned.append)
    assert seen == [(str(snap), "v0.13.0")]
    assert warned == []
    assert out == str(tmp_path / "b")


def test_render_base_warns_when_there_is_no_snapshot(tmp_path):
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    seen, warned = [], []

    render_base(live, blog, "v0.13.0", str(tmp_path / "b"),
                render=lambda c, v, d: seen.append((c, v)) or d, warn=warned.append)
    assert seen == [(str(live), "v0.13.0")]
    assert len(warned) == 1 and "#60" in warned[0]


def test_render_base_retries_with_the_live_config_when_the_snapshot_will_not_render(tmp_path):
    # e.g. a snapshot whose schema the recorded release predates. Degraded beats
    # dead: the run continues on the old (approximate) base, loudly.
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    snap = sync_state.write_snapshot(_config(tmp_path, "old.yaml", "features: {}\n"), blog)
    seen, warned = [], []

    def render(cfg, ver, dest):
        seen.append(cfg)
        if cfg == str(snap):
            raise RuntimeError("template error at v0.13.0")
        return dest

    out = render_base(live, blog, "v0.13.0", str(tmp_path / "b"), render=render, warn=warned.append)
    assert seen == [str(snap), str(live)]
    assert out == str(tmp_path / "b")
    assert any("template error" in w for w in warned)


def test_render_base_propagates_when_the_live_config_will_not_render_either(tmp_path):
    live = _config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()

    def render(cfg, ver, dest):
        raise RuntimeError("tag v0.13.0 is not reachable")

    with pytest.raises(RuntimeError, match="not reachable"):
        render_base(live, blog, "v0.13.0", str(tmp_path / "b"), render=render, warn=lambda _: None)
