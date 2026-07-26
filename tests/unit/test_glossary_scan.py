"""P2 — glossary_scan.py: deterministic abbreviation-candidate extraction.

The scanner proposes; it never decides. Its whole job is to hand the authoring
skill a list of tokens that are (a) plausibly technical abbreviations and (b)
genuinely in prose — not in a code fence, a heading, a link, frontmatter or an
existing shortcode. `excluded_spans()` is public because glossary_apply.py and
validate_glossary.py import it: three consumers, one answer, no disagreement.
"""
import glossary_scan as gs  # tools/ on sys.path via conftest


def _terms(text):
    return {c["term"] for c in gs.candidates(text)}


# --- T1: token shape + stoplist ---------------------------------------------

def test_finds_plain_acronyms():
    assert _terms("We ran NUT and hit an SLO breach.") == {"NUT", "SLO"}


def test_single_characters_never_match():
    assert _terms("A B I X") == set()


def test_overlong_runs_never_match():
    assert _terms("ABCDEFGHIJKL is not an abbreviation") == set()


def test_ten_character_run_is_the_upper_bound():
    assert _terms("ABCDEFGHIJ fits") == {"ABCDEFGHIJ"}


def test_digits_allowed_after_the_first_letter():
    assert _terms("OKLCH and H264 both count") == {"OKLCH", "H264"}


def test_leading_digit_never_matches():
    # Documented limitation: the operator hand-adds 3DES to the registry.
    assert _terms("3DES is legacy") == set()


def test_stoplist_tokens_are_dropped():
    assert _terms("OK TODO FIXME NOTE WARNING AM PM USD EUR BEGIN END") == set()


def test_legitimate_terms_are_not_stoplisted():
    # HTTP/URL/API/CI stay proposable — a reader may well not know them, and the
    # author drops what is not worth defining.
    assert _terms("HTTP and URL and API and CI") == {"HTTP", "URL", "API", "CI"}


# --- T2: exclusion regions ---------------------------------------------------
# Each case pins one region kind. A false positive here means a marker inserted
# into a code sample, a heading or a URL — i.e. a corrupted post.

def test_fenced_block_excluded():
    assert _terms("prose\n\n```\nNUT here\n```\n") == set()


def test_fenced_block_with_info_string_excluded():
    assert _terms("```yaml\nkey: NUT\n```") == set()


def test_tilde_fence_excluded():
    assert _terms("~~~\nNUT\n~~~") == set()


def test_longer_closing_fence_required():
    # A 3-backtick run inside a 4-backtick fence does not close it.
    text = "````\nNUT\n```\nSLO\n````"
    assert _terms(text) == set()


def test_indented_code_block_excluded():
    assert _terms("prose here\n\n    NUT indented\n\nmore prose") == set()


def test_inline_code_excluded():
    assert _terms("run `NUT` now") == set()


def test_double_backtick_inline_code_excluded():
    assert _terms("run ``NUT`` now") == set()


def test_frontmatter_excluded():
    assert _terms("---\ntitle: NUT setup\n---\n\nprose\n") == set()


def test_frontmatter_only_when_leading():
    # A --- rule mid-document is a horizontal rule, not frontmatter.
    assert _terms("prose\n\n---\n\nNUT in prose\n") == {"NUT"}


def test_heading_line_excluded():
    assert _terms("## NUT setup\n\nplain prose\n") == set()


def test_link_target_excluded():
    assert _terms("see [the docs](https://x.example/NUT)") == set()


def test_link_text_excluded():
    assert _terms("see [NUT](https://x.example/)") == set()


def test_bare_url_excluded():
    assert _terms("see https://x.example/NUT/guide for more") == set()


def test_existing_shortcode_excluded():
    assert _terms('already {{< abbr "NUT" >}} marked') == set()


def test_percent_shortcode_tags_excluded_but_inner_prose_is_not():
    # `{{% %}}` renders its body as markdown, so the body IS prose and a marker
    # placed there works. Only the tags themselves are off limits.
    assert _terms('{{% note %}}NUT matters{{% /note %}}') == {"NUT"}
    assert _terms('{{% ABC %}}body{{% /ABC %}}') == set()


def test_raw_html_tag_excluded():
    assert _terms('<abbr title="NUT">x</abbr>') == set()


def test_prose_after_a_fence_is_still_scanned():
    # Proves spans are bounded, not sticky — the common regression.
    assert _terms("```\nSLO\n```\n\nWe then configured NUT.\n") == {"NUT"}


def test_prose_around_inline_code_is_still_scanned():
    assert _terms("we ran `SLO` before NUT started") == {"NUT"}


# --- T3: registry awareness, inflected display forms, JSON CLI ---------------
import json
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCAN = os.path.join(ROOT, "tools", "glossary_scan.py")


def _post(tmp_path, body, name="index.md"):
    p = tmp_path / name
    p.write_text(body)
    return str(p)


def test_plural_becomes_a_display_form(tmp_path):
    found = gs.scan_file(_post(tmp_path, "our SLOs slipped badly"), {}, )
    assert len(found) == 1
    assert found[0]["term"] == "SLO"
    assert found[0]["display"] == "SLOs"


def test_possessive_becomes_a_display_form(tmp_path):
    found = gs.scan_file(_post(tmp_path, "the SLO's budget is gone"), {})
    assert found[0]["term"] == "SLO"
    assert found[0]["display"] == "SLO's"


def test_registered_and_already_marked_is_not_proposed(tmp_path):
    body = 'we ran {{< abbr "NUT" >}} today'
    assert gs.scan_file(_post(tmp_path, body), {"NUT": {}}) == []


def test_registered_but_unmarked_is_still_proposed(tmp_path):
    # A series-wide run must mark post 7 using post 3's definition.
    found = gs.scan_file(_post(tmp_path, "we ran NUT today"), {"NUT": {}})
    assert [f["term"] for f in found] == ["NUT"]


def test_occurrences_are_deduped_with_a_count(tmp_path):
    body = "NUT first.\n\nThen NUT again.\n\nAnd NUT once more.\n"
    found = gs.scan_file(_post(tmp_path, body), {})
    assert len(found) == 1
    assert found[0]["occurrences"] == 3
    assert found[0]["line"] == 1
    assert "NUT first" in found[0]["sentence"]


def test_sentence_is_the_containing_sentence_not_the_paragraph(tmp_path):
    body = "Unrelated opener. We wired NUT into the rack. A third sentence.\n"
    found = gs.scan_file(_post(tmp_path, body), {})
    s = found[0]["sentence"]
    assert "We wired NUT into the rack." in s
    assert "Unrelated opener" not in s


def test_cli_emits_json(tmp_path):
    blog = tmp_path / "blog"
    (blog / "data").mkdir(parents=True)
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump({"version": 5}))
    (blog / "data" / "glossary.yaml").write_text(yaml.safe_dump(
        {"SLO": {"name": "Service Level Objective", "description": "d"}}))
    post = _post(blog, "We hit an SLO breach and NUT saved us.")
    r = subprocess.run([sys.executable, SCAN, "--config",
                        str(blog / ".blog-craft.yaml"), post],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert {d["term"] for d in data} == {"SLO", "NUT"}
    assert all({"term", "display", "file", "line", "sentence", "occurrences"}
               <= set(d) for d in data)


def test_cli_tolerates_a_missing_registry(tmp_path):
    blog = tmp_path / "blog"
    blog.mkdir()
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump({"version": 5}))
    post = _post(blog, "NUT alone.")
    r = subprocess.run([sys.executable, SCAN, "--config",
                        str(blog / ".blog-craft.yaml"), post],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert [d["term"] for d in json.loads(r.stdout)] == ["NUT"]
