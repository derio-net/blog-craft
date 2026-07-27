"""features.mermaid_csp_init — the external mermaid initialiser for CSP-hardened sites.

`test_templates_csp_safe.py` (#56) guarantees no template blog-craft SHIPS emits
an inline <script>. It cannot see this bug, and its built-page assertion passes
vacuously against it: the fixture post there carries no mermaid diagram, so the
Hextra theme never loads `_partials/scripts/mermaid.html` and its inline init
never reaches the output. Build a page that DOES use mermaid and the same page
carries an inline block blog-craft does not own and cannot remove.

The consequence is quiet. mermaid.js self-starts, so diagrams still appear under
`script-src 'self'` — but always in the light theme, and they stop following the
dark/light toggle. Nothing fails; the page just looks fine and behaves wrong.

Hence a feature, not an unconditional asset: on a site with no CSP the theme's
inline block still runs, so materializing ours too would mean two
mermaid.initialize() calls and two MutationObservers racing the same nodes.
"""
import glob
import os
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
SERIES = "tutorials"          # from valid-v2.blog-craft.yaml
ASSET = "assets/js/mermaid-init.js"

# An inline block is a <script> with no src= before the closing angle bracket.
# Captured with its body so the premise check below can identify WHICH block it
# found — `_INLINE.search(html)` alone would go vacuous the day the theme adds an
# unrelated inline script.
_INLINE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)
# Keys on the theme's mermaid init specifically. `dataset.original` is the same
# substring frank's downstream build check pins on: it is load-bearing to the
# behaviour (the re-render needs the pre-SVG markup), so it survives minification
# and is not cosmetic enough to churn between theme releases.
_THEME_MERMAID_INIT = "dataset.original"


def _cfg(**features):
    with open(os.path.join(FIX, "valid-v2.blog-craft.yaml")) as fh:
        cfg = yaml.safe_load(fh)
    cfg.setdefault("features", {}).update(features)
    return cfg


def _bootstrap(cfg, tmp_path, name):
    ans = tmp_path / f"{name}.yaml"
    ans.write_text(yaml.safe_dump(cfg))
    target = tmp_path / name
    r = subprocess.run(["bash", RENDER, str(ans), str(target)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def _write_mermaid_post(blog):
    d = os.path.join(blog, "content", "docs", SERIES, "01-alpha")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.md"), "w") as fh:
        fh.write(
            "---\ntitle: Alpha\nseries: [%s]\nweight: 2\ndraft: false\nsummary: s\n---\n\n"
            "```mermaid\nflowchart LR\n  A --> B\n```\n" % SERIES)


def _build(blog):
    r = subprocess.run(["hugo"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(os.path.join(blog, "public", "**", SERIES, "01-alpha", "index.html"),
                     recursive=True)
    assert hits, "post not built"
    with open(hits[0]) as fh:
        return fh.read()


def test_materializes_only_when_the_flag_is_set(tmp_path):
    """Opt-in in both directions. Off is the default a CSP-less site relies on:
    two initialisers racing is a real regression, not a harmless duplicate."""
    on = _bootstrap(_cfg(mermaid_csp_init=True), tmp_path, "on")
    assert (on / ASSET).exists(), "flag set but the initialiser was not materialized"

    off = _bootstrap(_cfg(mermaid_csp_init=False), tmp_path, "off")
    assert not (off / ASSET).exists(), "flag false but the initialiser materialized anyway"

    absent = _bootstrap(_cfg(), tmp_path, "absent")
    assert not (absent / ASSET).exists(), "flag absent but the initialiser materialized anyway"


@pytest.mark.skipif(not shutil.which("hugo"), reason="Hugo required to build")
def test_built_mermaid_page_loads_the_external_initialiser(tmp_path):
    """The guarantee that matters is in the OUTPUT: a page using mermaid must
    carry our initialiser as an external, same-origin <script src=...>, which is
    what survives `script-src 'self'`."""
    blog = _bootstrap(_cfg(mermaid_csp_init=True), tmp_path, "on")
    _write_mermaid_post(str(blog))
    html = _build(str(blog))

    assert re.search(r'<script src="/[^"]*mermaid-init[^"]*"[^>]*\bdefer\b', html), \
        ("mermaid-init.js not loaded (external, same-origin, deferred) — diagrams "
         "would freeze in the light theme under a strict script-src")


@pytest.mark.skipif(not shutil.which("hugo"), reason="Hugo required to build")
def test_the_flag_off_leaves_no_initialiser_in_the_output(tmp_path):
    """Pins the other direction at output level, so the test above cannot pass
    by way of something loading mermaid-init unconditionally."""
    blog = _bootstrap(_cfg(mermaid_csp_init=False), tmp_path, "off")
    _write_mermaid_post(str(blog))
    html = _build(str(blog))

    assert "mermaid-init" not in html, \
        "flag off but the built page still references mermaid-init"


@pytest.mark.skipif(not shutil.which("hugo"), reason="Hugo required to build")
def test_the_theme_still_emits_the_inline_init_this_feature_supersedes(tmp_path):
    """The PREMISE check, and deliberately a pin on the pinned theme's markup.

    This feature exists only because the theme ships an inline mermaid init that
    a strict `script-src` drops. If a theme bump ever removes or externalises it,
    this assertion fails — and that failure is the signal to RETIRE the feature,
    because from that point ours would be the second initialiser, not the only
    one. Better a loud failure on a theme bump than a silent double-init.

    Note what is NOT asserted: that the built page carries no inline <script> at
    all. On a mermaid page it does, and blog-craft cannot remove it. The
    guarantee here is that a working external superseder is present alongside it.
    """
    blog = _bootstrap(_cfg(mermaid_csp_init=True), tmp_path, "on")
    _write_mermaid_post(str(blog))
    html = _build(str(blog))

    # Match the class as a TOKEN, not an exact attribute value: Hextra renders a
    # ```mermaid fence as `<pre class="mermaid hx:mt-6">` and appends its own
    # utility classes, so `class="mermaid"` would fail on styling churn alone.
    assert re.search(r'<pre[^>]*\bclass="[^"]*\bmermaid\b', html), \
        "fixture did not render a diagram — the premise check below would be vacuous"
    inline_bodies = [m.group(1) for m in _INLINE.finditer(html)]
    assert any(_THEME_MERMAID_INIT in body for body in inline_bodies), (
        "the Hextra theme no longer emits its inline mermaid init (looked for %r "
        "in %d inline block(s)) — features.mermaid_csp_init is now redundant and "
        "should be RETIRED before it becomes a second, racing initialiser"
        % (_THEME_MERMAID_INIT, len(inline_bodies)))
