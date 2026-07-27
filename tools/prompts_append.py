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
  * Verify instead of trust (D2): after writing, re-parse and require the
    document to load with exactly one more entry, carrying the expected key.
    Any failure restores the pre-append bytes and exits 2. That is what turns
    this whole class of append bug from silent into loud.

Usage:
  prompts_append.py append       --file <prompts.yaml> --key <key> --entry-file <block>
  prompts_append.py output-style --file <prompts.yaml> --site-prefix <site_dir>
"""
from __future__ import annotations

import argparse
import re
import sys
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


def cmd_append(path: Path, key: str, entry_file: Path) -> int:
    original = path.read_bytes()
    try:
        text = original.decode()
        before = load_entries(text)
    except (yaml.YAMLError, ValueError, UnicodeDecodeError) as exc:
        return _fail(f"{path}: refusing to append, the file does not parse as it stands "
                     f"— repair it first: {exc}")

    block = reindent(entry_file.read_text(), sequence_indent(text))
    # Normalise the seam to exactly one trailing newline: a prompts file that lost
    # its final newline had its last line fused with the first appended one.
    # (Trailing blank lines go with it — only a `|+` kept scalar would notice.)
    new = text.rstrip("\n") + "\n" + (block if block.endswith("\n") else block + "\n")
    path.write_bytes(new.encode())

    # D2 — verify, then keep. The restore path below is why this helper exists at
    # all: the old shell append never re-read what it wrote, so a corrupted file
    # was discovered by the next generate-images.py run, not by the scaffolder.
    try:
        after = load_entries(new)
    except (yaml.YAMLError, ValueError) as exc:
        return _restore(path, original, f"{path}: the append broke the file: {exc}")
    if len(after) != len(before) + 1:
        return _restore(path, original, f"{path}: the append left {len(after)} entries, "
                                        f"expected {len(before) + 1}")
    last = after[-1]
    if not isinstance(last, dict) or last.get("key") != key:
        return _restore(path, original, f"{path}: the last entry is not the appended key "
                                        f"{key!r} (found {_key_of(last)!r})")
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
        entries = load_entries(path.read_text())
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
    path.write_bytes(original)
    return _fail(f"{msg} — restored the pre-append bytes")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    app = sub.add_parser("append", help="append one composed entry to the images: sequence")
    app.add_argument("--file", required=True)
    app.add_argument("--key", required=True, help="the entry's key; verified after the write")
    app.add_argument("--entry-file", required=True, help="entry block, authored at 2-space indent")
    style = sub.add_parser("output-style", help="print bundle | output_dir (the blog's convention)")
    style.add_argument("--file", required=True)
    style.add_argument("--site-prefix", default="", help="site_dir with no trailing slash; \"\" at root")
    a = ap.parse_args(argv)
    if a.cmd == "append":
        return cmd_append(Path(a.file), a.key, Path(a.entry_file))
    return cmd_output_style(Path(a.file), a.site_prefix)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
