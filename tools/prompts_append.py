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

Every question about the file's SHAPE is asked of PyYAML's own parse — never of
the columns. `yaml.compose()` knows that `"images":` is the key `images`, that a
`tags: [one,\ntwo]` continuation line at column 0 is inside the sequence, and that
`images: []` is a flow collection nothing can be appended to; a line scanner knows
none of that and refused ordinary hand-wrapped files (V1).

`check` runs the WHOLE append in memory — read, resolve the indent, re-indent,
concatenate, parse, verify — and simply does not write. Sharing only the refusal
predicates was not enough: `check` used to model neither the indent resolution nor
the verification, so files it accepted were then refused by `append`, after the
caller had created the page bundle `check` exists to protect (V2).

Every file this module reads is read as UTF-8 explicitly. The entry block always
contains an em dash (blog-post-create.sh writes one into every `description:`),
so a locale-dependent read is not an edge case.

What `os.replace` changes (accepted, recorded rather than fixed):
  * a `chmod 444` prompts file is now modified successfully — the old in-place
    write was refused by the mode. Directory write permission is what governs a
    rename, so a read-only FILE no longer protects itself.
  * the mirror image: a writable file in a read-only DIRECTORY now fails where an
    in-place write succeeded. It fails safely — the file is left byte-identical.
  * hardlinks break. `os.replace` swings the directory entry, so any other link to
    the old inode keeps the pre-append bytes instead of seeing the new entry.
  * the rename is not crash-durable: the temp file is fsynced, the DIRECTORY is
    not, so a power loss between the rename and the filesystem's own commit can
    lose the swap. It cannot lose the original — that is the property this exists
    for.

Usage:
  prompts_append.py append       --file <prompts.yaml> --key <key> --entry-file <block>
  prompts_append.py check        --file <prompts.yaml> [--key <key> --entry-file <block>]
  prompts_append.py output-style --file <prompts.yaml> --site-prefix <site_dir>
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

import yaml

AUTHORED_INDENT = 2   # the indent the caller composes the entry block at
DEFAULT_INDENT = 2    # empty sequence -> the templates/hugo-hextra bootstrap shape

# `check` without an entry block still has to exercise the indent/concatenate/parse
# path, so it appends THIS in memory instead. blog-post-create.sh passes the real
# block (it composes it before it writes the bundle), which is strictly better —
# this is the fallback for a caller that only has the file.
PREFLIGHT_KEY = "prompts-append-preflight"
PREFLIGHT_ENTRY = (f"  - key: {PREFLIGHT_KEY}\n"
                   f"    output: static/images/{PREFLIGHT_KEY}.png\n")

class Refused(Exception):
    """An append this module will not perform, carrying the message to print."""


class Plan(NamedTuple):
    """A prepared append: the bytes to write, and what to verify afterwards.

    `check` builds one and stops; `append` builds one and writes `payload`. There
    is no second code path (V2).
    """
    original: bytes
    payload: bytes
    before: int
    key: str


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


def _images_node(text: str):
    """The value node of the top-level `images` key, or None.

    The parser's own structure, so a quoted key is the same key and a comment is a
    comment. The LAST `images` key wins, matching what `yaml.safe_load` returns for
    a document that (illegally, but parseably) repeats it.
    """
    try:
        root = yaml.compose(text)
    except (yaml.YAMLError, RecursionError):
        return None
    if not isinstance(root, yaml.MappingNode):
        return None
    found = None
    for key, value in root.value:
        if isinstance(key, yaml.ScalarNode) and key.value == "images":
            found = value
    return found


def sequence_indent(text: str, default: int = DEFAULT_INDENT) -> int:
    """Column of the first `- ` item under the top-level `images:` key.

    Both 0 and 2 are valid and real blogs use both, so the file's own convention
    is the only safe answer. Read off the parsed node's start mark rather than a
    regex over lines: `^images\\s*:` did not match `"images":`, fell back to 2, and
    put an invalid `  - key:` under a column-0 sequence — accepted by `check` and
    then refused by `append` (V2). Anything unrecognisable falls back to `default`;
    the verify step is what catches a wrong guess.
    """
    node = _images_node(text)
    if isinstance(node, yaml.SequenceNode) and not node.flow_style and node.value:
        return node.start_mark.column
    return default


def append_shape_problem(text: str) -> str | None:
    """Why this document's STRUCTURE makes an end-of-file append wrong, or None.

    The entry is placed at END OF FILE, which is correct only while the file is one
    document, `images:` is its last top-level key, and that key's value is a block
    sequence. Anything else makes every append fail with `expected <block end>, but
    found '-'` — an error that reads as "the append broke your file" when the file's
    LAYOUT is what makes an end-of-file append wrong. Only `images:` is documented,
    so this is a hand-edited file: refusing up front with an accurate message is the
    honest answer, and moving the insertion point is not worth the risk to this code
    path (F7).

    Asked of the parser, never of the columns. The first cut scanned lines on the
    premise that "column-0 content cannot occur inside the sequence", which is
    false — a multi-line flow collection and a hand-wrapped quoted scalar both
    legally continue at column 0, so `tags: [one,\\ntwo]` and an operator's
    hand-wrapped `description:` were refused as top-level keys, killing every
    scaffold on such a blog (V1).

    Raises yaml.YAMLError / RecursionError for a file that does not parse: it has no
    structure to inspect, and the caller reports that as its own refusal.
    """
    events = list(yaml.parse(text))
    documents = sum(1 for e in events if isinstance(e, yaml.DocumentStartEvent))
    if documents > 1:
        return (f"the file holds {documents} YAML documents. An entry placed at end of "
                f"file lands in the LAST document, not in the `images:` sequence — keep "
                f"the entries in a single document.")
    end = next((e for e in events
                if isinstance(e, yaml.DocumentEndEvent) and e.explicit), None)
    if end is not None:
        return (f"the file closes its document explicitly with `...` at line "
                f"{end.start_mark.line + 1}. An entry placed at end of file would start a "
                f"SECOND document instead of extending the `images:` sequence — remove "
                f"the `...` marker.")
    root = yaml.compose(text)
    if not isinstance(root, yaml.MappingNode):
        return None                    # load_entries names what is wrong with the shape
    keys = [key for key, _ in root.value]
    last = max((n for n, key in enumerate(keys)
                if isinstance(key, yaml.ScalarNode) and key.value == "images"),
               default=None)
    if last is None:
        return None                    # ditto — "no top-level `images:` key"
    if last != len(keys) - 1:
        after = keys[last + 1]
        name = after.value if isinstance(after, yaml.ScalarNode) else "?"
        return (f"`{name}` is a top-level key at line {after.start_mark.line + 1}, after "
                f"the `images:` sequence. The entry is placed at end of file, so `images:` "
                f"must be the last top-level key in the file — move the trailing key(s) "
                f"above `images:` (or add this entry by hand).")
    value = root.value[last][1]
    if isinstance(value, (yaml.SequenceNode, yaml.MappingNode)) and value.flow_style:
        return (f"`images:` is written in FLOW style (`[...]`) at line "
                f"{value.start_mark.line + 1}. A flow collection cannot be extended by "
                f"appending a block entry at end of file — rewrite it as a block sequence "
                f"(one `- key:` per line) first.")
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


def compose_payload(text: str, authored: str) -> bytes:
    """The exact bytes an append would put on disk. The one definition of that.

    `check` and `append` both go through here, which is what makes them the same
    code path by construction (V2).
    """
    block = reindent(authored, sequence_indent(text))
    # ENSURE a final newline at the seam: a prompts file that lost its own had its
    # last line fused with the first appended one. Trailing BLANK lines are left
    # alone — they are legal between sequence items, and in a `|+` kept block scalar
    # they are CONTENT that collapsing them would silently drop (p1-keep-chomp-seam).
    return ((text if text.endswith("\n") else text + "\n")
            + (block if block.endswith("\n") else block + "\n")).encode("utf-8")


def verification_problem(text: str, before: int, key: str) -> str | None:
    """Why the post-append document is not what was asked for, or None (D2).

    Over TEXT, so `check` can run it on a payload that is never written and
    `append` can run it again on the bytes it read back from disk.
    """
    try:
        after = load_entries(text)
    except (yaml.YAMLError, ValueError, UnicodeDecodeError, RecursionError) as exc:
        return f"the appended entry does not parse: {exc}"
    if len(after) != before + 1:
        return f"the append leaves {len(after)} entries, expected {before + 1}"
    last = after[-1]
    if not isinstance(last, dict) or last.get("key") != key:
        return f"the last entry is not the appended key {key!r} (found {_key_of(last)!r})"
    return None


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

    The cleanup never depends on the success path having run: a `close()` that
    raises (EIO/ENOSPC on close, plausible on NFS) used to leave `fd` non-negative,
    so the `finally` closed it again and the resulting EBADF propagated out OF the
    finally — masking the real errno and skipping the `os.unlink`, which left an
    untracked `.<name>.XXXX.tmp` beside the operator's file (V3).
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
            try:
                os.close(fd)          # already closed if the try got that far
            except OSError:
                pass                  # never the error the caller needs to see
        try:
            os.unlink(tmp_name)       # gone already on the success path
        except OSError:
            pass


def prepare(path: Path, key: str | None, entry_file: Path | None) -> Plan:
    """The whole append except the write, or Refused with the reason.

    Everything knowable BEFORE anything is written, so a caller can refuse before it
    creates anything (F3): blog-post-create.sh writes the page bundle first, and a
    refusal after that left a half-scaffolded post the operator had to know to
    delete. "Everything" now means the indent resolution and the parse verification
    too, not just the refusal predicates — modelling less than the real append is
    how `check` came to pass files `append` then refused (V2).
    """
    try:
        original = path.read_bytes()
    except OSError as exc:
        raise Refused(f"{path}: cannot be read: {exc}") from exc
    try:
        text = original.decode("utf-8")
        shape = append_shape_problem(text)
        if shape is not None:
            raise Refused(f"{path}: refusing to append, {shape}")
        before = len(load_entries(text))
    except (yaml.YAMLError, ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise Refused(f"{path}: refusing to append, the file does not parse as it "
                      f"stands — repair it first: {exc}") from exc

    if entry_file is None:
        authored, key = PREFLIGHT_ENTRY, PREFLIGHT_KEY
    else:
        try:
            authored = entry_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # Always non-ASCII in practice — the composed `description:` carries an em
            # dash — so this read is explicitly UTF-8, never the locale's guess (F2).
            raise Refused(f"{entry_file}: the entry block cannot be read as UTF-8: "
                          f"{exc}") from exc
    payload = compose_payload(text, authored)
    problem = verification_problem(payload.decode("utf-8"), before, key)
    if problem is not None:
        raise Refused(f"{path}: refusing to append, {problem} — nothing was written")
    return Plan(original, payload, before, key)


def cmd_append(path: Path, key: str, entry_file: Path) -> int:
    try:
        plan = prepare(path, key, entry_file)
    except Refused as exc:
        return _fail(str(exc))
    try:
        _write_atomically(path, plan.payload)
    except OSError as exc:
        return _fail(f"{path}: the append could not be written ({exc}) — the file is "
                     f"unchanged, nothing was written in place")

    # D2 — verify, then keep. Re-read FROM DISK: `prepare` already verified the parse
    # in memory, which only re-checks what this process believes; a short write, a
    # hostile filesystem or a concurrent writer is visible only in the bytes.
    try:
        written = path.read_bytes()
    except OSError as exc:
        return _restore(path, plan.original, f"{path}: cannot be re-read after the append: {exc}")
    if written != plan.payload:
        return _restore(path, plan.original,
                        f"{path}: what is on disk is not what was written "
                        f"({len(written)} bytes, expected {len(plan.payload)})")
    problem = verification_problem(written.decode("utf-8"), plan.before, plan.key)
    if problem is not None:
        return _restore(path, plan.original, f"{path}: on disk after the append, {problem}")
    return 0


def cmd_check(path: Path, key: str | None, entry_file: Path | None) -> int:
    """Exit 0 if an append would be accepted, 2 with the reason if it would not.

    Never writes anything. The whole point is ORDER: the scaffolder can ask this
    before it creates a page bundle, so a refused append leaves nothing half-built
    behind (F3). It is not a cheaper approximation of `append` — it IS `append`
    minus `_write_atomically` (V2), so pass the real `--key`/`--entry-file` when you
    have them.
    """
    try:
        prepare(path, key, entry_file)
    except Refused as exc:
        return _fail(str(exc))
    return 0


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
        # em dash, so that was not an edge case (F2). RecursionError is listed for
        # the same reason: PyYAML raises it on a deeply nested document, and it is
        # neither a YAMLError nor a ValueError, so "never fails a scaffold" used to
        # be false for one (V4).
        entries = load_entries(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, ValueError, RecursionError):
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
    chk.add_argument("--key", help="the key the append will carry (with --entry-file)")
    chk.add_argument("--entry-file", help="the block the append will place; a synthetic "
                                         "minimal entry is used when it is not given")
    style = sub.add_parser("output-style", help="print bundle | output_dir (the blog's convention)")
    style.add_argument("--file", required=True)
    style.add_argument("--site-prefix", default="", help="site_dir with no trailing slash; \"\" at root")
    a = ap.parse_args(argv)
    if a.cmd == "append":
        return cmd_append(Path(a.file), a.key, Path(a.entry_file))
    if a.cmd == "check":
        if (a.key is None) != (a.entry_file is None):
            ap.error("check: --key and --entry-file go together (pass both, or neither)")
        return cmd_check(Path(a.file), a.key,
                         Path(a.entry_file) if a.entry_file else None)
    return cmd_output_style(Path(a.file), a.site_prefix)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
