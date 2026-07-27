"""No shipped template may emit an inline <script>.

`script-src 'self'` (without 'unsafe-inline') is the ordinary hardening posture
for a public blog, and it drops inline blocks SILENTLY — no build failure, no
error the author will notice, just a feature that renders and does nothing. Two
templates shipped that way and were only found when a downstream blog turned a
CSP on (#56).

Behaviour must live in an external asset; per-instance configuration travels as
`data-*` attributes.

Inline `style=` is deliberately NOT covered: `abbr.html` needs a unique
`anchor-name` per trigger and `screenshot.html` takes a per-invocation
`max-width`, neither of which can live in a stylesheet, and `style-src` is
commonly left permissive where `script-src` is not.
"""
import os
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES = os.path.join(ROOT, "templates")
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
SERIES = "tutorials"   # from valid-v2.blog-craft.yaml

# An inline block is a <script> with no src= before the closing angle bracket.
_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.I)
# Go-template and HTML comments — prose there may legitimately mention <script>,
# e.g. a note explaining why the handler was moved out of one.
_COMMENT = re.compile(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}|<!--.*?-->", re.S)


def _blank_comments(text):
    """Replace comment bodies with newlines, preserving line numbers."""
    return _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _template_files():
    """Only templates that EMIT HTML. A .js.tmpl / .css.tmpl is not markup, and
    its own source may discuss <script> without emitting one."""
    for base, _dirs, files in os.walk(TEMPLATES):
        for f in files:
            if f.endswith(".html") or f.endswith(".html.tmpl"):
                yield os.path.join(base, f)


def test_no_template_emits_an_inline_script():
    offenders = []
    for path in _template_files():
        with open(path, encoding="utf-8") as fh:
            body = _blank_comments(fh.read())
        for lineno, line in enumerate(body.splitlines(), 1):
            if _SCRIPT.search(line):
                offenders.append("%s:%d" % (os.path.relpath(path, ROOT), lineno))
    assert not offenders, (
        "inline <script> is dropped by `script-src 'self'` and fails silently; "
        "move the behaviour to an external asset and pass config as data-* "
        "attributes:\n  " + "\n  ".join(offenders))


def _flags(markup):
    return bool(_SCRIPT.search(_blank_comments(markup)))


def test_the_detector_is_not_vacuous():
    """The guard above passes trivially if the regex or the comment-stripping
    stops matching. Pin both directions on synthetic markup."""
    # caught — these are the shapes that shipped broken (#56)
    assert _flags("<script>\nfoo();\n</script>")
    assert _flags('<script type="module">foo();</script>')
    assert _flags("<div></div>\n<script >x</script>")
    # allowed — external assets are the whole point of the fix
    assert not _flags('<script src="/js/app.js" defer></script>')
    assert not _flags('<script data-goatcounter="x/count" src="//gc.js" async></script>')
    # allowed — prose in a comment may name the thing it is explaining
    assert not _flags("{{- /* was an inline <script> until the CSP landed */ -}}")
    assert not _flags("<!-- moved out of a <script> block -->")


@pytest.mark.skipif(not shutil.which("hugo"), reason="Hugo required to build")
def test_built_page_wires_behaviour_without_inline_script(tmp_path):
    """Source-level absence is not the guarantee that matters — the guarantee is
    that a BUILT page still wires up the behaviour, via external assets and
    data-* attributes. Covers both templates that shipped inline (#56)."""
    with open(os.path.join(FIX, "valid-v2.blog-craft.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg.setdefault("features", {})["read_tracker"] = True
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = str(tmp_path / "blog")
    subprocess.run(["bash", RENDER, str(ans), blog], check=True, capture_output=True, text=True)

    d = os.path.join(blog, "content", "docs", SERIES, "01-alpha")
    os.makedirs(d)
    open(os.path.join(d, "index.md"), "w").write(
        "---\ntitle: Alpha\nseries: [%s]\nweight: 2\ndraft: false\nsummary: s\n---\n\n"
        '{{< asciinema src="demo.cast" cols="100" rows="24" >}}\n' % SERIES)
    r = subprocess.run(["hugo"], cwd=blog, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

    import glob
    hits = glob.glob(os.path.join(blog, "public", "**", SERIES, "01-alpha", "index.html"),
                     recursive=True)
    assert hits, "post not built"
    html = open(hits[0]).read()

    # asciinema: config as data-*, player bootstrapped by an external asset
    assert 'data-cast-src="demo.cast"' in html, "shortcode did not emit data-cast-src"
    assert 'data-cols="100"' in html and 'data-rows="24"' in html
    assert re.search(r'<script src="[^"]*asciinema-init[^"]*"[^>]*>', html), \
        "asciinema-init.js not loaded — the player would never start"
    # read-tracker: the clear link is styled by class and handled externally
    assert 'id="clear-read-history"' in html and 'class="clear-read-history"' in html
    assert re.search(r'<script src="[^"]*read-tracker[^"]*"[^>]*>', html), \
        "read-tracker.js not loaded — the clear link would do nothing"
    # and the page carries NO inline script a `script-src 'self'` CSP would drop
    assert not _SCRIPT.search(html), \
        "built page still emits an inline <script>: %s" % _SCRIPT.search(html).group(0)
    # the player library is vendored, so it is served same-origin — an off-origin
    # <script> is blocked by the same CSP as an inline block. Scoped to the player:
    # the Hextra theme loads assets blog-craft does not control, and asserting on
    # those would pin a dependency's behaviour, not this repo's.
    assert re.search(r'<script src="/[^"]*asciinema-player[^"]*"', html), \
        "vendored player library not loaded same-origin"
    offsite = re.findall(r'<(?:script|link)[^>]*(?:src|href)="[^"]*(?:unpkg\.com|cdn\.jsdelivr|asciinema\.org)[^"]*"', html)
    assert not offsite, "player assets still loaded off-origin: %s" % offsite
