"""The blocking mermaid WIDTH gate — tools/validate_mermaid_layout.mjs (MMD-3).

Why a real browser and not jsdom (probed during design, not assumed): mermaid
sizes every node from text metrics, and under jsdom `getBBox` and
`getComputedTextLength` do not exist, `getBoundingClientRect()` returns 0x0,
and `mermaid.render()` throws `CSSStyleSheet is not defined` — any width
"measured" there is fiction. So the tool drives a real headless Chrome over
raw CDP (Node >= 22 ships a global WebSocket; zero npm dependencies) and
renders with the BUILT SITE'S OWN mermaid bundle from public/js/mermaid.*.js,
so measured widths are exactly what readers get.

Tests that need a browser skip with a clear reason when none is discoverable,
so the suite stays runnable on a bare machine. Everything else — discovery
failure, extraction from built HTML, the disabled gate, bundle location — is
hermetic and runs wherever node does.
"""
import glob
import html
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "validate_mermaid_layout.mjs")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(
    NODE is None, reason="node not installed — the layout gate is a node tool")

# The tool's fixed discovery order (spec: "Runner capabilities" table — the
# ubuntu-24.04 image preinstalls Chrome + Chromium but defines NO CHROME_BIN).
CANDIDATES = ["$CHROME_BIN", "google-chrome", "google-chrome-stable",
              "chromium", "chromium-browser"]


def _find_browser():
    """A Chromium-family binary for the measurement tests, passed to the tool
    via CHROME_BIN. Broader than the tool's own candidate list on purpose:
    the tool's list is the spec-pinned CI contract; the tests just need any
    real Chromium on the dev machine (macOS included)."""
    cb = os.environ.get("CHROME_BIN")
    if cb and os.access(cb, os.X_OK):
        return cb
    for name in CANDIDATES[1:]:
        p = shutil.which(name)
        if p:
            return p
    for p in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ):
        if os.access(p, os.X_OK):
            return p
    return None


BROWSER = _find_browser()
needs_browser = pytest.mark.skipif(
    BROWSER is None,
    reason="no Chrome/Chromium/Brave discoverable — set CHROME_BIN to run the "
           "browser-dependent measurement tests")

# A stand-in mermaid bundle honouring the real one's contract: an async
# `mermaid.render(id, src) -> {svg}` whose svg carries the inline
# `style="max-width: <n>px"` mermaid writes. Width is scripted per diagram via
# a `w<NNN>` directive so tests control the outcome. It THROWS if the source
# still contains HTML entities — the extractor must hand render() DECODED
# source (built HTML escapes `-->` to `--&gt;` etc.), or every real diagram
# would fail to parse.
STUB_BUNDLE = """\
window.mermaid = {
  initialize() {},
  async render(id, src) {
    if (/&(lt|gt|amp|quot|#\\d+);/.test(src)) {
      throw new Error("entity-encoded source reached render() - extractor failed to decode");
    }
    if (src.includes("boom")) throw new Error("boom: scripted render failure");
    const m = src.match(/w<(\\d+)>/);
    const w = m ? Number(m[1]) : 100;
    if (src.includes("noinline")) {
      return { svg: `<svg viewBox="0 0 ${w} 80"></svg>` };
    }
    // viewBox deliberately DISAGREES with the inline max-width (half of it):
    // the tool must prefer the inline value — the one mermaid-view.css keys
    // off — so a regression to viewBox-first halves every measured width and
    // the width assertions below catch it.
    return { svg: `<svg viewBox="0 0 ${Math.floor(w / 2)} 80" style="max-width: ${w}px;"></svg>` };
  },
};
"""


def _public(tmp_path, pages, bundle=STUB_BUNDLE, bundle_name="mermaid.min.stub1234.js"):
    """Build a tiny public/ tree. `pages` maps a URL dir (e.g. "/docs/a/") to a
    list of mermaid sources, each emitted in the Hextra render-hook shape."""
    pub = tmp_path / "public"
    for url, sources in pages.items():
        d = pub
        for part in url.strip("/").split("/"):
            if part:
                d = d / part
        d.mkdir(parents=True, exist_ok=True)
        blocks = [
            '<div role="img" aria-label="Diagram">'
            '<pre class="mermaid hx:mt-6" tabindex="0">%s</pre></div>' % html.escape(s)
            for s in sources
        ]
        (d / "index.html").write_text(
            "<!doctype html><html><body><main>%s</main></body></html>" % "\n".join(blocks))
    if bundle is not None:
        (pub / "js").mkdir(parents=True, exist_ok=True)
        (pub / "js" / bundle_name).write_text(bundle)
    return pub


def _run(pub, *args, browser=None, path=None):
    """Run the tool. `browser` sets CHROME_BIN; `path` replaces PATH (an empty
    dir makes the run hermetic — no browser is discoverable)."""
    env = dict(os.environ)
    env.pop("CHROME_BIN", None)
    if browser:
        env["CHROME_BIN"] = browser
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        [NODE, TOOL, "--public", str(pub), *args],
        capture_output=True, text=True, env=env, timeout=180)


def _empty_path(tmp_path):
    d = tmp_path / "empty-path"
    d.mkdir(exist_ok=True)
    return str(d)


# --- Task 1: browser discovery — never hardcode a path -----------------------

def test_no_browser_found_names_every_candidate_in_order(tmp_path):
    """The ubuntu-24.04 runner image ships Google Chrome 150 and Chromium
    preinstalled but defines NO CHROME_BIN (only CHROMEWEBDRIVER /
    EDGEWEBDRIVER / GECKOWEBDRIVER), and `ubuntu-latest` will roll to a newer
    image — so the browser must be DISCOVERED over a candidate list, never a
    hardcoded path. When nothing is found, the failure must name exactly what
    it looked for, in order, so the fix (set CHROME_BIN / install) is obvious
    from the CI log alone."""
    pub = _public(tmp_path, {"/docs/a/": ["graph w<2000>"]})
    r = _run(pub, path=_empty_path(tmp_path))
    assert r.returncode != 0
    out = r.stdout + r.stderr
    pos = [out.find(c) for c in CANDIDATES]
    assert all(p >= 0 for p in pos), \
        f"discovery failure must name every candidate; missing from:\n{out}"
    assert pos == sorted(pos), \
        f"candidates must be named in resolution order; got:\n{out}"


# --- Task 2: extract diagram sources from built HTML --------------------------
#
# Extraction is observed hermetically (no browser) through the disabled-gate
# listing: with --max-width 0 the tool must still WALK and COUNT — a disabled
# gate that reports nothing is frank's original failure mode ("a gate nobody
# runs reports nothing, including how far behind you are", frank 77e68e37).

def test_disabled_gate_walks_built_html_and_lists_every_diagram(tmp_path):
    """--max-width 0 disables measurement but the walker still runs: every
    <pre class="mermaid"> body in public/**/*.html is found and listed by page
    URL + block index (built HTML has no source line numbers). PATH is empty,
    so exit 0 also proves no browser was even looked for."""
    pub = _public(tmp_path, {"/docs/a/": ["graph w<300>", "graph w<400>"]})
    # A SHORTCODE-emitted diagram: not the render-hook markup, wrapped in a
    # figure the way papers/landscape emits its quadrantChart. This is the
    # case a markdown-level check misses — and where frank's breakage was.
    land = pub / "docs" / "landscape"
    land.mkdir(parents=True)
    (land / "index.html").write_text(
        "<html><body><figure class=\"quadrant\"><pre class=\"mermaid\">%s</pre>"
        "</figure></body></html>"
        % html.escape('quadrantChart\n  title "Papers" & more\n  A --> B'))
    # A page with a non-mermaid <pre> must NOT be counted.
    prose = pub / "docs" / "prose"
    prose.mkdir(parents=True)
    (prose / "index.html").write_text(
        "<html><body><pre class=\"chroma\">not a diagram</pre></body></html>")
    # A bare .html page (no index.html) keeps its filename in the URL.
    (pub / "notes.html").write_text(
        "<html><body><pre class=\"mermaid\">graph w&lt;500&gt;</pre></body></html>")

    r = _run(pub, "--max-width", "0", path=_empty_path(tmp_path))
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "GATE DISABLED" in out
    assert "quality.mermaid_max_width: 0" in out
    assert "4 diagram" in out, out
    for ref in ("/docs/a/ #1", "/docs/a/ #2", "/docs/landscape/ #1", "/notes.html #1"):
        assert ref in out, f"missing {ref} in:\n{out}"
    assert "/docs/prose/" not in out, "a non-mermaid <pre> must not be counted"


def test_no_diagrams_is_a_pass_without_bundle_or_browser(tmp_path):
    """A diagram-free blog must pass with no bundle present and no browser
    invoked — the CI step must be free for blogs that never draw."""
    pub = _public(tmp_path, {}, bundle=None)
    (pub / "docs").mkdir(parents=True)
    (pub / "docs" / "index.html").write_text("<html><body>prose only</body></html>")
    r = _run(pub, path=_empty_path(tmp_path))
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "0 diagram" in out


def test_missing_bundle_is_an_error_naming_the_expected_glob(tmp_path):
    """Diagrams exist but public/js has no mermaid bundle: the gate cannot
    measure what readers see, so it must fail loudly (exit 2) and say where it
    looked — never silently pass."""
    pub = _public(tmp_path, {"/docs/a/": ["graph w<2000>"]}, bundle=None)
    r = _run(pub, path=_empty_path(tmp_path))
    out = r.stdout + r.stderr
    assert r.returncode == 2, out
    assert re.search(r"js[/\\]mermaid\.\*\.js", out), \
        f"error must name the expected bundle glob; got:\n{out}"


def test_missing_public_dir_is_an_error_not_a_crash(tmp_path):
    r = _run(tmp_path / "never-built", path=_empty_path(tmp_path))
    out = r.stdout + r.stderr
    assert r.returncode == 2, out
    assert "never-built" in out
    assert "hugo" in out.lower(), "the fix (build the site first) must be named"


# --- Task 3: render, measure, block -------------------------------------------
#
# These run a REAL headless Chromium over CDP. The stub bundle scripts each
# diagram's width, so the whole pipeline is under test — launch, CDP attach,
# bundle load, render, inline-max-width readout, budget compare, exit code —
# with deterministic outcomes. They skip (visibly) only when no browser exists.

def test_budget_zero_invokes_no_browser(tmp_path):
    """quality.mermaid_max_width: 0 must not merely tolerate a missing browser
    — it must never LAUNCH one. CHROME_BIN points at a sentinel script; if the
    tool ever executes it, the sentinel file appears and this fails."""
    sentinel = tmp_path / "browser-was-launched"
    fake = tmp_path / "fake-chrome"
    fake.write_text(f"#!/bin/sh\ntouch {sentinel}\nexit 1\n")
    fake.chmod(0o755)
    pub = _public(tmp_path, {"/docs/a/": ["graph w<99999>"]})
    r = _run(pub, "--max-width", "0", browser=str(fake))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "GATE DISABLED" in r.stdout + r.stderr
    assert not sentinel.exists(), "budget 0 must invoke NO browser"


@needs_browser
def test_under_budget_and_at_budget_pass(tmp_path):
    """A narrow diagram passes; a diagram at exactly the budget passes (the
    gate blocks what EXCEEDS the budget). The wide source also smuggles
    entities ('&', quotes) through the built HTML: the stub bundle throws if
    the extractor failed to decode them, so a pass proves decoding too."""
    pub = _public(tmp_path, {
        "/docs/narrow/": ['graph "n" & w<800>'],
        "/docs/at-budget/": ["graph w<1400>"],
    })
    r = _run(pub, "--max-width", "1400", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "MERMAID LAYOUT OK" in out
    assert "2 diagram" in out


@needs_browser
def test_over_budget_fails_naming_page_index_width_budget_and_overage(tmp_path):
    """The failure report is the fix-it artifact: page URL, block index,
    measured width, the budget, and the overage — enough to find the diagram
    and to argue with the number."""
    pub = _public(tmp_path, {
        "/docs/wide/": ["graph w<2000>"],
        "/docs/narrow/": ["graph w<800>"],
    })
    r = _run(pub, "--max-width", "1400", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "/docs/wide/ #1" in out
    assert "2000px" in out
    assert "1400" in out
    assert "600" in out, f"overage (2000-1400) must be reported; got:\n{out}"
    assert "/docs/narrow/" not in out, "under-budget diagrams are not findings"


@needs_browser
def test_wide_ok_comment_waives_exactly_that_diagram(tmp_path):
    """`%% blog-craft: wide-ok — <reason>` in the mermaid source waives that
    one diagram (%% is a mermaid comment, so it ships invisibly). Another
    over-budget diagram WITHOUT the comment must still block."""
    pub = _public(tmp_path, {
        "/docs/waived/": ["%% blog-craft: wide-ok — legacy quadrant, split tracked\ngraph w<2000>"],
        "/docs/unwaived/": ["graph w<1900>"],
    })
    r = _run(pub, "--max-width", "1400", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "/docs/unwaived/ #1" in out
    assert "1900px" in out
    assert "2000px" not in out, "the waived diagram must not be measured/reported as a finding"


@needs_browser
def test_render_failure_is_an_error_not_a_silent_skip(tmp_path):
    """A diagram that fails to render cannot be measured — treating it as a
    pass would let the gate go blind exactly where the site is broken."""
    pub = _public(tmp_path, {"/docs/broken/": ["graph boom"]})
    r = _run(pub, "--max-width", "1400", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "/docs/broken/ #1" in out
    assert "boom" in out, f"the render error message must surface; got:\n{out}"


@needs_browser
def test_width_falls_back_to_viewbox_when_inline_max_width_absent(tmp_path):
    """Primary readout is the inline style="max-width: <n>px" — the very value
    mermaid-view.css keys off, so gate and renderer cannot disagree. If a
    renderer/config omits it, the viewBox width stands in rather than the
    diagram silently measuring as unknown."""
    pub = _public(tmp_path, {"/docs/vb/": ["graph noinline w<1800>"]})
    r = _run(pub, "--max-width", "1400", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "1800px" in out


@needs_browser
def test_min_bundle_preferred_over_plain_when_both_are_shipped(tmp_path):
    """A production `hugo --minify` build can leave both mermaid.<hash>.js and
    mermaid.min.<hash>.js in public/js (frank does). The min one is what the
    production page loads, so the gate must pick it."""
    wrong = "window.mermaid = { initialize() {}, async render() { throw new Error('WRONG BUNDLE: non-min picked'); } };"
    pub = _public(tmp_path, {"/docs/a/": ["graph w<800>"]},
                  bundle=wrong, bundle_name="mermaid.aaaa1111.js")
    (pub / "js" / "mermaid.min.bbbb2222.js").write_text(STUB_BUNDLE)
    r = _run(pub, "--max-width", "1400", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "WRONG BUNDLE" not in out


def _real_bundle():
    """A real mermaid bundle from a BUILT consumer blog: env override first,
    then sibling checkouts (../<blog>/public/js or ../<blog>/<site>/public/js
    — the same sibling-root convention the acceptance report uses)."""
    env = os.environ.get("BLOG_CRAFT_MERMAID_BUNDLE")
    if env and os.path.isfile(env):
        return env
    hits = sorted(
        glob.glob(os.path.join(ROOT, "..", "*", "public", "js", "mermaid.min.*.js"))
        + glob.glob(os.path.join(ROOT, "..", "*", "*", "public", "js", "mermaid.min.*.js")))
    return hits[0] if hits else None


REAL_BUNDLE = _real_bundle()


@needs_browser
@pytest.mark.skipif(REAL_BUNDLE is None, reason=(
    "no real mermaid bundle found — set BLOG_CRAFT_MERMAID_BUNDLE to a built "
    "site's public/js/mermaid.min.*.js, or keep a built consumer blog as a sibling checkout"))
def test_real_mermaid_bundle_yields_real_plausible_widths(tmp_path):
    """The stub tests pin the PIPELINE; this pins the CONTRACT: real mermaid
    emits an inline max-width on its rendered svg, an LR chart measures wider
    than a two-node TD chart, and the numbers are plausible pixels — not the
    jsdom-style zeros this tool exists to avoid."""
    pub = _public(tmp_path, {"/docs/real/": [
        'flowchart LR\n  A["a long node label"] --> B["another long label"] --> C["third"] --> D["fourth"]',
        "flowchart TD\n  A --> B",
    ]}, bundle=None)
    (pub / "js").mkdir(parents=True, exist_ok=True)
    shutil.copy(REAL_BUNDLE, pub / "js" / "mermaid.min.real0000.js")
    r = _run(pub, "--max-width", "50", browser=BROWSER)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    got = {int(i): int(w) for i, w in
           re.findall(r"/docs/real/ #(\d+): (\d+)px > 50px", out)}
    assert set(got) == {1, 2}, f"both diagrams must measure over a 50px budget; got:\n{out}"
    assert got[1] > got[2], "the 4-node LR chart must measure wider than the 2-node TD chart"
    for w in got.values():
        assert 50 < w < 6000, f"implausible measured width {w}px"
