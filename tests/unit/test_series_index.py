"""P1 — the series-index shortcode renders a page-derived index of a series' posts.

Default style is `cards` (a vertical timeline); the same page-derived selection
(series filter, weight order, host-page self-exclusion, draft handling) is asserted
here against the card markup. Style switching itself lives in test_series_index_style.py.
"""
import glob
import os
import re
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

# (number, url, title) per card — `si-num` is unique to the cards, so this never
# matches Hextra's own nav / og:url links (the reason we don't scope by hand).
_CARD = re.compile(r'class="si-num">(\d+)</span><a href="([^"]+)">([^<]+)</a>')


def _cards(html):
    return _CARD.findall(html)


def _bootstrap(tmp_path):
    cfg = yaml.safe_load(open(os.path.join(FIX, "stoa-v2.expected.yaml")))
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = tmp_path / "blog"
    subprocess.run(["bash", RENDER, str(ans), str(blog)], check=True, capture_output=True, text=True)
    return blog


def _post(blog, series, num, slug, weight, summary):
    d = blog / "content" / "docs" / series / f"{num}-{slug}"
    d.mkdir(parents=True)
    (d / "index.md").write_text(
        f'---\ntitle: "{slug.replace("-", " ").title()}"\nseries: [{series}]\n'
        f'weight: {weight}\ndraft: false\nsummary: "{summary}"\n---\nbody\n')


def _overview(blog, series, body="{{< series-index >}}"):
    d = blog / "content" / "docs" / series / "00-overview"
    d.mkdir(parents=True)
    (d / "index.md").write_text(
        f'---\ntitle: "{series.title()} Overview"\nseries: [{series}]\nweight: 1\n---\n{body}\n')


def _build_overview_html(blog, series, drafts=True):
    cmd = ["hugo"] + (["--buildDrafts"] if drafts else [])
    r = subprocess.run(cmd, cwd=str(blog), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    hits = glob.glob(str(blog / "public" / "**" / series / "00-overview" / "index.html"), recursive=True)
    assert hits, f"no built overview for {series}"
    return open(hits[0]).read()


def test_series_index_renders_cards(tmp_path):
    blog = _bootstrap(tmp_path)
    _overview(blog, "building")
    # created out of order; distinct weights that define the display order
    _post(blog, "building", "02", "foundation", 20, "Talos and Omni bootstrap")
    _post(blog, "building", "01", "introduction", 10, "Why maximum-complexity homelab")
    _post(blog, "building", "03", "storage", 30, "Longhorn distributed block")
    html = _build_overview_html(blog, "building")
    assert '<div class="series-index">' in html and 'class="si-card' in html
    cards = _cards(html)
    assert [n for n, _, _ in cards] == ["01", "02", "03"], "cards not in weight order"
    urls = [u for _, u, _ in cards]
    for slug in ("01-introduction", "02-foundation", "03-storage"):
        assert any(f"building/{slug}/" in u for u in urls), f"{slug} not carded"
    for summ in ("Why maximum-complexity homelab", "Talos and Omni bootstrap",
                 "Longhorn distributed block"):
        assert summ in html, f"summary missing: {summ}"      # summaries are card-only
    assert not any("00-overview" in u for u in urls), "overview lists itself"
    assert len(cards) == 3


def test_overview_template_uses_shortcode(tmp_path):
    blog = _bootstrap(tmp_path)   # fixture has features.series_overview_posts: true
    overviews = glob.glob(str(blog / "content" / "docs" / "*" / "00-overview" / "index.md"))
    assert overviews, "no per-series overview materialized"
    for ov in overviews:
        txt = open(ov).read()
        assert "{{< series-index >}}" in txt, f"overview missing the shortcode: {ov}"
        assert "auto-appends" not in txt, f"stale marker left in {ov}"
    series = os.path.basename(os.path.dirname(os.path.dirname(overviews[0])))
    _post(blog, series, "01", "first", 10, "First post takeaway")
    html = _build_overview_html(blog, series)
    assert any(f"{series}/01-first/" in u for _, u, _ in _cards(html)), "post not carded by the overview shortcode"


def test_series_index_empty_series(tmp_path):
    blog = _bootstrap(tmp_path)
    _overview(blog, "operating")          # no operating posts exist
    html = _build_overview_html(blog, "operating")
    assert "series-index-empty" in html and "No posts yet" in html
    assert 'class="si-card' not in html


def test_series_index_positional_override(tmp_path):
    blog = _bootstrap(tmp_path)
    # host page is in 'building' but explicitly asks for the 'operating' index
    _overview(blog, "building", body='{{< series-index "operating" >}}')
    _post(blog, "operating", "01", "cluster-nodes", 10, "Node inventory")
    _post(blog, "building", "01", "intro", 10, "should not appear")
    html = _build_overview_html(blog, "building")
    urls = [u for _, u, _ in _cards(html)]
    assert any("operating/01-cluster-nodes/" in u for u in urls), "overridden series not carded"
    assert not any("building/01-intro/" in u for u in urls), "host series leaked in"


def test_series_index_excludes_drafts(tmp_path):
    blog = _bootstrap(tmp_path)
    _overview(blog, "building")
    _post(blog, "building", "01", "published", 10, "live post")
    d = blog / "content" / "docs" / "building" / "02-wip"; d.mkdir(parents=True)
    (d / "index.md").write_text(
        '---\ntitle: "Wip"\nseries: [building]\nweight: 20\ndraft: true\nsummary: "draft"\n---\nb\n')
    html = _build_overview_html(blog, "building", drafts=False)   # production build
    urls = [u for _, u, _ in _cards(html)]
    assert any("building/01-published/" in u for u in urls)
    assert not any("building/02-wip/" in u for u in urls)         # draft absent from a non-draft build


def test_papers_overview_uses_series_index(tmp_path):
    # a papers series overview gets {{< series-index >}} like any other series —
    # NOT {{< papers-roadmap >}} (that needs a data/papers.yaml roster a fresh
    # blog lacks, which would break the first hugo build). A roster-maintaining
    # blog swaps it in during adoption.
    cfg = yaml.safe_load(open(os.path.join(FIX, "answers-papers-v2.yaml")))
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = tmp_path / "blog"
    subprocess.run(["bash", RENDER, str(ans), str(blog)], check=True, capture_output=True, text=True)
    ov = lambda key: (blog / "content" / "docs" / key / "00-overview" / "index.md").read_text()
    papers_key = next(s["key"] for s in cfg["series"] if s.get("content_type") == "papers")
    assert "{{< series-index >}}" in ov(papers_key)
    assert "{{< papers-roadmap >}}" not in ov(papers_key)
