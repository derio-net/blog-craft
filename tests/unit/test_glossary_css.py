"""#49 — glossary.css carries the panel placement contract (spec §5a).

A `[popover]` is not positioned for you: the top layer decides stacking, not
coordinates. Left unpositioned the UA default (`inset: 0` plus `margin: auto`)
drops the panel in the viewport's block-start / inline-start corner — which is
exactly the bug #49 reports, and exactly what the *unanchored* path would still
do if the fallback were left to the UA.

These are text assertions over the shipped stylesheet, which is all CI can pin:
whether the rules actually place the box needs a real layout engine, and that is
Test Plan step 3a (matrix row GL-9). What they do buy is that nobody can delete
the anchoring, collapse the per-trigger anchor names, or let the fallback rot
back to the corner without a red test.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS_PATH = os.path.join(
    ROOT, "templates", "features", "glossary", "assets", "css", "glossary.css")


def _css():
    with open(CSS_PATH) as f:
        return f.read()


def _supports_block():
    """The body of the `@supports (anchor-name: ...)` block, brace-matched."""
    css = _css()
    m = re.search(r"@supports\s*\(\s*anchor-name\s*:", css)
    assert m, "anchored rules must be gated behind @supports (anchor-name: --x)"
    open_brace = css.index("{", m.end())
    depth, i = 0, open_brace
    while i < len(css):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[open_brace + 1:i]
        i += 1
    raise AssertionError("unbalanced braces in the @supports block")


def _fallback():
    """Everything outside the @supports block — the unanchored path."""
    css = _css()
    inner = _supports_block()
    start = css.index(inner)
    # walk back to the @supports keyword, forward past its closing brace
    at = css.rindex("@supports", 0, start)
    return css[:at] + css[start + len(inner) + 1:]


# --- the anchored path -------------------------------------------------------

def test_anchored_rules_are_gated_behind_supports():
    # Ungated, `position-area` in a non-supporting browser is simply dropped and
    # the fallback rules would never apply — the gate is what keeps the two
    # paths from blending into the corner default.
    block = _supports_block()
    assert ".abbr-panel" in block


def test_panel_is_anchor_positioned_below_the_term():
    # `position-anchor` itself is emitted inline per panel by the shortcode —
    # a stylesheet cannot name one instance — and is pinned by
    # test_glossary_hugo.py::test_trigger_and_panel_share_an_anchor_name.
    # This rule supplies only the geometry relative to that anchor.
    block = _supports_block()
    m = re.search(r"position-area\s*:\s*([^;]+);", block)
    assert m, "the anchored panel must declare a position-area"
    assert "block-end" in m.group(1), \
        f"the panel opens below the term by preference, got: {m.group(1).strip()}"


def test_panel_flips_rather_than_running_off_the_viewport():
    block = _supports_block()
    m = re.search(r"position-try-fallbacks\s*:\s*([^;]+);", block)
    assert m, "a term in the last line needs somewhere to flip to"
    fallbacks = m.group(1)
    assert "block-start" in fallbacks, "must flip above the term near the viewport foot"
    assert "span-inline-start" in fallbacks, "must flip its inline side near the edge"


def test_anchored_rule_resets_the_ua_popover_inset_and_margin():
    # The UA [popover] sheet sets inset:0 and margin:auto. Inside a position
    # area those stretch the panel across the whole area instead of sizing it
    # to its content, so the anchored rule has to say otherwise explicitly.
    block = _supports_block()
    assert re.search(r"\binset\s*:\s*auto", block), \
        "anchored rule must reset the UA [popover] inset: 0"
    assert re.search(r"\bmargin\s*:", block), \
        "anchored rule must override the UA [popover] margin: auto"


# --- the unanchored fallback -------------------------------------------------

def test_fallback_docks_the_panel_to_the_viewport_foot():
    # Anchor positioning is not universal, so this path is real. It must be
    # usable, not merely different from the corner.
    fb = _fallback()
    m = re.search(r"\.abbr-panel\s*\{([^}]*)\}", fb)
    assert m, "the base .abbr-panel rule must survive outside the @supports block"
    rule = m.group(1)
    assert re.search(r"position\s*:\s*fixed", rule), \
        "the fallback panel must position itself rather than inherit the UA default"
    assert re.search(r"\bbottom\s*:", rule) or re.search(r"\binset\s*:", rule), \
        "the fallback must pin the panel to the viewport block end"
    assert re.search(r"margin-inline\s*:\s*auto", rule), \
        "the fallback panel is inline-centred"


def test_fallback_never_lands_in_the_corner():
    # The literal shape of the bug: the UA's `inset: 0` left in force, or the
    # panel pinned to the block start, which is where it lands over the <h1>.
    # Inline pinning on both sides is fine and is how the dock centres itself —
    # `inset-inline: 0` plus `margin-inline: auto` — so only the block axis and
    # the all-sides shorthand are barred here.
    fb = _fallback()
    m = re.search(r"\.abbr-panel\s*\{([^}]*)\}", fb)
    rule = m.group(1)
    assert not re.search(r"\binset\s*:\s*0\s*;", rule), \
        "inset: 0 with no anchor is the #49 corner placement"
    assert not re.search(r"\btop\s*:\s*0\b", rule), \
        "the panel must not pin to the viewport top — that is where it covers the heading"
    assert re.search(r"\btop\s*:\s*auto\b", rule) or not re.search(r"\btop\s*:", rule), \
        "the fallback must not resolve a block-start offset"


def test_fallback_panel_stays_inside_a_narrow_viewport():
    fb = _fallback()
    m = re.search(r"\.abbr-panel\s*\{([^}]*)\}", fb)
    rule = m.group(1)
    assert "max-width" in rule and ("vw" in rule or "vi" in rule), \
        "a viewport-pinned panel must clamp its width to the viewport, not just to 22rem"
