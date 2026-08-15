"""tools/bootstrap-render.sh must tell "you didn't configure this" apart from
"the renderer is broken".

Every features.* / content_types.* gate asks tools/render-template one question
whose answer has three shapes, not two: the key is present, the key is ABSENT,
or the renderer never ran at all (compile error, no go.mod, no toolchain, `go
run` contention, disk pressure). `go run` reports the last two identically —
exit 1 — so the old `2>/dev/null || echo false` form collapsed them: a broken
renderer silently took the default and bootstrap carried on, producing a PARTIAL
blog with no error text anywhere. That surfaces much later as a missing file (it
cost one spurious release-gate failure during the sticker cycle).

The discriminator is the renderer's OWN sentinel on stderr. So there are two
things to pin, and the first matters more than the second:

  1. the DEFAULTS. This script runs on every bootstrap and every /update, for
     every blog, and absent keys are the common case in the field — a config
     that predates a feature has none of its keys. Nine gates, one of which
     (`features.mermaid_view`) defaults ON while the rest default OFF. A wrong
     default here would be worse than the bug being fixed, so every gate's
     absent-key behaviour is asserted, silently and with rc 0.
  2. a renderer failure is now FATAL and surfaces the renderer's own output,
     instead of defaulting.
"""
import os
import shutil
import subprocess

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
RENDERER_DIR = os.path.join(ROOT, "tools", "render-template")
FIX = os.path.join(ROOT, "tests", "fixtures")

MV_CSS_REL = "assets/css/mermaid-view.css"
MV_HOOK_REL = "layouts/_markup/render-codeblock-mermaid.html"
RT_REL = "assets/js/read-tracker.js"
GC_REL = "layouts/partials/custom/goatcounter.html"
STICKER_SCRIPTS = ("scripts/build-sheets.py", "scripts/generate-stickers.py")

# The line each gate logs when its key is ABSENT. This table IS the default
# contract: `features.mermaid_view` renders (absence means true), the rest skip.
# Matched as WHOLE lines — "[3h] mermaid-view" is a prefix of "[3h] mermaid-view:
# SKIPPED (…)", so a substring check would pass on the default being inverted.
ABSENT_KEY_DEFAULTS = (
    ("features.series_overview_posts", "[3] per-series-overview: per-series-overview/"),
    ("content_types.papers.enabled",
     "[3b] content-type-papers: SKIPPED (content_types.papers.enabled != true)"),
    ("content_types.explainers.enabled",
     "[3b2] content-type-explainers: SKIPPED (content_types.explainers.enabled != true)"),
    ("features.read_tracker", "[3c] read-tracker: SKIPPED (features.read_tracker != true)"),
    ("features.analytics", "[3d] analytics: SKIPPED (no features.analytics)"),
    ("features.glossary.enabled",
     "[3f] glossary: SKIPPED (features.glossary.enabled != true)"),
    ("features.mermaid_csp_init",
     "[3g] mermaid-csp-init: SKIPPED (features.mermaid_csp_init != true)"),
    ("features.mermaid_view", "[3h] mermaid-view"),
    ("features.stickers.enabled", "[3i] stickers: SKIPPED (features.stickers.enabled != true)"),
    ("series_index.layers", "[3e] layer-palette: SKIPPED (no series_index.layers)"),
)


def _cfg(**features):
    """valid-v2 with an EMPTY features map — i.e. every gate key absent."""
    with open(os.path.join(FIX, "valid-v2.blog-craft.yaml")) as fh:
        cfg = yaml.safe_load(fh)
    cfg["features"] = dict(features)
    cfg.pop("content_types", None)
    return cfg


def _run(script, cfg, tmp_path, name):
    ans = tmp_path / f"{name}.yaml"
    ans.write_text(cfg if isinstance(cfg, str) else yaml.safe_dump(cfg))
    target = tmp_path / name
    return subprocess.run(["bash", script, str(ans), str(target)],
                          capture_output=True, text=True), target


# --- 1. absent keys keep their documented defaults, silently -----------------

def test_every_absent_gate_key_takes_its_documented_default_silently(tmp_path):
    r, target = _run(RENDER, _cfg(), tmp_path, "absent")
    assert r.returncode == 0, r.stdout + r.stderr
    # silently: no gate read may report a renderer failure for a merely absent key
    assert "renderer FAILED" not in r.stderr, r.stderr

    lines = r.stdout.splitlines()
    for key, expected_line in ABSENT_KEY_DEFAULTS:
        assert expected_line in lines, (
            f"{key} is absent from the config; the log line documenting its "
            f"default ({expected_line!r}) is missing:\n{r.stdout}")
    assert "[bootstrap] series_overview_posts: 1" in lines, r.stdout

    # and the same contract at the filesystem, where a blog actually feels it
    assert (target / MV_CSS_REL).exists(), "features.mermaid_view defaults ON"
    assert (target / MV_HOOK_REL).exists(), "features.mermaid_view defaults ON"
    assert not (target / RT_REL).exists()
    assert not (target / GC_REL).exists()
    for rel in STICKER_SCRIPTS:
        assert not (target / rel).exists()
    assert not (target / "data/layer_palette.yaml").exists()


def test_a_present_but_non_bool_gate_value_also_takes_the_default(tmp_path):
    """`--get-bool`'s sentinel covers "not a bool" as well as "not found", and a
    hand-edited `read_tracker: yes-please` must keep defaulting, not abort."""
    r, target = _run(RENDER, _cfg(read_tracker="yes-please"), tmp_path, "nonbool")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "renderer FAILED" not in r.stderr, r.stderr
    assert "[3c] read-tracker: SKIPPED" in r.stdout, r.stdout
    assert not (target / RT_REL).exists()


# --- 2. a broken renderer is fatal, with its own output surfaced -------------
#
# The renderer is resolved from the SCRIPT's own location, so a broken renderer
# is simulated by standing up a fake plugin root: a verbatim copy of
# bootstrap-render.sh, the real templates/ (symlinked) and pyproject.toml, and a
# tools/render-template/ that is broken in one specific way. Nothing about the
# real Go source is touched, and the script under test is byte-identical to the
# shipped one — the only difference is the renderer it finds, which is exactly
# the variable the fix is about.


def _fake_root(tmp_path, renderer):
    root = tmp_path / f"fakeroot-{renderer}"
    (root / "tools").mkdir(parents=True)
    shutil.copy2(RENDER, root / "tools" / "bootstrap-render.sh")
    shutil.copy2(os.path.join(ROOT, "pyproject.toml"), root / "pyproject.toml")
    (root / "templates").symlink_to(os.path.join(ROOT, "templates"))
    rdir = root / "tools" / "render-template"
    rdir.mkdir()

    if renderer == "no-go-package":
        pass                      # empty dir: `go: go.mod file not found ...`
    elif renderer == "compile-error":
        for f in ("go.mod", "go.sum", "main.go"):
            shutil.copy2(os.path.join(RENDERER_DIR, f), rdir / f)
        (rdir / "bad.go").write_text(
            "package main\n\nfunc init() { thisSymbolDoesNotExist() }\n")
    elif renderer == "faults-on-has":
        for f in ("go.mod", "go.sum", "main.go"):
            shutil.copy2(os.path.join(RENDERER_DIR, f), rdir / f)
        src = (rdir / "main.go").read_text()
        marker = '\tif *has != "" {\n'
        assert marker in src, "main.go's --has branch moved; update this fault injection"
        src = src.replace(marker, marker + (
            '\t\tfmt.Fprintln(os.Stderr, "SIMULATED TOOLCHAIN FAULT at --has")\n'
            '\t\tos.Exit(9)\n'), 1)
        (rdir / "main.go").write_text(src)
    else:                                            # pragma: no cover
        raise AssertionError(renderer)
    return str(root / "tools" / "bootstrap-render.sh")


@pytest.mark.parametrize("renderer,expect_own_output", [
    # a toolchain-level failure whose stderr STARTS with `go: `, like the
    # `go: downloading …` chatter of a healthy run — so "ignore go's own lines"
    # would have mis-read this one as an absent key
    ("no-go-package", "go.mod file not found"),
    ("compile-error", "thisSymbolDoesNotExist"),
])
def test_a_broken_renderer_aborts_the_gate_read_instead_of_defaulting(
        tmp_path, renderer, expect_own_output):
    script = _fake_root(tmp_path, renderer)
    r, target = _run(script, _cfg(), tmp_path, renderer)

    assert r.returncode != 0, (
        "a renderer that cannot run took the default and carried on:\n"
        + r.stdout + r.stderr)
    assert "renderer FAILED" in r.stderr, r.stderr
    assert "--get-bool features.series_overview_posts" in r.stderr, r.stderr
    assert expect_own_output in r.stderr, (
        "the renderer's own output must be surfaced, not swallowed:\n" + r.stderr)
    # it aborts at the FIRST gate read — before writing anything
    assert "[1] one-pass" not in r.stdout, (
        "the render started anyway; a partial blog is the failure mode being "
        "fixed:\n" + r.stdout)


def test_a_renderer_failure_at_a_has_gate_is_fatal_too(tmp_path):
    """`--has` has no value to default to, and its absent-key answer is also
    exit 1 — so `if _render_has k` would read a crash as "key absent" and
    silently skip the feature. It must abort instead."""
    script = _fake_root(tmp_path, "faults-on-has")
    r, _ = _run(script, _cfg(), tmp_path, "faults-on-has")

    assert r.returncode != 0, (
        "a crash at a --has read was treated as an absent key:\n"
        + r.stdout + r.stderr)
    assert "renderer FAILED" in r.stderr, r.stderr
    assert "--has features.analytics" in r.stderr, r.stderr
    assert "SIMULATED TOOLCHAIN FAULT" in r.stderr, r.stderr
    assert "[3d] analytics: SKIPPED" not in r.stdout, (
        "the feature was skipped as if unconfigured:\n" + r.stdout)


# --- 3. a config the renderer cannot parse is fatal at the first read --------

def test_a_malformed_answers_file_is_fatal_at_the_first_gate_read(tmp_path):
    """A YAML parse error is not a missing key. Before the fix the gate reads
    all defaulted and the failure only surfaced at the first RENDER pass, after
    the log said the bootstrap was under way."""
    r, _ = _run(RENDER, "features:\n  read_tracker: [1, 2\n", tmp_path, "malformed")

    assert r.returncode != 0, r.stdout + r.stderr
    assert "renderer FAILED" in r.stderr, r.stderr
    assert "load answers" in r.stderr, (
        "the renderer's own parse error must be surfaced:\n" + r.stderr)
    assert "[1] one-pass" not in r.stdout, r.stdout
