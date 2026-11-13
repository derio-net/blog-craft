"""validate_writing_standard --preserve-from (R12).

Each test builds a git repository in tmp_path, commits a page, edits the
working-tree copy, and runs the checker against HEAD. Every rule has a
positive test (the change fails `preserve`) and a negative one (a change the
rule must accept).
"""
import subprocess

import pytest

import validate_writing_standard as vws

BASE = (
    "# Install the tool\n"
    "\n"
    "Run the installer. It takes 3 minutes.\n"
    "\n"
    "Use `make install` to build. See [the guide](guide.md) for details.\n"
    "\n"
    "1. Open the file.\n"
    "2. Save the file.\n"
    "\n"
    "```bash\n"
    "make install PREFIX=/usr/local\n"
    "```\n"
)


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )


def _repo(tmp_path, name="repo"):
    root = tmp_path / name
    root.mkdir()
    _git(root, "init", "-q")
    return root


def _committed(root, rel, text):
    page = root / rel
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(text, encoding="utf-8")
    _git(root, "add", rel)
    _git(root, "commit", "-q", "-m", "page")
    return page


def _run(page, capsys, ref="HEAD"):
    code = vws.main(["--default", "ste", "--preserve-from", ref, str(page)])
    out = capsys.readouterr().out
    return code, [line for line in out.splitlines() if ": preserve: " in line]


def _edit(tmp_path, capsys, before, after, rel="page.md"):
    root = _repo(tmp_path)
    page = _committed(root, rel, before)
    page.write_text(after, encoding="utf-8")
    return _run(page, capsys)


# ------------------------------------------------------------------ fenced code

def test_a_changed_fenced_code_block_fails(tmp_path, capsys):
    code, hits = _edit(tmp_path, capsys, BASE, BASE.replace("PREFIX=/usr/local", "PREFIX=/opt"))
    assert code == 1
    assert any("fenced code" in h and "disappeared" in h and "/usr/local" in h for h in hits)
    assert any("fenced code" in h and "appeared" in h and "/opt" in h for h in hits)
    assert all(h.startswith("FAIL: ") for h in hits)


def test_an_unchanged_fenced_code_block_passes(tmp_path, capsys):
    after = BASE.replace("Run the installer.", "Start the installer.")
    _, hits = _edit(tmp_path, capsys, BASE, after)
    assert hits == []


# ------------------------------------------------------------------ inline code

def test_a_changed_inline_code_span_fails(tmp_path, capsys):
    code, hits = _edit(tmp_path, capsys, BASE, BASE.replace("`make install`", "`make all`"))
    assert code == 1
    assert any("inline code" in h and "disappeared" in h and "make install" in h for h in hits)
    assert any("inline code" in h and "appeared" in h and "make all" in h for h in hits)


def test_a_moved_inline_code_span_passes(tmp_path, capsys):
    after = BASE.replace("Use `make install` to build.", "To build, use `make install`.")
    _, hits = _edit(tmp_path, capsys, BASE, after)
    assert hits == []


# ------------------------------------------------------------------ link targets

def test_a_changed_link_target_fails(tmp_path, capsys):
    code, hits = _edit(tmp_path, capsys, BASE, BASE.replace("(guide.md)", "(manual.md)"))
    assert code == 1
    assert any("link target" in h and "guide.md" in h and "disappeared" in h for h in hits)
    assert any("link target" in h and "manual.md" in h and "appeared" in h for h in hits)


def test_changed_link_text_with_the_same_target_passes(tmp_path, capsys):
    after = BASE.replace("[the guide](guide.md)", "[the install guide](guide.md)")
    _, hits = _edit(tmp_path, capsys, BASE, after)
    assert hits == []


def test_a_changed_reference_definition_target_fails(tmp_path, capsys):
    before = BASE + "\nRead [the spec][s].\n\n[s]: https://example.com/spec\n"
    after = before.replace("https://example.com/spec", "https://example.com/other")
    code, hits = _edit(tmp_path, capsys, before, after)
    assert code == 1
    assert any("link target" in h and "example.com/spec" in h for h in hits)


# ------------------------------------------------------------------ anchors

ANCHORED = (
    "# Guide\n"
    "\n"
    "Go to [setup](#old-setup) first.\n"
    "\n"
    "## Old setup\n"
    "\n"
    "Install the tool.\n"
)


def test_a_renamed_heading_with_its_anchor_updated_passes(tmp_path, capsys):
    after = ANCHORED.replace("## Old setup", "## Set up the tool").replace(
        "#old-setup", "#set-up-the-tool")
    _, hits = _edit(tmp_path, capsys, ANCHORED, after)
    assert hits == []


def test_an_anchor_that_names_no_heading_fails(tmp_path, capsys):
    after = ANCHORED.replace("## Old setup", "## Set up the tool").replace(
        "#old-setup", "#no-such-heading")
    code, hits = _edit(tmp_path, capsys, ANCHORED, after)
    assert code == 1
    assert any("#no-such-heading" in h and "appeared" in h for h in hits)
    assert any("#old-setup" in h and "disappeared" in h for h in hits)


def test_an_anchor_into_another_page_is_checked_against_that_page(tmp_path, capsys):
    root = _repo(tmp_path)
    (root / "other.md").write_text("# Other\n\n## Set up the tool\n\nText.\n", encoding="utf-8")
    before = "# Page\n\nSee [setup](other.md#old-setup).\n"
    page = _committed(root, "page.md", before)
    page.write_text(before.replace("#old-setup", "#set-up-the-tool"), encoding="utf-8")
    assert _run(page, capsys)[1] == []
    page.write_text(before.replace("#old-setup", "#missing"), encoding="utf-8")
    assert _run(page, capsys)[1] != []


def test_an_anchor_change_that_also_changes_the_path_fails(tmp_path, capsys):
    root = _repo(tmp_path)
    (root / "other.md").write_text("# Other\n\n## Set up\n", encoding="utf-8")
    before = "# Page\n\nSee [setup](guide.md#old).\n"
    page = _committed(root, "page.md", before)
    page.write_text(before.replace("guide.md#old", "other.md#set-up"), encoding="utf-8")
    assert _run(page, capsys)[1] != []


def test_github_slugs_drop_punctuation_and_number_duplicates():
    assert vws.heading_slugs("# Set up `fr`: the tool!\n\n## Notes\n\n## Notes\n") == {
        "set-up-fr-the-tool", "notes", "notes-1"}


# ------------------------------------------------------------------ numerals

def test_a_changed_numeral_fails(tmp_path, capsys):
    code, hits = _edit(tmp_path, capsys, BASE, BASE.replace("3 minutes", "5 minutes"))
    assert code == 1
    assert any("numeral" in h and "'3'" in h and "disappeared" in h for h in hits)
    assert any("numeral" in h and "'5'" in h and "appeared" in h for h in hits)
    # the hit names the line of the whole number, not of a digit inside another
    assert any(":3: preserve: numeral '5' appeared" in h for h in hits)
    assert any("'3' disappeared (1x, line 3 at HEAD)" in h for h in hits)


def test_a_numeral_spelled_out_fails_because_the_numeral_is_lost(tmp_path, capsys):
    code, hits = _edit(tmp_path, capsys, BASE, BASE.replace("3 minutes", "three minutes"))
    assert code == 1
    assert any("numeral" in h and "'3'" in h and "disappeared" in h for h in hits)


def test_a_changed_spelled_out_number_is_not_a_numeral(tmp_path, capsys):
    """Documented limit: "two" -> "three" is the fact check's job, not this one's."""
    before = BASE.replace("3 minutes", "two minutes")
    _, hits = _edit(tmp_path, capsys, before, before.replace("two minutes", "three minutes"))
    assert hits == []


def test_percentages_and_decimals_are_numerals(tmp_path, capsys):
    before = BASE + "\nThe rate is 2.5% today.\n"
    code, hits = _edit(tmp_path, capsys, before, before.replace("2.5%", "2.5"))
    assert code == 1
    assert any("'2.5%'" in h for h in hits)


def test_numerals_inside_code_and_link_targets_are_not_prose_numerals():
    items = vws.preserved_items(BASE + "\nSee [v](https://example.com/7).\n")
    assert items["numeral"] == {"3": 1}


def test_splitting_a_numbered_step_renumbers_without_a_hit(tmp_path, capsys):
    after = BASE.replace(
        "1. Open the file.\n2. Save the file.\n",
        "1. Open the file.\n2. Edit the file.\n3. Save the file.\n")
    _, hits = _edit(tmp_path, capsys, BASE, after)
    assert hits == []


def test_a_reworded_sentence_keeping_everything_passes(tmp_path, capsys):
    after = BASE.replace("Run the installer. It takes 3 minutes.",
                         "Start the installer. The installer needs 3 minutes.")
    code, hits = _edit(tmp_path, capsys, BASE, after)
    assert hits == []


# ------------------------------------------------------------------ the ref

def test_a_page_with_no_version_at_the_ref_fails(tmp_path, capsys):
    root = _repo(tmp_path)
    _committed(root, "other.md", "# Other\n")
    page = root / "new.md"
    page.write_text("# New\n\nText.\n", encoding="utf-8")
    code, hits = _run(page, capsys)
    assert code == 1
    assert hits == [f"FAIL: {page}:1: preserve: no version at HEAD"]


def test_the_page_is_read_at_its_own_toplevel(tmp_path, capsys, monkeypatch):
    """The page lives in another repository than the script and the cwd; git
    show runs at the page's toplevel with a path relative to it."""
    elsewhere = _repo(tmp_path, "elsewhere")
    root = _repo(tmp_path)
    page = _committed(root, "content/docs/page.md", BASE)
    monkeypatch.chdir(elsewhere)
    assert _run(page, capsys)[1] == []
    page.write_text(BASE.replace("3 minutes", "4 minutes"), encoding="utf-8")
    assert _run(page, capsys)[1] != []


def test_a_page_outside_any_git_repository_is_a_usage_error(tmp_path, capsys):
    page = tmp_path / "loose.md"
    page.write_text("# Loose\n", encoding="utf-8")
    assert vws.main(["--default", "ste", "--preserve-from", "HEAD", str(page)]) == 2


def test_the_preserve_hit_cannot_be_waived(tmp_path, capsys):
    """p3-r9: the waiver covers the changed line, and the hit on it stays."""
    after = BASE.replace("Run the installer. It takes 3 minutes.",
                         "<!-- writing-standard: ignore preserve -- I want to -->\n"
                         "Run the installer. It takes 4 minutes.")
    code, hits = _edit(tmp_path, capsys, BASE, after)
    assert code == 1
    assert any(":4: preserve: numeral '4' appeared" in h for h in hits)


def test_a_front_matter_preserve_waiver_is_refused(tmp_path, capsys):
    """p3-r9: front matter cannot waive preserve either: it names no check."""
    before = "---\ntitle: T\n---\n\n" + BASE
    after = before.replace("title: T", "title: T\nwriting_standard_waive: {preserve: I want to}")
    root = _repo(tmp_path)
    page = _committed(root, "page.md", before)
    page.write_text(after.replace("3 minutes", "4 minutes"), encoding="utf-8")
    code = vws.main(["--default", "ste", "--preserve-from", "HEAD", str(page)])
    captured = capsys.readouterr()
    assert code == 2
    assert "preserve" in captured.err


def test_preserved_items_lists_each_kind_of_a_known_page():
    """p3-r9: the multisets of BASE, exactly."""
    items = vws.preserved_items(BASE)
    assert items["fenced code"] == {"```bash\nmake install PREFIX=/usr/local\n```": 1}
    assert items["inline code"] == {"make install": 1}
    assert items["link target"] == {"guide.md": 1}
    assert items["numeral"] == {"3": 1}


# ------------------------------------------------------------------ review fixes (phase 3)

def test_numerals_in_link_text_are_compared(tmp_path, capsys):
    """p3-r1: replacing a link must keep its text for the numeral scan."""
    root = _repo(tmp_path)
    (root / "b.md").write_text("# B\n\n## Install\n", encoding="utf-8")
    before = "# Page\n\nSee [3 steps](b.md#install).\n"
    page = _committed(root, "page.md", before)
    page.write_text(before.replace("[3 steps]", "[5 steps]"), encoding="utf-8")
    code, hits = _run(page, capsys)
    assert code == 1
    assert any("numeral '5' appeared" in h for h in hits)


def test_link_text_numerals_unchanged_pass(tmp_path, capsys):
    before = "# Page\n\nSee [3 steps](b.md).\n"
    _, hits = _edit(tmp_path, capsys, before, before.replace("See [3", "Read [3"))
    assert hits == []


@pytest.mark.parametrize("text, target", [
    ("See [z](<c d.md#e>).\n", "c d.md#e"),
    ('See [x]({{< ref "b.md#usage" >}}).\n', '{{< ref "b.md#usage" >}}'),
    ('See [x]({{< relref "b.md#usage" >}}).\n', '{{< relref "b.md#usage" >}}'),
    ('See <a href="b.html#usage">usage</a>.\n', "b.html#usage"),
    ('See <img src="img/3.png" alt="x">.\n', "img/3.png"),
    ("See [x](b.md \"Title 7\").\n", "b.md"),
])
def test_each_link_form_gives_its_target(text, target):
    """p3-r2: angle targets with spaces, Hugo ref/relref, HTML href/src."""
    items = vws.preserved_items("# P\n\n" + text)
    assert items["link target"] == {target: 1}
    assert items["numeral"] == {}


def test_a_changed_hugo_ref_target_fails(tmp_path, capsys):
    before = '# P\n\nSee [x]({{< ref "b.md" >}}).\n'
    code, hits = _edit(tmp_path, capsys, before, before.replace("b.md", "c.md"))
    assert code == 1 and any("link target" in h for h in hits)


def test_a_changed_html_href_fails(tmp_path, capsys):
    before = '# P\n\nSee <a href="b.html">usage</a>.\n'
    code, hits = _edit(tmp_path, capsys, before, before.replace("b.html", "c.html"))
    assert code == 1 and any("link target" in h for h in hits)


def test_an_anchor_move_into_a_hugo_ref_is_accepted(tmp_path, capsys):
    root = _repo(tmp_path)
    (root / "b.md").write_text("# B\n\n## Usage\n", encoding="utf-8")
    before = '# P\n\nSee [x]({{< ref "b.md#use" >}}).\n'
    page = _committed(root, "page.md", before)
    page.write_text(before.replace("#use", "#usage"), encoding="utf-8")
    assert _run(page, capsys)[1] == []


def test_an_anchor_move_is_refused_when_the_old_heading_still_exists(tmp_path, capsys):
    """p3-r3: retargeting a link that still resolves is a real change."""
    root = _repo(tmp_path)
    (root / "b.md").write_text("# B\n\n## Install\n\n## Usage\n", encoding="utf-8")
    before = "# P\n\nSee [see](b.md#install).\n"
    page = _committed(root, "page.md", before)
    page.write_text(before.replace("#install", "#usage"), encoding="utf-8")
    code, hits = _run(page, capsys)
    assert code == 1 and any("#usage" in h for h in hits)


def test_a_wrapped_sentence_ending_in_a_number_is_not_a_list_marker(tmp_path, capsys):
    """p3-r4: "20." at a line start after paragraph text is a numeral."""
    before = "# P\n\nThe limit is 20. Use it.\n"
    _, hits = _edit(tmp_path, capsys, before, "# P\n\nThe limit is\n20. Use it.\n")
    assert hits == []


def test_a_changed_year_at_a_wrapped_line_start_fails(tmp_path, capsys):
    before = "# P\n\nReleased in\n2019. Then it grew.\n"
    code, hits = _edit(tmp_path, capsys, before, before.replace("2019", "2024"))
    assert code == 1 and any("'2019' disappeared" in h for h in hits)


def test_list_markers_after_a_blank_line_or_in_a_list_are_not_numerals():
    text = "# P\n\nIntro:\n1. One.\n2. Two.\n   lazy text\n3. Three.\n\n> 4. Quoted.\n"
    assert vws.preserved_items(text)["numeral"] == {}


def test_a_page_with_no_standard_is_still_preserve_checked(tmp_path, capsys):
    """p3-r5: writing_standard: none skips the checks, not preservation."""
    before = "---\nwriting_standard: none\n---\n\n" + BASE
    code, hits = _edit(tmp_path, capsys, before, before.replace("3 minutes", "4 minutes"))
    assert code == 1
    assert any("numeral '4' appeared" in h for h in hits)


def test_a_skipped_page_that_kept_everything_passes(tmp_path, capsys):
    before = "---\nwriting_standard: none\n---\n\n" + BASE
    code, hits = _edit(tmp_path, capsys, before, before.replace("Run the", "Start the"))
    assert code == 0 and hits == []


def test_an_unknown_ref_is_a_usage_error(tmp_path, capsys):
    """p3-r10: a bad ref is not "no version"."""
    root = _repo(tmp_path)
    page = _committed(root, "page.md", BASE)
    code = vws.main(["--default", "ste", "--preserve-from", "no-such-ref", str(page)])
    captured = capsys.readouterr()
    assert code == 2
    assert "no-such-ref" in captured.err
    assert "no version" not in captured.out


def test_an_old_version_that_is_not_utf8_is_a_usage_error(tmp_path, capsys):
    root = _repo(tmp_path)
    page = root / "page.md"
    page.write_bytes(b"# P\n\ncaf\xe9\n")
    _git(root, "add", "page.md")
    _git(root, "commit", "-q", "-m", "latin-1")
    page.write_text("# P\n\nText.\n", encoding="utf-8")
    code = vws.main(["--default", "ste", "--preserve-from", "HEAD", str(page)])
    captured = capsys.readouterr()
    assert code == 2 and "UTF-8" in captured.err


def test_setext_headings_get_slugs():
    """p3-r12."""
    text = "Set up the tool\n===============\n\nText.\n\nNext part\n---------\n"
    assert vws.heading_slugs(text) == {"set-up-the-tool", "next-part"}


def test_a_thematic_break_after_a_blank_line_is_no_heading():
    assert vws.heading_slugs("Text.\n\n---\n\nMore.\n") == set()


def test_an_anchor_move_to_a_setext_heading_is_accepted(tmp_path, capsys):
    before = "# P\n\nGo to [s](#old).\n\nOld\n---\n"
    after = "# P\n\nGo to [s](#new-name).\n\nNew name\n--------\n"
    _, hits = _edit(tmp_path, capsys, before, after)
    assert hits == []


def test_adjacent_fences_are_two_items():
    """p3-r12: a fence closes its block even with no prose after it."""
    text = "# P\n\n```\na\n```\n```\nb\n```\n"
    assert vws.preserved_items(text)["fenced code"] == {"```\na\n```": 1, "```\nb\n```": 1}


def test_a_root_relative_anchor_resolves_against_the_content_root(tmp_path, capsys):
    """p3-r7: a site-rooted link resolves under the nearest content/ directory."""
    root = _repo(tmp_path)
    (root / "content/posts/b").mkdir(parents=True)
    (root / "content/posts/b/index.md").write_text("# B\n\n## Usage\n", encoding="utf-8")
    before = "# P\n\nSee [x](/posts/b/#use).\n"
    page = _committed(root, "content/posts/a/index.md", before)
    page.write_text(before.replace("#use", "#usage"), encoding="utf-8")
    assert _run(page, capsys)[1] == []


def test_a_url_encoded_anchor_is_decoded(tmp_path, capsys):
    """p3-r7: an anchor written URL-encoded matches the heading's slug."""
    before = "# P\n\nGo to [s](#old).\n\n## Old\n"
    after = "# P\n\nGo to [s](#caf%C3%A9).\n\n## Café\n"
    _, hits = _edit(tmp_path, capsys, before, after)
    assert hits == []
