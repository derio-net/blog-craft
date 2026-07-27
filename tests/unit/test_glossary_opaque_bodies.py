"""A shortcode body handed to a renderer is not prose.

`{{< papers/landscape >}}` wraps its `.Inner` in `<pre class="mermaid">` under a
`quadrantChart` header. A marker there expands to a whole `<button
popovertarget>` + `<span popover>` tree inside a chart axis, and mermaid dies:

    Lexical error on line 4. Unrecognized text.

The scanner excluded fences, headings, links, frontmatter and the shortcode TAG
— but not a shortcode BODY, so `x-axis OSS --> Commercial` read as prose. Found
on a real blog: a full-blog sweep marked four such lines across four papers, and
the only thing that objected was a mermaid validator running over the RENDERED
output, whose error names a lexer position and nothing else.

Two halves, both needed. `excluded_spans` stops new markers being proposed or
inserted; `misplaced_markers` reports the ones a pre-fix sweep already wrote,
because the applier is idempotent — it never removes what it would no longer
add, so without the report they sit there until some build fails.

The criterion is "the body is renderer source", NOT "the shortcode has a body".
`papers/pullquote` and `papers/scar` also take `.Inner` and it is ordinary prose
that SHOULD be marked; excluding every shortcode body would silently drop
legitimate markers.
"""
import subprocess
import sys
import os

import glossary_apply as ga
from glossary_scan import candidates, misplaced_markers, opaque_body_spans

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REG = {"OSS": {"name": "Open Source Software", "description": "d"},
       "SLO": {"name": "Service Level Objective", "description": "d"}}

LANDSCAPE = (
    '{{< papers/landscape axes="x:OSS↔commercial" >}}\n'
    "    title Storage on bare metal\n"
    "    x-axis OSS --> Commercial\n"
    '    "Longhorn": [0.25, 0.75]\n'
    "{{< /papers/landscape >}}\n"
)


def _post(tmp_path, body, name="index.md"):
    p = tmp_path / name
    p.write_text(body)
    return p


def test_a_landscape_body_is_not_a_candidate():
    terms = [c["term"] for c in candidates(LANDSCAPE)]
    assert "OSS" not in terms, "diagram source must never be proposed for marking"


def test_prose_around_a_landscape_body_is_still_scanned():
    # The exclusion must be the BODY, not the whole document after the opener —
    # an over-broad span silently stops marking the rest of the post.
    text = "Before the chart, OSS matters.\n\n" + LANDSCAPE + "\nAfter it, SLO matters.\n"
    terms = [c["term"] for c in candidates(text)]
    assert terms.count("OSS") == 1 and "SLO" in terms


def test_a_prose_bodied_shortcode_is_still_marked():
    # pullquote/scar take .Inner too, and it IS prose. Excluding every shortcode
    # body would quietly cost every marker inside them.
    text = "{{< papers/scar date=\"2026-05-03\" >}}\nThe OSS build lacked it.\n{{< /papers/scar >}}\n"
    assert "OSS" in [c["term"] for c in candidates(text)]


def test_apply_writes_nothing_into_a_landscape_body(tmp_path):
    p = _post(tmp_path, LANDSCAPE)
    before = p.read_text()
    edits = ga.apply_file(str(p), REG, first_occurrence_only=True)
    assert edits == [], "nothing in a diagram body is markable"
    assert p.read_text() == before, "the applier shares the scanner's exclusions"


def test_an_unclosed_landscape_cannot_swallow_the_document():
    # The body span is bounded by a lookahead for the closing tag, so a malformed
    # shortcode excludes nothing rather than everything after it.
    text = "{{< papers/landscape >}}\n    x-axis OSS --> Commercial\n\nLater OSS prose.\n"
    assert opaque_body_spans(text) == []
    assert "OSS" in [c["term"] for c in candidates(text)]


def test_an_unclosed_opener_does_not_pair_with_a_later_blocks_closer():
    # Regression: a `*?` body reached past the unclosed opener to the NEXT
    # block's closer and swallowed every paragraph between them. The prose in
    # the middle must stay markable; only the real block's body is excluded.
    text = ("A {{< papers/landscape >}}\n\nSLO prose here.\n\n"
            "{{< papers/landscape >}}\n    x-axis RAID --> C\n{{< /papers/landscape >}}\n")
    terms = [c["term"] for c in candidates(text)]
    assert "SLO" in terms, "prose between a stray opener and a real block was lost"
    assert "RAID" not in terms, "the real diagram body must still be excluded"


def test_an_opener_shown_in_inline_code_is_documentation_not_a_block():
    # Regression, and the nastier half: backtracking EXTENDED the opening tag
    # past its own `>}}` to the next block's, so an opener quoted in prose
    # reported that block's body as its own and un-marked everything between.
    text = ("Wrap it in `{{< papers/landscape >}}` first.\n\n"
            "Then SLO and NUT and RAID matter.\n\n"
            "{{< papers/landscape >}}\n    x-axis GPU --> C\n{{< /papers/landscape >}}\n")
    terms = [c["term"] for c in candidates(text)]
    assert {"SLO", "NUT", "RAID"} <= set(terms)
    assert "GPU" not in terms


def test_two_landscape_blocks_exclude_only_their_own_bodies():
    text = (LANDSCAPE + "\nBetween them NUT matters.\n\n"
            + LANDSCAPE.replace("OSS", "RAID"))
    assert [c["term"] for c in candidates(text)] == ["NUT"]


def test_the_percent_delimited_form_is_excluded_too():
    # `{{% %}}` renders .Inner as markdown, which breaks a diagram just as
    # thoroughly; an asymmetry between the two forms would be a trap.
    text = "{{% papers/landscape %}}\n    x-axis OSS --> C\n{{% /papers/landscape %}}\n"
    assert [c["term"] for c in candidates(text)] == []


def test_a_documented_example_in_a_fence_is_not_reported_as_misplaced():
    # A post explaining the shortcode must not fail its own blog's CI. This is
    # the invariant markers_in already honours; the two must not disagree about
    # the same text.
    text = ('Docs:\n\n```markdown\n{{< papers/landscape >}}\n'
            '    x-axis {{< abbr "OSS" >}} --> C\n{{< /papers/landscape >}}\n```\n')
    from glossary_scan import markers_in
    assert misplaced_markers(text) == []
    assert markers_in(text) == [], "the two marker views must agree"


def test_misplaced_markers_reports_a_pre_existing_marker():
    text = LANDSCAPE.replace("x-axis OSS", 'x-axis {{< abbr "OSS" >}}')
    found = misplaced_markers(text)
    assert [name for name, _ in found] == ["papers/landscape"]
    assert found[0][1] == 3, "reports the line, so the operator can go straight to it"


def test_misplaced_markers_ignores_markers_in_prose():
    assert misplaced_markers('A {{< abbr "OSS" >}} build.\n' + LANDSCAPE) == []


def test_validator_fails_on_a_marker_inside_a_landscape_body(tmp_path):
    # End-to-end: the key is VALID, so only a placement check can catch this.
    cfg = tmp_path / ".blog-craft.yaml"
    data = tmp_path / "data"
    data.mkdir()
    (data / "glossary.yaml").write_text(
        "OSS:\n  name: Open Source Software\n  description: d\n")
    cfg.write_text("version: 5\nsite_dir: .\n")
    post = _post(tmp_path, LANDSCAPE.replace("x-axis OSS", 'x-axis {{< abbr "OSS" >}}'))

    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "validate_glossary.py"),
         "--config", str(cfg), str(post)],
        capture_output=True, text=True, cwd=tmp_path)

    assert r.returncode == 1
    assert "papers/landscape" in r.stderr and "renderer source" in r.stderr
