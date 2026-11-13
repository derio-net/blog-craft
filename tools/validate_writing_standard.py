#!/usr/bin/env python3
"""Check Markdown pages against a writing standard (STE, Elements of Style, ...).

    validate_writing_standard.py [--config .blog-craft.yaml] [--default <standard>]
        [--severity <check>=<fail|warn|off> ...] [--terms <file>] [--term <word> ...]
        [--preserve-from <git-ref>] [--stats] <path-or-glob> [...]

A standard is one reference file, skills/apply-writing-standard/standards/<name>.md,
whose fenced yaml block declares named check instances of a closed set of kinds.
Needs only Python 3 and PyYAML. Exit 0 when nothing fails, 1 when a check fails,
2 on a usage or configuration error.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SEVERITIES = ("fail", "warn", "off")

# The closed set of check kinds: kind -> (required params, optional params),
# each a mapping param -> accepted type. A standard may only use these.
KINDS: dict[str, tuple[dict[str, type | tuple], dict[str, type | tuple]]] = {
    "sentence_length": ({"procedural_max": int, "descriptive_max": int}, {}),
    "average_sentence_length": ({"max": (int, float)}, {}),
    "contractions": ({}, {}),
    "one_instruction": ({"step_verbs": list}, {}),
    "replacements": ({"words": dict}, {}),
    "phrases": ({"phrases": dict}, {}),
    "passive": ({"scope": str}, {}),
    "ing_forms": ({}, {}),
    "paragraph_length": ({"max_sentences": int}, {}),
    "loose_sentences": ({"run": int}, {}),
    "nominalizations": ({}, {}),
    "abbreviations": ({}, {}),
}


class StandardError(Exception):
    """A standard that cannot be loaded or used: always an error, never a skip."""


@dataclass(frozen=True)
class CheckSpec:
    kind: str
    severity: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Standard:
    name: str
    title: str
    checks: dict[str, CheckSpec]
    terms: list[str]
    path: str = ""


# ------------------------------------------------------------------ registry

def standards_dirs() -> list[str]:
    """Where standards live: the plugin checkout, else writing-standards/ next
    to this script (a materialized blog's scripts/writing-standards/)."""
    here = Path(__file__).resolve().parent
    return [
        str(here.parent / "skills" / "apply-writing-standard" / "standards"),
        str(here / "writing-standards"),
    ]


def _standard_files(dirs: list[str] | None) -> dict[str, Path]:
    """name -> file, first directory wins; README.md is never a standard."""
    found: dict[str, Path] = {}
    for d in dirs if dirs is not None else standards_dirs():
        p = Path(d)
        if not p.is_dir():
            continue
        for f in sorted(p.glob("*.md")):
            if f.name == "README.md":
                continue
            found.setdefault(f.stem, f)
    return found


def list_standards(dirs: list[str] | None = None) -> list[str]:
    return sorted(_standard_files(dirs))


def _parse_block(path: Path) -> dict:
    """The first fenced yaml block of a reference file, as a mapping."""
    import yaml
    m = re.search(r"```yaml\n(.*?)```", path.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        raise StandardError(f"{path}: no fenced yaml block")
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        raise StandardError(f"{path}: yaml block does not parse: {e}") from e
    if not isinstance(data, dict):
        raise StandardError(f"{path}: yaml block is not a mapping")
    return data


def _validate_check(path: Path, cid: str, raw) -> CheckSpec:
    """One check instance: a known kind, a valid severity, exactly its kind's params."""
    where = f"{path}: check {cid!r}"
    if not isinstance(raw, dict):
        raise StandardError(f"{where}: is not a mapping")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise StandardError(
            f"{where}: unknown kind {kind!r} (known: {', '.join(sorted(KINDS))})"
        )
    severity = raw.get("severity")
    if severity not in SEVERITIES:
        raise StandardError(
            f"{where}: severity {severity!r} is not one of {'|'.join(SEVERITIES)}"
        )
    required, optional = KINDS[kind]
    params = {k: v for k, v in raw.items() if k not in ("kind", "severity")}
    for key in params:
        if key not in required and key not in optional:
            raise StandardError(f"{where}: kind {kind} takes no parameter {key!r}")
    for key in required:
        if key not in params:
            raise StandardError(f"{where}: kind {kind} needs parameter {key!r}")
    for key, value in params.items():
        expected = required.get(key) or optional.get(key)
        if isinstance(value, bool) or not isinstance(value, expected):
            raise StandardError(f"{where}: parameter {key!r} has the wrong type")
    if kind == "passive" and params["scope"] not in ("steps", "all"):
        raise StandardError(f"{where}: parameter 'scope' must be steps or all")
    return CheckSpec(kind=kind, severity=severity, params=params)


def load_standard(name: str, dirs: list[str] | None = None) -> Standard:
    files = _standard_files(dirs)
    if name not in files:
        raise StandardError(
            f"unknown writing standard {name!r} (available: "
            f"{', '.join(sorted(files)) or 'none'})"
        )
    path = files[name]
    data = _parse_block(path)
    checks_raw = data.get("checks") or {}
    if not isinstance(checks_raw, dict):
        raise StandardError(f"{path}: 'checks' is not a mapping")
    terms = data.get("terms") or []
    if not isinstance(terms, list):
        raise StandardError(f"{path}: 'terms' is not a list")
    checks = {str(cid): _validate_check(path, str(cid), raw) for cid, raw in checks_raw.items()}
    return Standard(
        name=str(data.get("name") or name),
        title=str(data.get("title") or name),
        checks=checks,
        terms=[str(t) for t in terms],
        path=str(path),
    )


# ------------------------------------------------------------------ prose

# One inline code span becomes this one token: it counts as one word, and no
# word-matching check sees it (it is not a \w character).
CODE_TOKEN = ""

# Abbreviations whose final period never ends a sentence.
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.", "approx.")

# A sentence ends at . ! or ?, then optional closing emphasis / quote / bracket,
# then whitespace, then something that can start a sentence.
_SENTENCE_END = re.compile(
    r"[.!?][*_]*[\"')\]]*[*_]*\s+(?=[A-Z" + CODE_TOKEN + r"`(\[*_\"])"
)
_WORD = re.compile(r"[\w" + CODE_TOKEN + r"][\w'\-" + CODE_TOKEN + r"]*")
_LIST_ITEM = re.compile(r"^(\s*)(?:([-*+])|(\d{1,9})[.)])\s+(.*)$")
_TYPOGRAPHIC = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


@dataclass(frozen=True)
class Unit:
    """One block of prose: a paragraph, a heading or a list item's text."""
    text: str
    line: int
    in_step: bool
    paragraph: int


@dataclass(frozen=True)
class Sentence:
    text: str
    line: int
    in_step: bool
    paragraph: int


def count_words(text: str) -> int:
    return len(_WORD.findall(text))


def _prose_line_numbers(lines: list[str]) -> set[int]:
    """Indices of the lines outside fenced code, by validate_educational's
    CommonMark fence rule (the index rides at the end of each line, where the
    fence match never looks)."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    from validate_educational import _prose_lines
    tagged = "\n".join(f"{line}\x00{i}" for i, line in enumerate(lines))
    return {int(line.rsplit("\x00", 1)[1]) for line in _prose_lines(tagged)}


def _blank_front_matter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != "---":
        return lines
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            return [""] * (end + 1) + lines[end + 1:]
    return lines


def _blank_comments(text: str) -> str:
    """Drop HTML comments, keeping their newlines so line numbers hold."""
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)


def _clean_inline(text: str) -> str:
    """Inline markup of one unit: code to CODE_TOKEN, links to their text."""
    text = re.sub(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)",
                  lambda m: CODE_TOKEN + "\n" * m.group(2).count("\n"), text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # inline links
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)      # reference links
    text = re.sub(r"<https?://[^>]*>", "", text)               # autolinks
    text = re.sub(r"https?://\S+", "", text)                   # bare URLs
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)              # HTML tags
    return text.translate(_TYPOGRAPHIC)


def extract_prose(text: str) -> list[Unit]:
    """The prose units of a Markdown page, each with its source line (1-based).

    Front matter, fenced code, tables, HTML comments, link URLs and reference
    definitions are dropped. A unit inside an ordered-list item is a step.
    """
    lines = _blank_front_matter(_blank_comments(text).splitlines())
    prose = _prose_line_numbers(lines)
    units: list[Unit] = []
    buf: list[str] = []
    start = 0
    in_step = False
    item_indent = -1          # content indent of the open list item, -1 when none
    item_ordered = False

    def flush():
        nonlocal buf
        joined = "\n".join(buf).strip()
        if joined:
            cleaned = _clean_inline(joined).strip()
            if cleaned:
                units.append(Unit(cleaned, start + 1, in_step, len(units)))
        buf = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if i not in prose or not stripped:
            flush()
            continue
        if stripped.startswith("|") or re.match(r"^\[[^\]]+\]:\s", stripped):
            flush()
            continue
        indent = len(line) - len(line.lstrip())
        item = _LIST_ITEM.match(line)
        heading = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", stripped)
        if heading:
            flush()
            item_indent = -1
            start, in_step, buf = i, False, [heading.group(1)]
            flush()
            continue
        if item:
            flush()
            item_ordered = item.group(3) is not None
            item_indent = len(line) - len(item.group(4))
            start, in_step, buf = i, item_ordered, [item.group(4)]
            continue
        if item_indent >= 0 and indent < item_indent and not buf:
            item_indent = -1           # a dedented paragraph closes the item
        if not buf:
            start = i
            in_step = item_indent >= 0 and item_ordered
        buf.append(stripped.lstrip("> ").strip() if stripped.startswith(">") else stripped)
    flush()
    return units


def split_sentences(unit: Unit) -> list[Sentence]:
    """Split one unit into sentences; a colon never splits (a colon before a
    list or a fence already ends its unit)."""
    out: list[Sentence] = []
    text = unit.text
    begin = 0
    for m in _SENTENCE_END.finditer(text):
        before = text[begin:m.start() + 1]
        last = before.split()[-1].lower().lstrip("(*_\"") if before.split() else ""
        if last in ABBREVIATIONS:
            continue
        out.append(_sentence(unit, text, begin, m.end()))
        begin = m.end()
    if text[begin:].strip():
        out.append(_sentence(unit, text, begin, len(text)))
    return out


def _sentence(unit: Unit, text: str, begin: int, end: int) -> Sentence:
    lead = len(text[begin:end]) - len(text[begin:end].lstrip())
    line = unit.line + text[:begin + lead].count("\n")
    return Sentence(text[begin:end].strip(), line, unit.in_step, unit.paragraph)


def main(argv: list[str]) -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
