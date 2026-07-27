#!/usr/bin/env python3
"""Place a composed entry into a blog's prompts file, and read its conventions.

The seam blog-post-create.sh appends through. The shell composes the entry body
(it owns the v5 composition block); this places it and answers the one question
the file can answer about itself.

Two things the shell could not do safely:

  * `>> "$PROMPTS_YAML"` with a hard-coded `  - key:` corrupts every prompts file
    whose `images:` sequence sits at column 0 — valid YAML, and what `bootstrap`
    plus 88 hand-written entries produced in the reporting blog (#65 item 1). The
    indent is READ here, never assumed. Not by loading and re-dumping the
    document: `yaml.safe_dump` over a real ~1900-line entries file reflows every
    block scalar, re-quotes every string and reorders keys — the tradeoff
    migrate_prompts.py accepts for a one-shot migration and this must not (D1).
    Every byte above the insertion point stays as the operator wrote it.
  * Verify instead of trust (D2): the new bytes are written to a sibling temp
    file and `os.replace`d into place (atomic on POSIX), then re-READ FROM DISK
    and re-parsed, requiring the document to load with exactly one more entry
    carrying the expected key. Any failure restores the pre-append bytes and
    exits 2. That is what turns this whole class of append bug from silent into
    loud. The atomic swap is what makes the promise true rather than aspirational:
    `write_bytes` truncates first, so a short write (ENOSPC, quota,
    RLIMIT_FSIZE, SIGINT) used to leave the file truncated with the only copy of
    the original bytes in this process's memory.

Every file this module reads is read as UTF-8 explicitly. The entry block always
contains an em dash (blog-post-create.sh writes one into every `description:`),
so a locale-dependent read is not an edge case.

Usage:
  prompts_append.py append       --file <prompts.yaml> --key <key> --entry-file <block>
  prompts_append.py check        --file <prompts.yaml>
  prompts_append.py output-style --file <prompts.yaml> --site-prefix <site_dir>
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

AUTHORED_INDENT = 2   # the indent the caller composes the entry block at
DEFAULT_INDENT = 2    # empty sequence -> the templates/hugo-hextra bootstrap shape

_IMAGES_KEY = re.compile(r"^images\s*:")
_SEQ_ITEM = re.compile(r"^( *)-(?: |$)")


def load_entries(text: str) -> list:
    """The `images` sequence, or ValueError naming what is wrong with the file.

    `images:` with nothing under it is an empty sequence, not an error — that is
    the shape templates/hugo-hextra bootstraps and the shape the existing tests
    seed.
    """
    doc = yaml.safe_load(text)
    if doc is None:
        doc = {}
    if not isinstance(doc, dict):
        raise ValueError(f"top level is a {type(doc).__name__}, not a mapping")
    if "images" not in doc:
        raise ValueError("no top-level `images:` key")
    images = doc["images"]
    if images is None:
        return []
    if not isinstance(images, list):
        raise ValueError(f"`images:` is a {type(images).__name__}, not a sequence")
    return images


def sequence_indent(text: str, default: int = DEFAULT_INDENT) -> int:
    """Column of the first `- ` item under the top-level `images:` key.

    Both 0 and 2 are valid and real blogs use both, so the file's own convention
    is the only safe answer. Anything unrecognisable falls back to `default` —
    the verify step is what catches a wrong guess.
    """
    lines = text.splitlines()
    for n, line in enumerate(lines):
        if not _IMAGES_KEY.match(line):
            continue
        for candidate in lines[n + 1:]:
            if not candidate.strip() or candidate.lstrip().startswith("#"):
                continue
            m = _SEQ_ITEM.match(candidate)
            return len(m.group(1)) if m else default
        return default
    return default


def trailing_top_level_key(text: str) -> tuple[int, str] | None:
    """`(line number, name)` of the first top-level key AFTER `images:`, or None.

    The entry is placed at END OF FILE, which is only correct while `images:` is
    the last top-level key. Anything after it makes every append fail with
    `expected <block end>, but found '-'` — an error that reads as "the append
    broke your file" when the file's LAYOUT is what makes an end-of-file append
    wrong. Only `images:` is documented, so this is a hand-edited file: refusing
    up front with an accurate message is the honest answer, and moving the
    insertion point is not worth the risk to this code path (F7).
    """
    lines = text.splitlines()
    for n, line in enumerate(lines):
        if not _IMAGES_KEY.match(line):
            continue
        for number, candidate in enumerate(lines[n + 1:], start=n + 2):
            if not candidate.strip() or candidate[:1].isspace():
                continue                                  # blank, or nested below
            if candidate.startswith("#") or _SEQ_ITEM.match(candidate):
                continue                                  # comment, or a column-0 item
            return number, candidate.split(":", 1)[0].strip()
        return None
    return None


def reindent(block: str, indent: int) -> str:
    """Shift every line of the block by one uniform delta.

    Uniform is the whole point: a `scene: |` block scalar's content is only
    valid relative to its key, so per-line re-indentation would break it.
    """
    delta = indent - AUTHORED_INDENT
    if delta == 0:
        return block
    out = []
    for line in block.splitlines():
        if not line.strip():
            out.append("")
        elif delta > 0:
            out.append(" " * delta + line)
        else:
            head = line[:-delta]
            out.append(line[-delta:] if head.isspace() else line.lstrip())
    return "".join(f"{line}\n" for line in out)


def _fail(msg: str) -> int:
    print(f"prompts_append: {msg}", file=sys.stderr)
    return 2


def _write_atomically(path: Path, payload: bytes) -> None:
    """Give `path` exactly `payload`, or leave it exactly as it was.

    A sibling temp file in the SAME directory (`os.replace` is only atomic within
    one filesystem) plus `os.replace`. `Path.write_bytes` truncates and then
    writes, so a short write — ENOSPC, disk quota, RLIMIT_FSIZE, SIGINT, OOM —
    left the operator's entries file as a truncated prefix of itself, which is the
    one outcome this whole module exists to prevent (F1). Raw `os.write` in a loop
    rather than a buffered writer, so a short write surfaces here instead of from
    inside a `close()` the caller cannot see. The mode is copied off the original:
    mkstemp creates 0600 and a prompts file in a git repo is 0644. A symlinked
    prompts file is replaced through its realpath, so the link survives — plain
    `os.replace(tmp, path)` would turn the symlink into a regular file.
    """
    target = Path(os.path.realpath(path))
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent),
                                    prefix=f".{target.name}.", suffix=".tmp")
    try:
        try:
            os.fchmod(fd, os.stat(target).st_mode & 0o7777)
        except OSError:
            pass                      # a mode we could not copy is not a reason to fail
        view = memoryview(payload)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(tmp_name, target)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(tmp_name)       # gone already on the success path
        except OSError:
            pass


def _appendability_problem(path: Path, original: bytes) -> str | None:
    """Why an end-of-file append to these bytes would be unsafe, or None.

    Everything knowable BEFORE anything is written, so a caller can refuse before
    it creates anything (F3): blog-post-create.sh writes the page bundle first, and
    a refusal after that left a half-scaffolded post the operator had to know to
    delete.
    """
    try:
        text = original.decode("utf-8")
        load_entries(text)
    except (yaml.YAMLError, ValueError, UnicodeDecodeError) as exc:
        return (f"{path}: refusing to append, the file does not parse as it stands "
                f"— repair it first: {exc}")
    trailing = trailing_top_level_key(text)
    if trailing is not None:
        number, name = trailing
        return (f"{path}: refusing to append, `{name}` is a top-level key at line "
                f"{number}, after the `images:` sequence. The entry is placed at end of "
                f"file, so `images:` must be the last top-level key in the file — move "
                f"the trailing key(s) above `images:` (or add this entry by hand).")
    return None


def cmd_append(path: Path, key: str, entry_file: Path) -> int:
    try:
        original = path.read_bytes()
    except OSError as exc:
        return _fail(f"{path}: cannot be read: {exc}")
    problem = _appendability_problem(path, original)
    if problem is not None:
        return _fail(problem)
    text = original.decode("utf-8")
    before = load_entries(text)

    try:
        authored = entry_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # Always non-ASCII in practice — the composed `description:` carries an em
        # dash — so this read is explicitly UTF-8, never the locale's guess (F2).
        return _fail(f"{entry_file}: the entry block cannot be read as UTF-8: {exc}")
    block = reindent(authored, sequence_indent(text))
    # ENSURE a final newline at the seam: a prompts file that lost its own had its
    # last line fused with the first appended one. Trailing BLANK lines are left
    # alone — they are legal between sequence items, and in a `|+` kept block scalar
    # they are CONTENT that collapsing them would silently drop (p1-keep-chomp-seam).
    payload = ((text if text.endswith("\n") else text + "\n")
               + (block if block.endswith("\n") else block + "\n")).encode("utf-8")
    try:
        _write_atomically(path, payload)
    except OSError as exc:
        return _fail(f"{path}: the append could not be written ({exc}) — the file is "
                     f"unchanged, nothing was written in place")

    # D2 — verify, then keep. Re-read FROM DISK: verifying the in-memory string only
    # re-checks what this process already believes, and a short write would be
    # invisible to it. The restore path below is why this helper exists at all: the
    # old shell append never re-read what it wrote, so a corrupted file was
    # discovered by the next generate-images.py run, not by the scaffolder.
    try:
        written = path.read_bytes()
    except OSError as exc:
        return _restore(path, original, f"{path}: cannot be re-read after the append: {exc}")
    if written != payload:
        return _restore(path, original,
                        f"{path}: what is on disk is not what was written "
                        f"({len(written)} bytes, expected {len(payload)})")
    try:
        after = load_entries(written.decode("utf-8"))
    except (yaml.YAMLError, ValueError, UnicodeDecodeError) as exc:
        return _restore(path, original, f"{path}: the append broke the file: {exc}")
    if len(after) != len(before) + 1:
        return _restore(path, original, f"{path}: the append left {len(after)} entries, "
                                        f"expected {len(before) + 1}")
    last = after[-1]
    if not isinstance(last, dict) or last.get("key") != key:
        return _restore(path, original, f"{path}: the last entry is not the appended key "
                                        f"{key!r} (found {_key_of(last)!r})")
    return 0


def cmd_check(path: Path) -> int:
    """Exit 0 if an append would be accepted, 2 with the reason if it would not.

    Never writes anything. The whole point is ORDER: the scaffolder can ask this
    before it creates a page bundle, so a refused append leaves nothing half-built
    behind (F3). `append` re-runs the same checks itself — this is an early look,
    not a substitute for them.
    """
    try:
        original = path.read_bytes()
    except OSError as exc:
        return _fail(f"{path}: cannot be read: {exc}")
    problem = _appendability_problem(path, original)
    return 0 if problem is None else _fail(problem)


def cmd_output_style(path: Path, site_prefix: str) -> int:
    """Print `bundle` or `output_dir` — which cover convention this blog uses (D7).

    Covers inside the page bundle and covers in `image.output_dir` are both
    legitimate, and the file already states which one the blog picked, so the
    scaffolder reads it instead of hard-coding one. Never fails a scaffold: an
    unreadable file answers `output_dir`, today's behaviour, and the append step
    is where a broken file is reported.
    """
    prefix = site_prefix.rstrip("/")
    if prefix == ".":
        prefix = ""
    bundle_root = f"{prefix}/content/" if prefix else "content/"
    try:
        # encoding= is load-bearing: this `except` swallows UnicodeDecodeError (a
        # ValueError), so under a non-UTF-8 locale a real bundle-style blog answered
        # `output_dir` — the cover written where Hugo's page resources never look,
        # with no diagnostic at all. Every entry this scaffolder writes carries an
        # em dash, so that was not an edge case (F2).
        entries = load_entries(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, ValueError):
        print("output_dir")
        return 0
    outputs = [e["output"] for e in entries
               if isinstance(e, dict) and isinstance(e.get("output"), str)]
    bundled = sum(1 for o in outputs
                  if (o[2:] if o.startswith("./") else o).startswith(bundle_root))
    # Strictly more, so an exact tie (and no entries at all) keeps output_dir.
    print("bundle" if bundled > len(outputs) - bundled else "output_dir")
    return 0


def _key_of(entry) -> object:
    return entry.get("key") if isinstance(entry, dict) else entry


def _restore(path: Path, original: bytes, msg: str) -> int:
    """Put the pre-append bytes back, atomically, and say so — or say it failed.

    The restore is the promise the module makes (SKILL.md), so it cannot be the one
    write left unguarded: `original` lives only in this process's memory, and a
    restore that raised would take the message with it (F1).
    """
    try:
        _write_atomically(path, original)
    except OSError as exc:
        return _fail(f"{msg} — AND THE RESTORE FAILED ({exc}). {path} still holds the "
                     f"appended bytes and the pre-append content is no longer "
                     f"recoverable from this process; inspect the file before re-running")
    return _fail(f"{msg} — restored the pre-append bytes")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    app = sub.add_parser("append", help="append one composed entry to the images: sequence")
    app.add_argument("--file", required=True)
    app.add_argument("--key", required=True, help="the entry's key; verified after the write")
    app.add_argument("--entry-file", required=True, help="entry block, authored at 2-space indent")
    chk = sub.add_parser("check", help="exit 0 if an append would be accepted; never writes")
    chk.add_argument("--file", required=True)
    style = sub.add_parser("output-style", help="print bundle | output_dir (the blog's convention)")
    style.add_argument("--file", required=True)
    style.add_argument("--site-prefix", default="", help="site_dir with no trailing slash; \"\" at root")
    a = ap.parse_args(argv)
    if a.cmd == "append":
        return cmd_append(Path(a.file), a.key, Path(a.entry_file))
    if a.cmd == "check":
        return cmd_check(Path(a.file))
    return cmd_output_style(Path(a.file), a.site_prefix)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
