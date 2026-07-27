"""P5 — Hugo smoke: the glossary shortcodes render real, clickable markup.

These are the only tests that prove GL-2 and GL-7 — that a marked abbreviation
actually becomes a button + popover pair in the built HTML, and that the index
renders. Whether the panel is *dismissible* is GL-3 and needs a browser; that
lives in the manual phase.

--buildFuture throughout: a bare `date:` is midnight site-time, so a
locally-stamped post is future-dated for part of every day (see the phase-5
journal entry).
"""
import os
import re
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
ANSWERS = os.path.join(FIX, "answers-glossary-v5.yaml")

REGISTRY = {
    "SLO": {"name": "Service Level Objective",
            "description": "The numeric reliability target a service commits to."},
    "NUT": {"name": "Network UPS Tools",
            "description": "Daemon suite that monitors a UPS.",
            "url": "https://networkupstools.org"},
    # Two expansions of the same letters (#65 item 4): the registry is keyed by
    # the abbreviation, so the second sense needs a suffixed key — and
    # rendered_text is what keeps that key out of the reader's face.
    "GC": {"name": "Garbage Collection",
           "description": "Reclaiming memory no longer reachable."},
    "GC_GOATCOUNTER": {"rendered_text": "GC",
                       "name": "GoatCounter",
                       "description": "The analytics tool behind the numbers."},
}

_DT_RE = re.compile(r'<dt class="glossary-term"><abbr title="([^"]*)">([^<]*)</abbr>')

POST = """---
title: "Glossary smoke"
date: {date}
draft: false
weight: 2
series: [building]
---

{body}
"""


def _blog(tmp_path, body, registry=REGISTRY, answers=ANSWERS, name="blog"):
    blog = str(tmp_path / name)
    r = subprocess.run(["bash", RENDER, answers, blog],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    if registry is not None:
        os.makedirs(os.path.join(blog, "data"), exist_ok=True)
        with open(os.path.join(blog, "data", "glossary.yaml"), "w") as f:
            yaml.safe_dump(registry, f)
    post_dir = os.path.join(blog, "content", "docs", "building", "01-smoke")
    os.makedirs(post_dir, exist_ok=True)
    with open(os.path.join(post_dir, "index.md"), "w") as f:
        f.write(POST.format(date="2020-01-01", body=body))
    return blog


def _build(blog, expect_ok=True):
    r = subprocess.run(["hugo", "--buildDrafts", "--buildFuture"],
                       cwd=blog, capture_output=True, text=True)
    if expect_ok:
        assert r.returncode == 0, r.stdout + r.stderr
    return r


def _html(blog, *parts):
    with open(os.path.join(blog, "public", *parts, "index.html")) as f:
        return f.read()


def _post_html(blog):
    return _html(blog, "docs", "building", "01-smoke")


# --- the {{< abbr >}} shortcode ---------------------------------------------

def test_abbr_renders_button_and_popover_pair(tmp_path):
    blog = _blog(tmp_path, 'We wired {{< abbr "NUT" >}} into the rack.')
    _build(blog)
    html = _post_html(blog)
    assert 'popovertarget="abbr-nut-0"' in html
    assert 'id="abbr-nut-0"' in html
    assert "popover" in html
    assert "<button" in html


def test_panel_carries_name_and_description(tmp_path):
    blog = _blog(tmp_path, 'We wired {{< abbr "NUT" >}} into the rack.')
    _build(blog)
    html = _post_html(blog)
    assert "Network UPS Tools" in html
    assert "Daemon suite that monitors a UPS." in html


def test_entry_with_url_renders_a_link(tmp_path):
    blog = _blog(tmp_path, 'We wired {{< abbr "NUT" >}} in.')
    _build(blog)
    assert 'href="https://networkupstools.org"' in _post_html(blog)


def test_entry_without_url_renders_no_link(tmp_path):
    blog = _blog(tmp_path, 'Our {{< abbr "SLO" >}} slipped.')
    _build(blog)
    html = _post_html(blog)
    assert "abbr-panel" in html
    assert "abbr-link" not in html


def test_same_term_twice_gets_distinct_ids(tmp_path):
    blog = _blog(tmp_path,
                 'First {{< abbr "NUT" >}} then {{< abbr "NUT" >}} again.')
    _build(blog)
    html = _post_html(blog)
    assert 'id="abbr-nut-0"' in html
    assert 'id="abbr-nut-1"' in html


def test_trigger_and_panel_share_an_anchor_name(tmp_path):
    # #49: the panel must be anchored to its trigger, or the browser falls back
    # to the UA default and drops it in the viewport corner.
    blog = _blog(tmp_path, 'We wired {{< abbr "NUT" >}} into the rack.')
    _build(blog)
    html = _post_html(blog)
    assert 'style="anchor-name: --abbr-nut-0"' in html
    assert 'style="position-anchor: --abbr-nut-0"' in html


def test_each_occurrence_gets_its_own_anchor_name(tmp_path):
    # A single shared --abbr would anchor every panel on the page to whichever
    # trigger resolved first, so the second term's panel opens under the first.
    blog = _blog(tmp_path,
                 'First {{< abbr "NUT" >}} then {{< abbr "SLO" >}} after.')
    _build(blog)
    html = _post_html(blog)
    assert 'style="anchor-name: --abbr-nut-0"' in html
    assert 'style="position-anchor: --abbr-nut-0"' in html
    assert 'style="anchor-name: --abbr-slo-1"' in html
    assert 'style="position-anchor: --abbr-slo-1"' in html


def test_anchor_name_tracks_the_id_for_a_repeated_term(tmp_path):
    blog = _blog(tmp_path,
                 'First {{< abbr "NUT" >}} then {{< abbr "NUT" >}} again.')
    _build(blog)
    html = _post_html(blog)
    for ordinal in (0, 1):
        assert f'id="abbr-nut-{ordinal}"' in html
        assert f'style="anchor-name: --abbr-nut-{ordinal}"' in html
        assert f'style="position-anchor: --abbr-nut-{ordinal}"' in html


def test_display_override_changes_display_not_lookup(tmp_path):
    blog = _blog(tmp_path, 'Our {{< abbr "SLO" "SLOs" >}} slipped.')
    _build(blog)
    html = _post_html(blog)
    assert ">SLOs<" in html
    assert "Service Level Objective" in html


def test_rendered_text_is_shown_instead_of_the_key(tmp_path):
    blog = _blog(tmp_path, 'Our {{< abbr "GC_GOATCOUNTER" >}} numbers rose.')
    _build(blog)
    html = _post_html(blog)
    assert ">GC<" in html
    assert '<abbr title="GoatCounter"' in html
    assert ">GC_GOATCOUNTER<" not in html          # never visible text


def test_rendered_text_is_used_in_the_aria_label(tmp_path):
    # abbr.html interpolated $key here, so the disambiguating suffix leaked to
    # screen readers as well as to the index.
    blog = _blog(tmp_path, 'Our {{< abbr "GC_GOATCOUNTER" >}} numbers rose.')
    _build(blog)
    html = _post_html(blog)
    assert 'aria-label="Expand abbreviation: GC"' in html
    assert "GC_GOATCOUNTER" not in html      # the id is anchorized, so lowercase


def test_call_site_argument_still_beats_rendered_text(tmp_path):
    blog = _blog(tmp_path, 'Two {{< abbr "GC_GOATCOUNTER" "GCs" >}} later.')
    _build(blog)
    html = _post_html(blog)
    assert ">GCs<" in html
    assert '<abbr title="GoatCounter"' in html


def test_rendered_text_does_not_move_the_id_or_the_anchor(tmp_path):
    # #49: $id and the anchor name stay derived from the KEY. Deriving them from
    # a shared display text would collide both senses of GC onto one anchor.
    blog = _blog(tmp_path,
                 'Both {{< abbr "GC" >}} and {{< abbr "GC_GOATCOUNTER" >}}.')
    _build(blog)
    html = _post_html(blog)
    assert 'id="abbr-gc-0"' in html
    assert 'style="anchor-name: --abbr-gc-0"' in html
    assert 'style="position-anchor: --abbr-gc-0"' in html
    assert 'id="abbr-gc_goatcounter-1"' in html
    assert 'style="anchor-name: --abbr-gc_goatcounter-1"' in html
    assert 'style="position-anchor: --abbr-gc_goatcounter-1"' in html


def test_inner_abbr_carries_the_expansion_as_a_title(tmp_path):
    blog = _blog(tmp_path, 'We wired {{< abbr "NUT" >}} in.')
    _build(blog)
    assert '<abbr title="Network UPS Tools"' in _post_html(blog)


def test_unknown_key_fails_the_build(tmp_path):
    blog = _blog(tmp_path, 'We wired {{< abbr "XYZ" >}} in.')
    r = _build(blog, expect_ok=False)
    assert r.returncode != 0
    assert "XYZ" in (r.stdout + r.stderr)


# --- the {{< glossary-index >}} shortcode ------------------------------------

def test_glossary_index_lists_every_term_alphabetically(tmp_path):
    # REGISTRY is deliberately stored SLO-then-NUT; output must be NUT-then-SLO.
    blog = _blog(tmp_path, 'Terms:\n\n{{< glossary-index >}}\n')
    _build(blog)
    html = _post_html(blog)
    assert "Network UPS Tools" in html
    assert "Service Level Objective" in html
    assert html.index("Network UPS Tools") < html.index("Service Level Objective")
    assert "<dl" in html


def test_glossary_index_shows_rendered_text_never_the_key(tmp_path):
    blog = _blog(tmp_path, 'Terms:\n\n{{< glossary-index >}}\n')
    _build(blog)
    html = _post_html(blog)
    terms = _DT_RE.findall(html)
    assert ("GoatCounter", "GC") in terms
    assert "GC_GOATCOUNTER" not in html


def test_glossary_index_sorts_on_the_resolved_text_keeping_senses_adjacent(tmp_path):
    # Sorting on the key would put GC_GOATCOUNTER after NUT for a reader who can
    # only see "GC". Display text with the key as tiebreaker keeps both senses
    # together and is a no-op for every entry without rendered_text.
    blog = _blog(tmp_path, 'Terms:\n\n{{< glossary-index >}}\n')
    _build(blog)
    terms = _DT_RE.findall(_post_html(blog))
    assert [name for name, _ in terms] == [
        "Garbage Collection", "GoatCounter",
        "Network UPS Tools", "Service Level Objective"]
    assert [display for _, display in terms] == ["GC", "GC", "NUT", "SLO"]


def test_glossary_index_is_safe_without_a_registry(tmp_path):
    blog = _blog(tmp_path, 'Terms:\n\n{{< glossary-index >}}\n', registry=None)
    _build(blog)          # must not fail the build
    assert "glossary-index" not in _post_html(blog)


# --- stylesheet wiring -------------------------------------------------------

def test_glossary_css_is_linked_before_custom_css(tmp_path):
    blog = _blog(tmp_path, 'We wired {{< abbr "NUT" >}} in.')
    _build(blog)
    html = _post_html(blog)
    assert "glossary" in html
    gi = html.index("glossary.")
    ci = html.index("custom.")
    assert gi < ci, "glossary.css must load before custom.css so a blog can override it"
