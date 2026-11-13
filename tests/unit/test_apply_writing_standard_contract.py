"""P3 — apply-writing-standard skill contract (R14, R14a, R15, R16, R17).

Grep-style contract tests in the style of test_cold_reader_contract.py: they
pin the load-bearing strings of the skill without judging its prose.
"""
import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(ROOT, "skills", "apply-writing-standard", "SKILL.md")


def _read(path):
    assert os.path.exists(path), f"missing file: {path}"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _frontmatter():
    m = re.match(r"^---\n(.*?)\n---\n", _read(SKILL), re.DOTALL)
    assert m, "no yaml frontmatter block"
    return yaml.safe_load(m.group(1))


def _body():
    """The text after the front matter, with each run of white space as one
    space, so a phrase that wraps across lines still matches."""
    return " ".join(_read(SKILL).split("\n---\n", 1)[1].split())


def _args():
    return {a["name"]: a for a in _frontmatter()["arguments"]}


# ---- front matter

def test_the_skill_is_named_and_user_invocable():
    fm = _frontmatter()
    assert fm["name"] == "apply-writing-standard"
    assert fm["user-invocable"] is True
    assert fm["description"].strip()


def test_standard_and_paths_are_required_arguments():
    args = _args()
    assert args["standard"]["required"] is True
    assert args["paths"]["required"] is True


def test_batch_size_is_optional_3_to_5_default_4():
    arg = _args()["batch_size"]
    assert arg["required"] is False
    assert "3" in arg["description"] and "5" in arg["description"]
    assert re.search(r"default(?:s to)?:? 4", arg["description"], re.IGNORECASE)


def test_the_argument_list_is_exactly_these_three():
    assert set(_args()) == {"standard", "paths", "batch_size"}


# ---- refusals (R14a)

def test_it_refuses_an_unknown_standard_and_lists_the_shipped_ones():
    body = _body()
    assert "unknown standard" in body
    assert "standards/" in body
    for name in ("ste", "elements-of-style", "plain-language"):
        assert f"`{name}`" in body


def test_it_refuses_uncommitted_pages_and_pages_with_no_version_at_head():
    body = _body()
    assert "uncommitted changes" in body
    assert "no version at `HEAD`" in body
    assert re.search(r"git [^`]*status --porcelain", body)


# ---- the rewrite (R14, R15)

def test_it_changes_the_language_only_and_names_what_it_keeps():
    body = _body()
    assert "language only" in body
    for kept in ("front matter key", "section order", "fenced code", "inline code",
                 "numerals", "link targets"):
        assert kept in body, f"keep list misses {kept!r}"
    assert "anchors" in body


def test_it_finds_inbound_links_to_a_changed_headings_old_anchor():
    body = _body()
    assert "old anchor" in body
    assert re.search(r"git grep [^`]*#<old-slug>", body), "no grep for the old anchor"


def test_it_does_not_touch_the_cover_weight_or_url():
    body = _body()
    assert "cover image" in body and "`weight`" in body and "URL" in body


# ---- the batch loop (R16)

def test_each_batch_runs_the_checker_against_head_with_stats():
    body = _body()
    assert re.search(r"validate_writing_standard\.py [^`]*--preserve-from HEAD [^`]*--stats", body)


def test_it_may_not_waive_a_check_to_pass():
    assert "never add a waiver" in _body()


def test_fact_keeper_runs_once_per_page():
    body = _body()
    assert "fact-keeper" in body
    assert "once per page" in body
    assert "agents/fact-keeper.md" in body


def test_the_baseline_is_written_outside_the_repository_and_deleted_after_the_batch():
    body = _body()
    assert "outside the repository" in body
    assert "git show HEAD:" in body
    assert "delete the baseline directory" in body


def test_it_prints_one_summary_line_per_page():
    body = _body()
    assert "one line per page" in body
    for field in ("kept", "changed", "lost", "added"):
        assert field in body


def test_it_stops_for_approval_between_batches():
    body = _body()
    assert "approval" in body
    assert "next batch" in body
    stop = body.index("Stop for the operator's approval")
    fact = body.index("once per page")
    assert fact < stop, "the fact check must come before the approval stop"


def test_drafts_are_written_in_place_with_git_as_the_safety_net():
    body = _body()
    assert "in place" in body
    assert "`.bak`" in body


# ---- one session (R17)

def test_it_names_the_no_claude_p_batch_rule_and_one_session():
    body = _body()
    assert "no-claude-p-batch" in body
    assert "claude -p" in body
    assert "one session" in body
    assert "subagent" in body


def test_it_never_calls_its_output_conformant_or_compliant():
    text = _read(SKILL).lower()
    assert "conformant" not in text and "compliant" not in text


# ---- review fixes (phase 3)

def _step(n):
    """The text of '## Step n' up to the next '## Step' heading (white space collapsed)."""
    body = _body()
    parts = body.split(f"## Step {n}:")
    assert len(parts) > 1, f"no '## Step {n}:' heading"
    return parts[1].split("## Step ")[0]


def test_step_2_resolves_each_pages_standard_before_any_rewrite():
    """p3-r5: a page that resolves to another standard, or to none, is found
    before the rewrite, by the STATS lines of a first checker run."""
    step2 = _step(2)
    assert "--stats" in step2
    assert "STATS" in step2
    assert "`none`" in step2
    assert "ask the operator" in step2


def test_the_batch_stops_when_stats_lines_do_not_match_the_pages():
    """p3-r5 / p3-r9: the standard-mismatch stop in the batch loop."""
    step3 = _step(3)
    assert "one `STATS` line for each page" in step3
    assert "Stop and ask the operator" in step3


def test_the_baseline_keeps_the_repository_relative_path():
    """p3-r6: two index.md pages must not share one baseline file."""
    body = _body()
    assert "<baseline>/<path relative to the toplevel>" in body
    assert "git -C <page directory> show HEAD:./<file name>" in body


def test_an_anchor_the_checker_cannot_resolve_is_restored_and_listed():
    """p3-r7: the way out of an unwaivable preserve FAIL."""
    body = _body()
    assert "restore the old link" in body
    assert "inbound link" in body


def test_the_inbound_link_search_catches_every_link_form():
    """p3-r8."""
    body = _body()
    assert "git -C <page toplevel> grep -nE" in body
    assert "#<old-slug>([)" in body
    assert "GitHub" in body and "{#id}" in body
    assert "resolves to the renamed page" in body


def test_fact_keeper_gets_exactly_two_paths():
    assert "exactly two paths" in _step(3)


def test_the_summary_line_has_every_field():
    step3 = _step(3)
    for field in ("headings changed", "inbound links listed", "checker", "avg", "sentences"):
        assert field in step3, f"summary misses {field!r}"
