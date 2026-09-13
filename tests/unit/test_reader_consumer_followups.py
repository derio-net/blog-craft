"""Reader-surface follow-ups from the first consumer (derio-net/frank#787).

Four things frank had to patch locally in framework-owned files after adopting
0.22.x — exactly the class of drift `/update` overwrites — lifted here so the
consumer's copies converge back onto upstream.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
READER = os.path.join(ROOT, "templates", "features", "reader-experience")
HEXTRA = os.path.join(ROOT, "templates", "hugo-hextra")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def test_covers_are_not_hardcoded_off_for_a_series():
    """0.22.0 omitted the cover on `operating` posts unconditionally; the first
    consumer wanted them back. The exclusion is now the operator's list
    (features.reader_experience.coverless_series -> params.reader.coverless)."""
    header = _read(READER, "layouts", "partials", "reader", "header.html")
    assert 'in .Params.series "operating"' not in header
    assert "site.Params.reader.coverless" in header
    tmpl = _read(HEXTRA, "hugo.toml.tmpl")
    assert "with .coverless_series" in tmpl and "coverless = [" in tmpl


def test_series_tiles_render_an_image_when_the_data_gives_one():
    sc = _read(READER, "layouts", "shortcodes", "reader-home.html")
    assert "with .image" in sc and "reader-series-card" in sc
    # and still the text tile without one
    assert 'class="reader-topic"' in sc


def test_topics_index_has_a_tile_shortcode_in_the_bundle():
    sc = _read(READER, "layouts", "shortcodes", "reader-topics.html")
    assert "reader-topic-index" in sc and "reader-count" in sc
    # chips only when the blog has a layer palette — never a hard dependency
    assert "site.Data.layer_palette" in sc
    css = _read(READER, "assets", "css", "reader.css")
    assert ".reader-chip" in css and ".reader-series-card" in css


def test_top_level_sections_outside_docs_get_their_own_banner():
    banner = _read(HEXTRA, "layouts", "partials", "site-banner.html")
    assert 'printf "images/banner-%s.png" (index $parts 0)' in banner
