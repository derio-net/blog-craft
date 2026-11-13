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
    after = BASE.replace("Run the installer. It takes 3 minutes.",
                         "<!-- writing-standard: ignore preserve -- I want to -->\n"
                         "Run the installer. It takes 4 minutes.")
    code, hits = _edit(tmp_path, capsys, BASE, after)
    assert code == 1 and hits


@pytest.mark.parametrize("text", [BASE, ANCHORED, ""])
def test_preserved_items_is_a_pure_function_of_text(text):
    assert vws.preserved_items(text) == vws.preserved_items(text)
    assert set(vws.preserved_items(text)) == {"fenced code", "inline code", "link target", "numeral"}
