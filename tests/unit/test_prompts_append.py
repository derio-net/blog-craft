"""tools/prompts_append.py — indentation-detecting, verified append (spec D1/D2).

The scaffolder emitted `  - key: …` literally, which corrupts every prompts file
whose `images:` sequence sits at column 0 (#65 item 1). The fix reads the file's
OWN sequence indent and shifts the authored block onto it, leaving every byte
above the insertion point untouched — a load-and-dump round-trip would reflow all
~1900 lines of a real entries file instead (D1).
"""
import errno
import importlib.util
import os
import subprocess
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "prompts_append.py")

# Most cases drive the CLI, which is the contract. `_write_atomically`'s failure
# windows are not reachable through it (they need a syscall to misbehave), so the
# module is imported too — see the close-that-raises case below.
_SPEC = importlib.util.spec_from_file_location("prompts_append", TOOL)
prompts_append = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(prompts_append)

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


def _append(tmp_path, body: str, key: str = NEW_KEY, entry: str = ENTRY_BLOCK, env=None):
    """Run `append` over `body`; return (result, original text, resulting text)."""
    f = tmp_path / "prompt_for_images.yaml"
    f.write_text(body, encoding="utf-8")
    blk = tmp_path / "entry.txt"
    blk.write_text(entry, encoding="utf-8")
    r = subprocess.run([sys.executable, TOOL, "append", "--file", str(f),
                        "--key", key, "--entry-file", str(blk)],
                       capture_output=True, text=True,
                       env=None if env is None else dict(os.environ, **env))
    return r, body, f.read_text(encoding="utf-8")


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


def test_trailing_blank_lines_do_not_break_the_append(tmp_path):
    # Blank lines between sequence items are legal YAML, so they are left alone —
    # this is a no-regression guard, not evidence of normalisation.
    r, _, new = _append(tmp_path, _prompts(2) + "\n\n\n")
    assert r.returncode == 0, r.stderr
    assert len(_entries(new)) == 2, f"blank lines at the seam broke the append:\n{new}"


# A `|+` KEPT block scalar is the one shape where a trailing blank line is CONTENT
# (p1-keep-chomp-seam). The seam therefore only ENSURES a final newline; it must
# never collapse the ones already there, and D2's verification (count + last key)
# would not notice if it did.
KEPT_SCALAR = ("images:\n"
               "- key: existing-01\n"
               "  output: static/images/existing.png\n"
               "  composition:\n"
               "    scene: |+\n"
               "      an existing scene\n"
               "\n")


def test_a_kept_block_scalar_keeps_its_trailing_blank_line(tmp_path):
    r, orig, new = _append(tmp_path, KEPT_SCALAR)
    assert r.returncode == 0, r.stderr
    entries = _entries(new)
    assert len(entries) == 2, f"the append broke a |+ file:\n{new}"
    assert entries[0]["composition"]["scene"] == "an existing scene\n\n", \
        "a kept scalar's trailing blank line is content and must survive the seam"
    assert new.startswith(orig), "bytes above the insertion point were rewritten"


# ── Atomicity: a write that cannot complete may not damage the file (F1) ────────
#
# `path.write_bytes()` truncates before it writes, so a short write (ENOSPC, disk
# quota, RLIMIT_FSIZE, SIGINT) left the operator's ~1900-line entries file
# truncated — with the only copy of the original bytes in the dying process's
# memory. `ulimit -f` is the one deterministic way to provoke a real short write,
# so the reproduction from the review IS the test.

_ULIMIT_F = subprocess.run(["bash", "-c", "ulimit -f 2"],
                           capture_output=True).returncode == 0


def _big_prompts(entries: int = 40) -> str:
    """~4.8 kB of entries — comfortably over the 2048-byte RLIMIT_FSIZE below."""
    lines = ["images:"]
    for n in range(1, entries + 1):
        lines += [f"- key: existing-{n:02d}",
                  f"  output: static/images/existing-{n:02d}.png",
                  "  composition:", "    scene: |",
                  f"      an existing scene number {n}"]
    return "\n".join(lines) + "\n"


@pytest.mark.skipif(not _ULIMIT_F, reason="`ulimit -f` is unavailable on this platform")
def test_a_write_that_cannot_complete_leaves_the_file_byte_identical(tmp_path):
    f = tmp_path / "prompt_for_images.yaml"
    original = _big_prompts().encode()
    f.write_bytes(original)
    blk = tmp_path / "entry.txt"
    blk.write_text(ENTRY_BLOCK, encoding="utf-8")
    # -B so the child never writes bytecode caches under the same size limit.
    r = subprocess.run(
        ["bash", "-c", 'ulimit -f 2; exec "$0" -B "$@"', sys.executable, TOOL,
         "append", "--file", str(f), "--key", NEW_KEY, "--entry-file", str(blk)],
        capture_output=True, text=True)
    assert f.read_bytes() == original, \
        "a failed write truncated the operator's file — the exact bug this module exists to prevent"
    assert r.returncode == 2, f"a failed write must exit 2, not {r.returncode}: {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"a failed write must report, not traceback: {r.stderr!r}"
    assert "prompt_for_images.yaml" in r.stderr
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")], \
        "the temp file must be cleaned up on the failure path"


def test_a_healthy_append_leaves_no_temp_file_behind(tmp_path):
    r, _, _ = _append(tmp_path, _prompts(0))
    assert r.returncode == 0, r.stderr
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


# A `close()` that raises (EIO/ENOSPC on close — plausible on NFS) used to leave the
# fd non-negative, so the `finally` closed it a SECOND time: the resulting
# `OSError: [Errno 9] Bad file descriptor` propagated out OF the finally, skipping
# the `os.unlink`. An untracked `.prompt_for_images.yaml.XXXX.tmp` was left beside
# the operator's file (`*.tmp` is not gitignored here) and the real errno was masked
# by a bogus EBADF (V3). Not reachable through the CLI — it needs a syscall to
# misbehave — so this drives `_write_atomically` in a child interpreter, which keeps
# the patched `os.close` out of the test process.
_CLOSE_RAISES = r'''
import errno, importlib.util, os, pathlib, sys
spec = importlib.util.spec_from_file_location("prompts_append", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
real, seen = os.close, []
def failing(fd):
    seen.append(fd)
    real(fd)              # close(2) closes the fd even when it reports an error
    if len(seen) == 1:
        raise OSError(errno.EIO, "simulated I/O error on close")
os.close = failing
try:
    m._write_atomically(pathlib.Path(sys.argv[2]), b"images: []\n")
except OSError as exc:
    os.close = real
    print(exc.errno)
else:
    os.close = real
    print("no error")
'''


def test_a_close_that_raises_still_unlinks_the_temp_file_and_keeps_the_errno(tmp_path):
    f = tmp_path / "prompt_for_images.yaml"
    f.write_text(_prompts(0), encoding="utf-8")
    r = subprocess.run([sys.executable, "-c", _CLOSE_RAISES, TOOL, str(f)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(errno.EIO), \
        f"the real errno must reach the caller, not EBADF from a double close: {r.stdout!r}"
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")], \
        "the temp file must be unlinked even when close() raises"
    assert f.read_text(encoding="utf-8") == _prompts(0), \
        "a write that never reached os.replace must leave the target alone"


# ── A RecursionError is a file problem, not a crash (V4) ────────────────────────
#
# `load_entries` caught only (YAMLError, ValueError, UnicodeDecodeError), so a
# deeply nested document made PyYAML raise RecursionError and all three subcommands
# exited 1 with a traceback — falsifying `output-style`'s promise never to fail a
# scaffold ("an unreadable file answers output_dir"). Adversarial input only, no data
# loss, but the answer is the same as for any unreadable file.
#
# Two shapes, because they fail in different places. 2000 nested BLOCK sequences
# tokenise instantly and every reader (compose, safe_load) then blows the stack, so
# it is the fixture that actually reaches the RecursionError handling. The reported
# input — `images: ` + 60000 `[` — never closes its brackets, so the event stream
# raises ParserError first (also refused, also no traceback); it is used only where
# it is cheap, since building 60000 nested parser states takes ~40 s.
DEEPLY_NESTED = "images:\n" + "- " * 2000 + "x\n"
UNCLOSED_FLOW = "images: " + "[" * 60000 + "\n"


def test_a_deeply_nested_document_is_refused_without_a_traceback(tmp_path):
    r, orig, new = _append(tmp_path, DEEPLY_NESTED)
    assert r.returncode == 2, f"expected the refusal exit code, got {r.returncode}: {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"an unreadable file must report, not crash: {r.stderr!r}"
    assert new == orig, "the file must not be touched"
    assert "prompt_for_images.yaml" in r.stderr


def test_check_refuses_a_deeply_nested_document_without_a_traceback(tmp_path):
    r, after = _check(tmp_path, DEEPLY_NESTED)
    assert r.returncode == 2, r.stderr
    assert "Traceback" not in r.stderr, f"an unreadable file must report, not crash: {r.stderr!r}"
    assert after == DEEPLY_NESTED


@pytest.mark.parametrize("body", [DEEPLY_NESTED, UNCLOSED_FLOW])
def test_output_style_never_fails_on_an_unreadable_document(tmp_path, body):
    r = _style(tmp_path, body)
    assert r.returncode == 0, f"output-style must never fail a scaffold: {r.stderr!r}"
    assert r.stdout.strip() == "output_dir"


# ── Encoding: the entry block is ALWAYS non-ASCII (F2) ─────────────────────────
#
# blog-post-create.sh writes a literal em dash into every entry's `description:`,
# so a locale-dependent read is not an edge case — it is every scaffold under a
# non-UTF-8 locale. PYTHONCOERCECLOCALE=0 defeats PEP 538 coercion, PYTHONUTF8=0
# defeats PEP 540, so `LC_ALL=C` really means ASCII here.
C_LOCALE = {"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}

EM_DASH_ENTRY = (f"  - key: {NEW_KEY}\n"
                 "    output: static/images/operating-30-cover.png\n"
                 '    description: "Cover for operating post 30 — Silent Failure"\n')


def test_a_non_ascii_entry_block_appends_under_a_c_locale(tmp_path):
    r, orig, new = _append(tmp_path, _prompts(0), entry=EM_DASH_ENTRY, env=C_LOCALE)
    assert r.returncode == 0, f"the em dash every entry carries must not depend on $LC_ALL: {r.stderr!r}"
    entries = _entries(new)
    assert len(entries) == 2
    assert entries[-1]["description"].endswith("— Silent Failure")
    assert new.startswith(orig)


# ── `images:` must be the last top-level key (F7) ──────────────────────────────
#
# The entry is placed at END OF FILE, so a top-level key AFTER the sequence turns
# every scaffold into `expected <block end>, but found '-'` — an error that blames
# the append for the file's layout. Only `images:` is documented, so this is a
# hand-edited file, and the honest answer is to refuse UP FRONT and say why.
TRAILING_TOP_LEVEL_KEY = _prompts(0) + "settings:\n  quality: high\n"


def test_a_top_level_key_after_the_sequence_is_refused_with_an_accurate_message(tmp_path):
    r, orig, new = _append(tmp_path, TRAILING_TOP_LEVEL_KEY)
    assert r.returncode == 2
    assert new == orig, "the file must not be touched"
    assert "settings" in r.stderr, f"stderr must name the offending key: {r.stderr!r}"
    assert "last" in r.stderr, \
        f"stderr must say `images:` has to be the last top-level key, not blame the append: {r.stderr!r}"
    assert "broke the file" not in r.stderr, \
        f"the append did not break anything — the layout did: {r.stderr!r}"


def test_a_top_level_key_before_the_sequence_is_fine(tmp_path):
    body = "version: 5\n" + _prompts(0)
    r, orig, new = _append(tmp_path, body)
    assert r.returncode == 0, r.stderr
    assert len(_entries(new)) == 2
    assert new.startswith(orig)


def test_a_comment_after_the_sequence_is_fine(tmp_path):
    # A trailing comment column is not a top-level key and must not be refused.
    body = _prompts(0) + "# end of entries\n"
    r, orig, new = _append(tmp_path, body)
    assert r.returncode == 0, r.stderr
    assert len(_entries(new)) == 2


# ── …asked of the PARSER, not of the columns (V1) ───────────────────────────────
#
# The first cut scanned lines and assumed "column-0 content cannot occur inside the
# `images:` sequence". That premise is FALSE: a multi-line flow collection and a
# hand-wrapped quoted scalar both legally continue at column 0. Every file below is
# valid YAML (PyYAML parses it, and a plain end-of-file append works on it) and was
# refused — `refusing to append, `two]` is a top-level key at line 5` — which killed
# every scaffold on such a blog. A hand-wrapped `description:` in an entries file is
# entirely ordinary, so the heuristic was worse than the rare layout it diagnosed.

COLUMN_ZERO_CONTINUATIONS = {
    "a flow sequence wrapped at column 0":
        "images:\n- key: a\n  output: x.png\n  tags: [one,\ntwo]\n",
    "a double-quoted scalar wrapped at column 0":
        'images:\n- key: a\n  output: x.png\n'
        '  description: "a long cover description that the\noperator wrapped by hand"\n',
    "a flow mapping wrapped at column 0":
        "images:\n- key: a\n  output: x.png\n  meta: {p: 1,\nq: 2}\n",
    "a single-quoted scalar wrapped at column 0":
        "images:\n- key: a\n  output: x.png\n  note: 'hello\nworld'\n",
}


@pytest.mark.parametrize("name,body", sorted(COLUMN_ZERO_CONTINUATIONS.items()))
def test_column_zero_continuations_are_not_trailing_keys(tmp_path, name, body):
    assert yaml.safe_load(body)["images"], f"{name}: the fixture must be VALID to begin with"
    chk = tmp_path / "chk"
    chk.mkdir()
    assert _check(chk, body)[0].returncode == 0, f"{name}: check refused a valid file"
    app = tmp_path / "app"
    app.mkdir()
    r, orig, new = _append(app, body)
    assert r.returncode == 0, f"{name}: append refused a valid file: {r.stderr!r}"
    assert len(_entries(new)) == 2, f"{name} did not round-trip:\n{new}"
    assert _entries(new)[-1]["key"] == NEW_KEY
    assert new.startswith(orig)


# `---` and `...` at column 0 are refused too — an end-of-file append into a
# multi-document stream is not correct either — but they are not "a top-level key
# named `...`", which is what the line scanner called them.

def test_an_explicit_document_end_marker_is_named_for_what_it_is(tmp_path):
    r, orig, new = _append(tmp_path, _prompts(0) + "...\n")
    assert r.returncode == 2
    assert new == orig, "the file must not be touched"
    assert "document" in r.stderr, \
        f"stderr must name the document-end marker: {r.stderr!r}"
    assert "top-level key" not in r.stderr, \
        f"`...` is a document-end marker, not a top-level key: {r.stderr!r}"


def test_a_multi_document_stream_is_named_for_what_it_is(tmp_path):
    r, orig, new = _append(tmp_path, _prompts(0) + "---\nsettings:\n  quality: high\n")
    assert r.returncode == 2
    assert new == orig, "the file must not be touched"
    assert "document" in r.stderr, f"stderr must say the file holds two documents: {r.stderr!r}"
    assert "top-level key" not in r.stderr, \
        f"`---` is a document separator, not a top-level key: {r.stderr!r}"


# ── `check`: refuse BEFORE the caller writes anything (F3) ─────────────────────
#
# blog-post-create.sh writes the page bundle before it appends, so an append that
# is going to be refused has to be knowable first — otherwise a refusal leaves a
# half-scaffolded post the operator has to know to delete.

def _check(tmp_path, body: str):
    f = tmp_path / "prompt_for_images.yaml"
    f.write_text(body, encoding="utf-8")
    r = subprocess.run([sys.executable, TOOL, "check", "--file", str(f)],
                       capture_output=True, text=True)
    return r, f.read_text(encoding="utf-8")


def test_check_accepts_an_appendable_file(tmp_path):
    r, after = _check(tmp_path, _prompts(0))
    assert r.returncode == 0, r.stderr
    assert after == _prompts(0), "check must never write"


def test_check_accepts_an_empty_sequence(tmp_path):
    assert _check(tmp_path, "images:\n")[0].returncode == 0


def test_check_refuses_the_same_files_append_refuses(tmp_path):
    for n, body in enumerate((BROKEN, "images:\n  existing-01:\n    output: x.png\n",
                              "other:\n- key: k\n", TRAILING_TOP_LEVEL_KEY)):
        case = tmp_path / f"case{n}"
        case.mkdir()
        r, after = _check(case, body)
        assert r.returncode == 2, f"case {n} must be refused: {r.stdout!r}"
        assert "prompt_for_images.yaml" in r.stderr, \
            f"case {n} must be refused BY check, naming the file — not by argparse: {r.stderr!r}"
        assert after == body, f"case {n}: check must never write"


# ── `check` and `append` are ONE code path, by construction (V2) ────────────────
#
# Sharing the refusal PREDICATES was not enough. `append` additionally resolved the
# insertion indent and verified the resulting parse; `check` modelled neither, so
# these five files passed `check` and were then refused by `append` — with
# content/docs/<series>/<NN>-<slug>/index.md already on disk, which is the whole
# hole `check` exists to close. `check` now performs the ENTIRE append in memory
# (read, resolve indent, re-indent, concatenate, parse, verify) and simply does not
# write, so the two cannot drift apart again.

FLOW_EMPTY = "images: []\n"
FLOW_ITEM = "images: [{key: a, output: static/images/a.png}]\n"
FLOW_SPACED = "images: [ ]\n"
# A quoted key is the same key: `^images\s*:` did not match it, so the indent fell
# back to 2 and the appended `  - key:` was invalid under a column-0 sequence.
QUOTED_KEY = '"images":\n- key: a\n  output: static/images/a.png\n'
SINGLE_QUOTED_KEY = "'images':\n- key: a\n  output: static/images/a.png\n"
DIVERGED = [FLOW_EMPTY, FLOW_ITEM, QUOTED_KEY, SINGLE_QUOTED_KEY, FLOW_SPACED]


@pytest.mark.parametrize("body", DIVERGED)
def test_check_answers_exactly_what_append_would_do(tmp_path, body):
    chk = tmp_path / "chk"
    chk.mkdir()
    c, after = _check(chk, body)
    app = tmp_path / "app"
    app.mkdir()
    r, orig, new = _append(app, body)
    assert c.returncode == r.returncode, (
        f"check said {c.returncode} and append said {r.returncode} for {body!r} — the "
        f"divergence that leaves a half-scaffolded post behind.\n"
        f"check: {c.stderr!r}\nappend: {r.stderr!r}")
    assert after == body, "check must never write"
    if r.returncode != 0:
        assert new == orig, "a refused append must leave the file byte-identical"


@pytest.mark.parametrize("body", [FLOW_EMPTY, FLOW_ITEM, FLOW_SPACED])
def test_a_flow_style_images_value_is_refused_with_an_accurate_message(tmp_path, body):
    # A flow sequence cannot be extended by appending a block item at end of file, so
    # this is refused UP FRONT rather than discovered by the post-write parse.
    r, orig, new = _append(tmp_path, body)
    assert r.returncode == 2
    assert new == orig
    assert "flow" in r.stderr.lower(), \
        f"stderr must name the flow-style value, not blame the append: {r.stderr!r}"
    assert "broke the file" not in r.stderr, \
        f"the append did not break anything — the layout did: {r.stderr!r}"


@pytest.mark.parametrize("body", [QUOTED_KEY, SINGLE_QUOTED_KEY])
def test_a_quoted_images_key_appends_at_the_files_own_indent(tmp_path, body):
    # `"images":` is the same key as `images:`; the sequence under it is at column 0
    # and that — not the fallback of 2 — is where the entry belongs.
    r, orig, new = _append(tmp_path, body)
    assert r.returncode == 0, r.stderr
    assert len(_entries(new)) == 2, f"a quoted key must not change where the entry goes:\n{new}"
    assert new.startswith(orig)
    assert f"\n- key: {NEW_KEY}" in new, f"the entry must land at column 0:\n{new}"


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

def _style(tmp_path, body: str, site_prefix: str = "blog", env=None):
    f = tmp_path / "prompt_for_images.yaml"
    f.write_text(body, encoding="utf-8")
    r = subprocess.run([sys.executable, TOOL, "output-style", "--file", str(f),
                        "--site-prefix", site_prefix],
                       capture_output=True, text=True,
                       env=None if env is None else dict(os.environ, **env))
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


def test_detection_is_not_locale_dependent(tmp_path):
    # The silent half of F2: a locale-dependent read raised UnicodeDecodeError,
    # which `except ... ValueError` swallowed, so a real bundle-style blog got
    # `output_dir` — the cover written where Hugo's page resources never look, with
    # no diagnostic at all. Every entry this scaffolder writes carries an em dash.
    body = ("images:\n"
            "- key: existing-01\n"
            "  output: content/docs/operating/29-x/cover.png\n"
            '  description: "Cover for operating post 29 — Prior Post"\n')
    r = _style(tmp_path, body, site_prefix="", env=C_LOCALE)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "bundle", \
        "a non-ASCII entries file must not silently answer output_dir under $LC_ALL=C"
