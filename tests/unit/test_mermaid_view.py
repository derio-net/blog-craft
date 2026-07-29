"""features.mermaid_view — the shipped stylesheet and the codeblock render hook.

Diagrams used to render at ~31% of their authored size because mermaid's
`useMaxWidth` shrinks the SVG to fit Hextra's 672px content column. The fix is
one CSS rule whose correctness is entirely non-obvious, so these tests pin the
*reasoning*, not the aesthetics:

mermaid writes ``style="max-width: <natural>px"`` INLINE on each rendered SVG.
Inline beats stylesheet and `max-width` beats `width` regardless of origin, so a
sheet rule of ``width: 200rem`` resolves to ``min(200rem, natural)`` — every
diagram renders at exactly its authored size and never larger, with no
per-diagram tuning. Adding a `max-width` to the SVG in this stylesheet would
override the inline value and destroy the whole mechanism; its ABSENCE is
therefore an assertion here, not an oversight.

These are text assertions over shipped files, which is all CI can pin: whether
the frame and the scrollbar actually paint needs a real layout engine, and that
is the post-merge Test Plan (matrix rows MMD-2 / MMD-6).
"""
import os
import re
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEATURE = os.path.join(ROOT, "templates", "features", "mermaid-view")
CSS_PATH = os.path.join(FEATURE, "assets", "css", "mermaid-view.css")
HOOK_PATH = os.path.join(
    FEATURE, "layouts", "_markup", "render-codeblock-mermaid.html")
HEAD_END_PATH = os.path.join(
    ROOT, "templates", "hugo-hextra", "layouts", "partials", "custom", "head-end.html")
BOOTSTRAP = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
MV_CSS_REL = "assets/css/mermaid-view.css"
MV_HOOK_REL = "layouts/_markup/render-codeblock-mermaid.html"


def _css():
    with open(CSS_PATH) as fh:
        return fh.read()


def _strip_comments(css):
    # Comments in this sheet are prose about CSS and contain braces, selectors
    # and property names; parsing them as rules would make every assertion below
    # pass or fail on documentation.
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _rules(css, at=None):
    """[(selector, body, enclosing-at-rule)] — descends into @supports/@media."""
    out, pos = [], 0
    while True:
        brace = css.find("{", pos)
        if brace < 0:
            return out
        sel = " ".join(css[pos:brace].split())
        depth, j = 1, brace + 1
        while j < len(css) and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[brace + 1:j - 1]
        if sel.startswith("@"):
            out.extend(_rules(body, sel))
        else:
            out.append((sel, body, at))
        pos = j


def _parsed():
    return _rules(_strip_comments(_css()))


def _rule(selector, at=None):
    """The (merged) body of every rule whose selector is exactly `selector`."""
    hits = [b for s, b, a in _parsed() if s == selector and a == at]
    assert hits, "no rule for selector %r (at-rule %r)" % (selector, at)
    return "\n".join(hits)


def _decl(body, prop):
    """The value of `prop` in a rule body, or None. Exact property match, so
    `width` never matches `max-width` and `background` never `background-image`."""
    m = re.search(r"(?:^|;)\s*" + re.escape(prop) + r"\s*:\s*([^;]+)", body)
    return m.group(1).strip() if m else None


# --- Task 1: natural-size rendering and the frame ----------------------------

def test_the_stylesheet_ships_in_the_feature_module():
    assert os.path.exists(CSS_PATH), (
        "mermaid-view.css must live in the feature module so /update lands it as "
        "a clean add — custom.css.tmpl is a merge-class file consumers have "
        "already rewritten, and a new .content .mermaid block there conflicts")


def test_the_scroll_container_is_the_mermaid_block():
    # Without overflow-x the full-size SVG would simply overflow the column and
    # be clipped by the page, which is worse than the 31% shrink it replaces.
    assert _decl(_rule(".content .mermaid"), "overflow-x") == "auto"


def test_the_svg_is_sized_by_width_not_max_width():
    # The whole mechanism. `width: 200rem` is not a literal size: it is an upper
    # bound the inline `max-width: <natural>px` always clamps.
    body = _rule(".content .mermaid svg")
    assert _decl(body, "width") == "200rem", (
        "the SVG rule must set `width: 200rem`; got %r" % _decl(body, "width"))


def test_the_svg_rule_never_declares_a_max_width():
    # A stylesheet max-width outranks nothing — it *replaces* the inline value in
    # the cascade only if more specific, but any max-width here (even a large
    # one) risks capping diagrams below their authored size and re-introduces the
    # per-diagram tuning the width rule exists to avoid. Regression guard.
    for sel, body, _at in _parsed():
        if sel.endswith(".mermaid svg") or sel.endswith(".mermaid > svg"):
            assert _decl(body, "max-width") is None, (
                "%s declares max-width — mermaid's inline max-width is the only "
                "one allowed to size the diagram" % sel)


def test_the_svg_is_a_block_box_so_left_overflow_stays_reachable():
    # NOT cosmetic. blog-craft's own custom.css.tmpl:142 ships
    # `.content .mermaid { text-align: center }`, and a centred INLINE child that
    # is wider than its scroll container overflows on BOTH sides — the left
    # overflow is outside the scrollable overflow region and can never be
    # scrolled to. A wide diagram would lose its left edge permanently.
    # `display: block` takes the SVG out of the line box entirely (text-align
    # then cannot reach it) and `margin-inline: auto` centres it when it fits;
    # when it does not, the over-constrained block resolves both auto margins to
    # 0, so all overflow goes right and all of it is scrollable.
    body = _rule(".content .mermaid svg")
    assert _decl(body, "display") == "block", (
        "the SVG must be block-level, or the inherited text-align: center makes "
        "the left edge of a wide diagram unreachable")
    assert (_decl(body, "margin-inline") or _decl(body, "margin") or "") \
        .split()[-1] == "auto", "a diagram narrower than the frame must centre"


def test_the_frame_is_derived_from_currentcolor_so_one_rule_serves_both_themes():
    body = _rule(".content .mermaid")
    border = _decl(body, "border") or ""
    background = _decl(body, "background") or _decl(body, "background-color") or ""
    assert "color-mix(" in border, (
        "border must be color-mix(in srgb, currentColor …) — a hardcoded colour "
        "needs a second .dark rule to stay legible; got %r" % border)
    assert "color-mix(" in background, (
        "background tint must be color-mix-derived for the same reason; got %r"
        % background)
    assert "border-radius" in body, "the frame reads as a frame only with a radius"
    assert _decl(body, "padding"), "the diagram must not touch the frame border"


# --- Task 2: the two scroll affordances, which are mutually exclusive --------

def test_the_scrollbar_opts_out_of_macos_overlay_behaviour():
    # The affordance is not decoration: macOS overlay scrollbars paint NOTHING
    # at rest, so a truncated diagram looks complete and the reader never learns
    # a right-hand third exists. Measured on the prototype:
    # offsetHeight - clientHeight == 0 without this declaration, 9px with it.
    # Sizing the pseudo-element alone does not opt out — only -webkit-appearance.
    body = _rule(".content .mermaid::-webkit-scrollbar")
    assert _decl(body, "-webkit-appearance") == "none", (
        "::-webkit-scrollbar must set -webkit-appearance: none, or the bar is "
        "an invisible overlay and the diagram is silently truncated")
    assert _decl(body, "height"), "a horizontal scrollbar needs a height to occupy"


def test_the_thumb_is_visible_at_rest_and_theme_derived():
    thumb = _rule(".content .mermaid::-webkit-scrollbar-thumb")
    assert "color-mix(" in (_decl(thumb, "background") or ""), (
        "the thumb colour must derive from currentColor so it survives both "
        "themes without a second rule")


def test_the_standard_scrollbar_properties_are_gated_behind_supports():
    # THE TRAP. `scrollbar-width` / `scrollbar-color` are what Firefox needs,
    # but in Chrome/Safari they WIN over the ::-webkit-scrollbar pseudo-elements
    # and disable them — silently restoring the invisible overlay bar with no
    # error anywhere. The feature query is load-bearing, not tidiness.
    gate = "@supports not selector(::-webkit-scrollbar)"
    seen = 0
    for sel, body, at in _parsed():
        for prop in ("scrollbar-width", "scrollbar-color"):
            if _decl(body, prop) is None:
                continue
            seen += 1
            assert at == gate, (
                "%s in rule %r sits under %r — set alongside the WebKit "
                "pseudo-elements it disables them; it must live inside %r"
                % (prop, sel, at, gate))
    assert seen >= 2, (
        "Firefox has no ::-webkit-scrollbar, so the standard properties must "
        "still be present inside the @supports block; found %d" % seen)


def test_scroll_shadows_pin_edges_and_scroll_covers_with_the_content():
    # The second cue, and the self-cancelling one: two cover gradients in the
    # frame colour are attached `local` so they travel with the content and
    # uncover, at each end, an edge shadow attached `scroll` to the scroller.
    # The order of the four layers must match background-image's order exactly —
    # cover, cover, shadow, shadow — or the shadows are covered permanently.
    body = _rule(".content .mermaid")
    attach = _decl(body, "background-attachment")
    assert attach, "no background-attachment: the scroll shadows cannot work"
    assert [p.strip() for p in attach.split(",")] == \
        ["local", "local", "scroll", "scroll"], \
        "expected local, local, scroll, scroll; got %r" % attach
    layers = _decl(body, "background-image") or ""
    assert layers.count("linear-gradient(") == 4, (
        "background-image must declare the same four layers the attachment "
        "list indexes; got %d" % layers.count("linear-gradient("))
    assert "var(--frame-bg)" in layers and "var(--frame-shadow)" in layers, (
        "the covers paint the frame colour and the shadows the shadow colour, "
        "both through custom properties so the theme can invert them")


def test_the_shadow_colours_invert_with_the_theme():
    # A black shadow is invisible against a #111 frame, so the cue would vanish
    # in dark mode exactly like the overlay scrollbar does — same failure, second
    # route. #fff / #111 are Hextra's measured light/dark body backgrounds.
    light = _rule(".content .mermaid")
    assert _decl(light, "--frame-bg"), "the cover gradients need a frame colour"
    assert _decl(light, "--frame-shadow"), "the edge gradients need a shadow colour"
    dark = _rule(".dark .content .mermaid")
    assert _decl(dark, "--frame-bg"), "the dark theme needs its own frame colour"
    assert _decl(dark, "--frame-shadow"), \
        "the dark theme needs its own shadow colour, or the cue disappears"


# --- Task 3: the render hook — keyboard reach without losing the contract ----

def _hook():
    """The hook's emitted markup, with Go template comments stripped.

    The header comment quotes the very markup these tests assert on (`<pre>`,
    `role="img"`, the store set) to explain why each part is load-bearing.
    Searched raw, the prose would satisfy every assertion below while the actual
    output was empty — so the comment has to go before anything is matched.
    """
    with open(HOOK_PATH) as fh:
        return re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", "", fh.read(), flags=re.S)


def test_the_render_hook_ships_in_the_feature_module():
    assert os.path.exists(HOOK_PATH), (
        "the codeblock hook must ship with the stylesheet: the frame is only "
        "half the feature, and an override materialized without it leaves a "
        "scroll container no keyboard can reach")


def test_the_scroll_container_is_keyboard_focusable():
    # WCAG 2.1 §2.1.1: a scrollable region must be operable from the keyboard.
    # Now that the <pre> scrolls, it needs to be in the tab order — a mouse-only
    # scroller is the accessibility regression this feature would otherwise
    # introduce, on a page that previously had nothing to scroll.
    m = re.search(r"<pre\b[^>]*>", _hook())
    assert m, "the hook must still emit the <pre> mermaid mounts into"
    pre = m.group(0)
    assert re.search(r'tabindex\s*=\s*"0"', pre), (
        "the scrolling <pre> must carry tabindex=\"0\"; got %s" % pre)
    assert re.search(r'class="[^"]*\bmermaid\b', pre), \
        "mermaid keys on the .mermaid class — losing it stops every diagram"
    assert "hx:mt-6" in pre, (
        "the theme's own spacing utility must survive the override, or diagrams "
        "reflow differently from every other Hextra site")


def test_the_hook_preserves_the_themes_accessibility_wrapper():
    hook = _hook()
    assert 'role="img"' in hook, \
        "the theme labels the diagram as an image for screen readers"
    assert re.search(r'aria-label="\{\{\s*\(T\s+"mermaidDiagram"\)\s*\|\s*default\s+"Diagram"\s*\}\}"', hook), (
        "the i18n aria-label AND its \"Diagram\" fallback must both survive — "
        "the fallback is what a site with no translation string gets")


def test_the_hook_still_sets_the_hasmermaid_store():
    # The theme's scripts partial reads Page.Store.hasMermaid to decide whether
    # to load mermaid at all. Drop it and diagrams stop rendering SITE-WIDE —
    # the loudest possible way for a cosmetic override to break the feature it
    # was meant to improve, and invisible in this file's diff.
    assert re.search(r'\.Page\.Store\.Set\s+"hasMermaid"\s+true', _hook()), \
        "the override must re-set hasMermaid; the theme's script loader needs it"


def test_the_hook_passes_the_diagram_source_through_unchanged():
    assert re.search(r"\.Inner\s*\|\s*htmlEscape\s*\|\s*safeHTML", _hook()), (
        "the source pipeline is the theme's: htmlEscape then safeHTML. Changing "
        "it either double-escapes the diagram or opens an injection path")


# --- Task 4: wiring — head-end.html load order and the bootstrap [3h] gate ---

def _head_end():
    """head-end.html's markup, with Go template comments stripped.

    The glossary block's header comment already quotes 'css/glossary.css' and
    the mermaid-csp block quotes 'mermaid-init.js' — a raw substring search
    would match those explanations for the WRONG feature, or in the worst case
    pass vacuously on an empty partial whose only content is prose. Same trap
    Task 3's _hook() guards against.
    """
    with open(HEAD_END_PATH) as fh:
        return re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", "", fh.read(), flags=re.S)


def test_head_end_loads_mermaid_view_css_before_custom_css():
    # A blog overrides feature styling in its own custom.css, which only works
    # if the feature sheet loads first — the same rule the glossary.css block
    # at the top of this file already documents.
    html = _head_end()
    mermaid_idx = html.find('resources.Get "css/mermaid-view.css"')
    custom_idx = html.find('resources.Get "css/custom.css"')
    assert mermaid_idx != -1, "head-end.html must retrieve css/mermaid-view.css"
    assert custom_idx != -1, "head-end.html must retrieve css/custom.css"
    assert mermaid_idx < custom_idx, (
        "mermaid-view.css must be requested BEFORE custom.css, or a blog's own "
        "override of .content .mermaid in custom.css cannot win the cascade")


def _mv_cfg(**features):
    with open(os.path.join(FIX, "valid-v2.blog-craft.yaml")) as fh:
        cfg = yaml.safe_load(fh)
    if features:
        cfg.setdefault("features", {}).update(features)
    return cfg


def _mv_bootstrap(cfg, tmp_path, name):
    ans = tmp_path / f"{name}.yaml"
    ans.write_text(yaml.safe_dump(cfg))
    target = tmp_path / name
    r = subprocess.run(["bash", BOOTSTRAP, str(ans), str(target)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def test_bootstrap_materializes_mermaid_view_true_false_and_absent(tmp_path):
    # --get-bool returns false for an ABSENT key (verified against
    # tools/render-template/main.go's digBool), but the config contract says
    # absent means true — a blog that never ran migrations/005_to_006.py must
    # still get the fix, or the feature silently misses every existing blog.
    on = _mv_bootstrap(_mv_cfg(mermaid_view=True), tmp_path, "on")
    assert (on / MV_CSS_REL).exists(), "flag true but the stylesheet was not materialized"
    assert (on / MV_HOOK_REL).exists(), "flag true but the render hook was not materialized"

    off = _mv_bootstrap(_mv_cfg(mermaid_view=False), tmp_path, "off")
    assert not (off / MV_CSS_REL).exists(), "flag explicitly false but the stylesheet materialized anyway"
    assert not (off / MV_HOOK_REL).exists(), "flag explicitly false but the render hook materialized anyway"

    absent = _mv_bootstrap(_mv_cfg(), tmp_path, "absent")   # no features.mermaid_view key at all
    assert (absent / MV_CSS_REL).exists(), (
        "features.mermaid_view is absent from this config — absent means true, "
        "and the stylesheet must still be materialized")
    assert (absent / MV_HOOK_REL).exists(), (
        "features.mermaid_view is absent from this config — absent means true, "
        "and the render hook must still be materialized")
