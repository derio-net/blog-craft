"""tools/prompts_append.py — indentation-detecting, verified append (spec D1/D2).

The scaffolder emitted `  - key: …` literally, which corrupts every prompts file
whose `images:` sequence sits at column 0 (#65 item 1). The fix reads the file's
OWN sequence indent and shifts the authored block onto it, leaving every byte
above the insertion point untouched — a load-and-dump round-trip would reflow all
~1900 lines of a real entries file instead (D1).
"""
import os
import subprocess
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "prompts_append.py")

# The shell composes the entry block at a 2-space indent; the helper re-indents it
# onto whatever the target file uses. The scene deliberately carries a deeper line
# so a re-indent that rewrites per-line leading whitespace shows up as a diff.
NEW_KEY = "operating-30"
ENTRY_BLOCK = (
    f"  - key: {NEW_KEY}\n"
    "    output: static/images/operating-30-cover.png\n"
    "    composition:\n"
    "      scene: |\n"
    "        line one\n"
    "          indented line\n"
    "        line three\n"
)
NEW_SCENE = "line one\n  indented line\nline three\n"


def _prompts(indent: int) -> str:
    """An entries file with one existing v5 entry at `indent` columns."""
    i = " " * indent
    return ("images:\n"
            f"{i}- key: existing-01\n"
            f"{i}  output: static/images/existing.png\n"
            f"{i}  composition:\n"
            f"{i}    scene: |\n"
            f"{i}      an existing scene\n")


def _append(tmp_path, body: str, key: str = NEW_KEY, entry: str = ENTRY_BLOCK):
    """Run `append` over `body`; return (result, original text, resulting text)."""
    f = tmp_path / "prompt_for_images.yaml"
    f.write_text(body)
    blk = tmp_path / "entry.txt"
    blk.write_text(entry)
    r = subprocess.run([sys.executable, TOOL, "append", "--file", str(f),
                        "--key", key, "--entry-file", str(blk)],
                       capture_output=True, text=True)
    return r, body, f.read_text()


def _entries(text):
    return (yaml.safe_load(text) or {}).get("images")


@pytest.mark.parametrize("indent", [0, 2, 4])
def test_append_matches_the_files_own_sequence_indent(tmp_path, indent):
    r, orig, new = _append(tmp_path, _prompts(indent))
    assert r.returncode == 0, r.stderr
    entries = _entries(new)
    assert len(entries) == 2, f"indent {indent} did not round-trip:\n{new}"
    assert entries[-1]["key"] == NEW_KEY
    assert entries[-1]["composition"]["scene"] == NEW_SCENE
    assert new.startswith(orig), "bytes above the insertion point were rewritten"


def test_empty_sequence_defaults_to_two(tmp_path):
    r, orig, new = _append(tmp_path, "images:\n")
    assert r.returncode == 0, r.stderr
    entries = _entries(new)
    assert len(entries) == 1
    assert entries[0]["key"] == NEW_KEY
    assert entries[0]["composition"]["scene"] == NEW_SCENE
    assert new.startswith(orig)


# ── Seam hygiene and verify-after-write (D2) ────────────────────────────────────

def test_missing_trailing_newline_is_not_fused(tmp_path):
    r, _, new = _append(tmp_path, _prompts(0).rstrip("\n"))
    assert r.returncode == 0, r.stderr
    assert len(_entries(new)) == 2, f"the seam fused two lines:\n{new}"


def test_trailing_blank_lines_are_normalised(tmp_path):
    r, _, new = _append(tmp_path, _prompts(2) + "\n\n\n")
    assert r.returncode == 0, r.stderr
    assert len(_entries(new)) == 2, f"blank lines at the seam broke the append:\n{new}"


# The reported corruption (#65 §1): a nested `- ` inside the previous entry's
# composition block. A helper that appends to this without looking would bury the
# operator's real problem one entry deeper.
BROKEN = ("images:\n"
          "- key: existing-01\n"
          "  output: static/images/existing.png\n"
          "  composition:\n"
          "    scene: |\n"
          "      a scene\n"
          "  - key: operating-30\n"
          "    output: static/images/operating-30-cover.png\n")


def test_already_broken_file_is_refused_and_untouched(tmp_path):
    r, orig, new = _append(tmp_path, BROKEN)
    assert r.returncode != 0
    assert new == orig, "a broken file must not be written to"
    assert "prompt_for_images.yaml" in r.stderr
    assert "line" in r.stderr, f"stderr does not name the parse error: {r.stderr!r}"


def test_images_mapping_is_refused_and_untouched(tmp_path):
    body = "images:\n  existing-01:\n    output: static/images/existing.png\n"
    r, orig, new = _append(tmp_path, body)
    assert r.returncode != 0
    assert new == orig
    assert r.stderr.strip()


def test_missing_images_key_is_refused_and_untouched(tmp_path):
    r, orig, new = _append(tmp_path, "other:\n- key: k\n")
    assert r.returncode != 0
    assert new == orig
    assert "images" in r.stderr


def test_key_mismatch_restores_the_original_bytes(tmp_path):
    # The verification is on the KEY, not just the count: an entry block whose key
    # does not match what the caller says it appended means the two disagree about
    # what was written, which is exactly the state D2 refuses to leave on disk.
    r, orig, new = _append(tmp_path, _prompts(0), key="not-the-appended-key")
    assert r.returncode == 2
    assert new == orig, "a failed verification must restore the pre-append bytes"
    assert "not-the-appended-key" in r.stderr


# ── output-style: read the blog's cover convention off the file (D7) ────────────

def _style(tmp_path, body: str, site_prefix: str = "blog"):
    f = tmp_path / "prompt_for_images.yaml"
    f.write_text(body)
    r = subprocess.run([sys.executable, TOOL, "output-style", "--file", str(f),
                        "--site-prefix", site_prefix],
                       capture_output=True, text=True)
    return r


def _with_outputs(*outputs: str) -> str:
    lines = ["images:"]
    for n, out in enumerate(outputs, start=1):
        lines.append(f"- key: existing-{n:02d}")
        if out:
            lines.append(f"  output: {out}")
    return "\n".join(lines) + "\n"


BUNDLE = "blog/content/docs/operating/29-x/cover.png"
STATIC = "blog/static/images/operating-29-cover.png"


def test_bundle_shaped_entries_win(tmp_path):
    r = _style(tmp_path, _with_outputs(BUNDLE, BUNDLE, STATIC))
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "bundle"


def test_output_dir_shaped_entries_win(tmp_path):
    r = _style(tmp_path, _with_outputs(BUNDLE, STATIC, STATIC))
    assert r.stdout.strip() == "output_dir"


def test_a_tie_falls_to_output_dir(tmp_path):
    # The conservative side: output_dir is today's behaviour, so a file that does
    # not clearly state a convention keeps it.
    r = _style(tmp_path, _with_outputs(BUNDLE, STATIC))
    assert r.stdout.strip() == "output_dir"


def test_no_entries_is_output_dir(tmp_path):
    assert _style(tmp_path, "images:\n").stdout.strip() == "output_dir"


def test_entries_without_output_are_output_dir(tmp_path):
    r = _style(tmp_path, _with_outputs("", ""))
    assert r.stdout.strip() == "output_dir"


def test_empty_site_prefix_still_recognises_content(tmp_path):
    # site_dir "." — the blog IS the repo root, so the bundle path has no prefix.
    r = _style(tmp_path, _with_outputs("content/docs/operating/29-x/cover.png"),
               site_prefix="")
    assert r.stdout.strip() == "bundle"


def test_unparseable_file_never_breaks_detection(tmp_path):
    # Detection must not be a second place a broken file can stop a scaffold; the
    # append step is where it is caught, loudly.
    r = _style(tmp_path, BROKEN)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "output_dir"
