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
_WORD = re.compile(r"[\w" + CODE_TOKEN + r"](?:[\w'\-" + CODE_TOKEN + r"]|\.(?=\w))*")
_LIST_ITEM = re.compile(r"^(\s*)(?:([-*+])|(\d{1,9})[.)])\s+(.*)$")
_TYPOGRAPHIC = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


@dataclass(frozen=True)
class Unit:
    """One block of prose: a paragraph, a heading or a list item's text."""
    text: str
    line: int
    in_step: bool
    paragraph: int
    item: int | None = None      # the list item it belongs to, across its paragraphs


@dataclass(frozen=True)
class Sentence:
    text: str
    line: int
    in_step: bool
    paragraph: int
    item: int | None = None


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


_INLINE_CODE = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _prose_source_lines(text: str) -> list[str]:
    """The page's lines with front matter and fenced code blanked, so line
    numbers hold and nothing in code is read as prose (or as a comment)."""
    lines = _blank_front_matter(text.splitlines())
    prose = _prose_line_numbers(lines)
    return [line if i in prose else "" for i, line in enumerate(lines)]


def _mask_code(text: str) -> str:
    """*text* with every inline code span replaced by x's of the same length
    (newlines kept), so offsets found in the mask are offsets in *text*."""
    return _INLINE_CODE.sub(lambda m: re.sub(r"[^\n]", "x", m.group(0)), text)


def _blank_comments(text: str) -> str:
    """Drop HTML comments outside inline code, keeping their newlines."""
    out, pos = [], 0
    for m in _COMMENT.finditer(_mask_code(text)):
        out.append(text[pos:m.start()])
        out.append("\n" * m.group(0).count("\n"))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _clean_inline(text: str) -> str:
    """Inline markup of one unit: code to CODE_TOKEN, links to their text."""
    text = _INLINE_CODE.sub(lambda m: CODE_TOKEN + "\n" * m.group(2).count("\n"), text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # inline links
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)      # reference links
    text = re.sub(r"<https?://[^>]*>", "", text)               # autolinks
    text = re.sub(r"https?://\S+?(?=[.,;:!?)\]]*(?:\s|$))", "", text)  # bare URLs
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)              # HTML tags
    return text.translate(_TYPOGRAPHIC)


def extract_prose(text: str) -> list[Unit]:
    """The prose units of a Markdown page, each with its source line (1-based).

    Front matter, fenced code, tables, HTML comments, link URLs and reference
    definitions are dropped. A unit inside an ordered-list item is a step.
    """
    lines = _blank_comments("\n".join(_prose_source_lines(text))).splitlines()
    units: list[Unit] = []
    buf: list[str] = []
    start = 0
    in_step = False
    item_indent = -1          # content indent of the open list item, -1 when none
    item_ordered = False
    item_id: int | None = None
    items = 0

    def flush():
        nonlocal buf
        joined = "\n".join(buf).strip()
        if joined:
            cleaned = _clean_inline(joined).strip()
            if cleaned:
                units.append(Unit(cleaned, start + 1, in_step, len(units), item_id))
        buf = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
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
            item_indent, item_id = -1, None
            start, in_step, buf = i, False, [heading.group(1)]
            flush()
            continue
        if item:
            flush()
            item_ordered = item.group(3) is not None
            item_indent = len(line) - len(item.group(4))
            items += 1
            item_id = items
            start, in_step, buf = i, item_ordered, [item.group(4)]
            continue
        if item_indent >= 0 and indent < item_indent and not buf:
            item_indent, item_id = -1, None   # a dedented paragraph closes the item
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
    return Sentence(text[begin:end].strip(), line, unit.in_step, unit.paragraph, unit.item)


# ------------------------------------------------------------------ checks

@dataclass(frozen=True)
class Hit:
    check: str
    severity: str
    line: int
    message: str


@dataclass(frozen=True)
class Page:
    """What a matcher sees: the prose units, their sentences, and the terms."""
    units: list[Unit]
    sentences: list[Sentence]
    terms: frozenset[str]


Finding = tuple[int, str]          # (line, message), before a check id and severity

_BE = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being)\s+"
    r"(?:(?:\w+ly|often|not|also|always|never|still|then|now|already|just|even|usually)\s+)?"
    r"(\w+(?:ed|en))\b",
    re.IGNORECASE,
)
# Words ending -ed / -en that are not past participles.
PASSIVE_STOP_LIST = frozenset({
    "open", "often", "even", "then", "when", "token", "seven", "eleven", "ten",
    "men", "women", "children", "garden", "kitchen", "chicken", "heaven", "golden",
    "wooden", "sudden", "listen", "oxygen", "citizen", "linen", "omen", "screen",
    "green", "queen", "teen", "between", "red", "bed", "seed", "speed", "feed",
    "need", "indeed", "hundred", "shed", "sled", "embed",
})
_CONTRACTION = re.compile(
    r"\b\w+n't\b|\b\w+'(?:re|ll|ve|d)\b"
    r"|\b(?:it|he|she|that|there|what|who|where|here|how|let)'s\b|\bI'm\b",
    re.IGNORECASE,
)
ING_STOP_LIST = frozenset({
    "during", "string", "thing", "nothing", "something", "anything", "everything",
    "bring", "king", "ring", "sing", "spring", "swing", "wing", "morning",
    "evening", "ceiling", "ping", "sting", "sling", "cling", "fling", "awning",
})


def _opening_verb(text: str) -> str:
    """The sentence's first word, lowercased; past a leading `Then`."""
    m = re.match(r"[\s*_\"'(\[]*([A-Za-z]+)(?:,?\s+([A-Za-z]+))?", text)
    if not m:
        return ""
    if m.group(1).lower() == "then" and m.group(2):
        return m.group(2).lower()
    return m.group(1).lower()


# A second instruction joined to the first: `and`, `and then`, `, then`, `then`,
# followed by a lowercase word (a capitalised word mid-sentence is a name).
_JOINED = re.compile(r"(?:\b[Aa]nd(?:\s+then)?|,?\s*\b[Tt]hen)\s+([a-z]+)\b")


def _word_pattern(word: str) -> re.Pattern:
    body = r"\s+".join(re.escape(w) for w in word.split())
    return re.compile(r"(?<![\w-])" + body + r"(?![\w-])", re.IGNORECASE)


def match_sentence_length(page: Page, p: dict) -> list[Finding]:
    out = []
    for s in page.sentences:
        limit = p["procedural_max"] if s.in_step else p["descriptive_max"]
        n = count_words(s.text)
        if n > limit:
            kind = "step" if s.in_step else "sentence"
            out.append((s.line, f"{kind} has {n} words (max {limit})"))
    return out


def match_contractions(page: Page, p: dict) -> list[Finding]:
    return [(s.line, f"contraction {m.group(0)!r}: write the full words")
            for s in page.sentences for m in _CONTRACTION.finditer(s.text)]


def match_one_instruction(page: Page, p: dict) -> list[Finding]:
    verbs = {str(v).lower() for v in p["step_verbs"]}
    by_item: dict[int | None, list[Sentence]] = {}
    for s in page.sentences:
        if s.in_step:
            by_item.setdefault(s.item, []).append(s)
    out = []
    for sents in by_item.values():
        starts = [s for s in sents if _opening_verb(s.text) in verbs]
        if len(starts) > 1:
            out.append((sents[0].line, "step holds more than one instruction: make one step for each"))
            continue
        for s in starts:
            m = next((m for m in _JOINED.finditer(s.text) if m.group(1) in verbs), None)
            if m:
                out.append((s.line, f"step joins a second instruction ({m.group(1)!r}): "
                                    "make one step for each"))
    return out


def match_passive(page: Page, p: dict) -> list[Finding]:
    return [(s.line, f"passive voice {m.group(0)!r} ({m.group(1)}): name who does the action")
            for s in page.sentences if p["scope"] == "all" or s.in_step
            for m in _BE.finditer(s.text) if m.group(1).lower() not in PASSIVE_STOP_LIST]


def match_ing_forms(page: Page, p: dict) -> list[Finding]:
    out = []
    for s in page.sentences:
        for m in re.finditer(r"\b[A-Za-z]+ing\b", s.text):
            word = m.group(0).lower()
            if word not in ING_STOP_LIST and word not in page.terms:
                out.append((s.line, f"-ing form {m.group(0)!r}: use a verb or a noun"))
    return out


def _listed(page: Page, mapping: dict, skip_terms: bool):
    """(sentence, match, value) for each listed word or phrase of *mapping*
    found on word boundaries, case-insensitive; a term is skipped on request."""
    for key, value in mapping.items():
        if skip_terms and str(key).lower() in page.terms:
            continue
        pattern = _word_pattern(str(key))
        for s in page.sentences:
            for m in pattern.finditer(s.text):
                yield s, m, value


def match_replacements(page: Page, p: dict) -> list[Finding]:
    return [(s.line, f"{m.group(0)!r}: use {replacement!r}")
            for s, m, replacement in _listed(page, p["words"], skip_terms=True)]


def match_phrases(page: Page, p: dict) -> list[Finding]:
    return [(s.line, f"{m.group(0)!r}: {hint}")
            for s, m, hint in _listed(page, p["phrases"], skip_terms=False)]


def match_average_sentence_length(page: Page, p: dict) -> list[Finding]:
    lengths = [count_words(s.text) for s in page.sentences]
    if not lengths:
        return []
    avg = sum(lengths) / len(lengths)
    if avg <= p["max"]:
        return []
    return [(1, f"page averages {avg:.1f} words a sentence (max {p['max']})")]


# Two clauses joined by a comma and a coordinating word or a relative pronoun.
_LOOSE_JOIN = re.compile(r",\s+(?:and|but|so|which|who)\s+\w", re.IGNORECASE)


def match_loose_sentences(page: Page, p: dict) -> list[Finding]:
    out: list[Finding] = []
    run: list[Sentence] = []

    def close():
        if len(run) >= p["run"]:
            out.append((run[0].line, f"{len(run)} loose sentences in a row: "
                                     "vary them, or make some periodic"))
        run.clear()

    for s in page.sentences:
        if run and s.paragraph != run[-1].paragraph:
            close()
        if _LOOSE_JOIN.search(s.text):
            run.append(s)
        else:
            close()
    close()
    return out


_WEAK_VERB = (
    r"(?:make|makes|made|making|give|gives|gave|given|giving|take|takes|took|taken|taking"
    r"|have|has|had|having|conduct|conducts|conducted|conducting"
    r"|perform|performs|performed|performing|carr(?:y|ies|ied|ying)\s+out)"
)
_NOMINALIZATION = re.compile(
    r"\b" + _WEAK_VERB + r"\s+(?:a|an|the)\s+([A-Za-z]+(?:ion|ment|ance|ence|al|sis))\b",
    re.IGNORECASE,
)
# Nouns with those endings that hide no verb.
NOMINAL_STOP_LIST = frozenset({
    "question", "section", "function", "option", "station", "edition", "portion", "nation",
    "version", "region", "opinion", "million", "billion", "union", "onion", "basis",
    "moment", "document", "element", "segment", "fragment", "instrument", "comment",
    "sentence", "audience", "distance", "instance", "total", "final", "general", "special",
    "original", "local", "signal", "manual", "terminal", "interval", "journal", "hospital",
    "capital", "animal", "metal", "tutorial", "proposal", "material", "potential",
})


def match_nominalizations(page: Page, p: dict) -> list[Finding]:
    return [(s.line, f"{m.group(0)!r}: use the verb that {m.group(1)!r} hides")
            for s in page.sentences for m in _NOMINALIZATION.finditer(s.text)
            if m.group(1).lower() not in NOMINAL_STOP_LIST]


_ABBREVIATION = re.compile(r"(?<![\w.-])([A-Z]{2,6})s?(?![\w.-])")
# Directly after the token: a parenthesis holding a word with a lowercase letter.
_EXPANSION_AFTER = re.compile(r"\s*\([^()]*[a-z][^()]*\)")


def _spelled_out(text: str, m: re.Match) -> bool:
    """Is the abbreviation at *m* written as `full form (ABC)` or `ABC (full form)`?"""
    if text[:m.start()].endswith("(") and text[m.end():].startswith(")"):
        return re.search(r"[A-Za-z]{2}", text[:m.start() - 1]) is not None
    return _EXPANSION_AFTER.match(text, m.end()) is not None


def match_abbreviations(page: Page, p: dict) -> list[Finding]:
    seen: set[str] = set()
    out = []
    for s in page.sentences:
        for m in _ABBREVIATION.finditer(s.text):
            token = m.group(1)
            if token in seen or token.lower() in page.terms:
                continue
            seen.add(token)
            if not _spelled_out(s.text, m):
                out.append((s.line, f"{token!r} is not spelled out at its first use: "
                                    f"write the full form, then ({token})"))
    return out


def match_paragraph_length(page: Page, p: dict) -> list[Finding]:
    counts: dict[int, list[Sentence]] = {}
    for s in page.sentences:
        counts.setdefault(s.paragraph, []).append(s)
    return [(sents[0].line, f"paragraph has {len(sents)} sentences (max {p['max_sentences']})")
            for sents in counts.values() if len(sents) > p["max_sentences"]]


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

# kind -> its matcher. Every kind in KINDS has one; a kind without one would be
# an error when run, never a silent skip.
MATCHERS = {
    "sentence_length": match_sentence_length,
    "contractions": match_contractions,
    "one_instruction": match_one_instruction,
    "passive": match_passive,
    "ing_forms": match_ing_forms,
    "replacements": match_replacements,
    "paragraph_length": match_paragraph_length,
    "phrases": match_phrases,
    "average_sentence_length": match_average_sentence_length,
    "loose_sentences": match_loose_sentences,
    "nominalizations": match_nominalizations,
    "abbreviations": match_abbreviations,
}


def build_page(text: str, terms=()) -> Page:
    units = extract_prose(text)
    sentences = [s for u in units for s in split_sentences(u)]
    return Page(units, sentences, frozenset(str(t).lower() for t in terms))


@dataclass(frozen=True)
class CheckResult:
    hits: list[Hit]
    page: Page


def run_checks(text: str, standard: Standard, terms=(), severities: dict | None = None) -> CheckResult:
    """Every hit of *standard* on page *text*, and the page it built.
    *severities* maps a check id to its effective severity (default: the
    standard's); `off` skips the check."""
    page = build_page(text, list(standard.terms) + list(terms))
    hits: list[Hit] = []
    for cid, spec in standard.checks.items():
        severity = (severities or {}).get(cid, spec.severity)
        if severity == "off":
            continue
        matcher = MATCHERS.get(spec.kind)
        if matcher is None:
            raise StandardError(f"{standard.path}: check {cid!r}: kind {spec.kind} is not implemented yet")
        hits.extend(Hit(cid, severity, line, msg) for line, msg in matcher(page, spec.params))
    return CheckResult(sorted(hits, key=lambda h: (h.line, h.check)), page)


# ------------------------------------------------------------------ configuration

class ConfigError(Exception):
    """A usage or configuration error: exit 2."""


# Kinds whose hits concern the whole page, waived in front matter.
PAGE_LEVEL_KINDS = frozenset({"average_sentence_length"})

_WAIVER = re.compile(
    r"<!--\s*writing-standard:\s*ignore\s+([\w.-]+)(?:\s+(?:--|—)(.*?))?\s*-->"
)


def series_values(series) -> list[str]:
    if isinstance(series, str):
        return [s.strip() for s in series.split(",") if s.strip()]
    if isinstance(series, list):
        return [str(s) for s in series]
    return []


def resolve_standard(fm: dict, config: dict | None, default: str | None) -> str | None:
    """The page's standard name, or None to skip (R5)."""
    name = fm.get("writing_standard")
    if name is None and config:
        defaults = {}
        named = set(series_values(fm.get("series")))
        for s in config.get("series") or []:
            if isinstance(s, dict) and s.get("key") in named and s.get("writing_standard"):
                defaults[s["key"]] = str(s["writing_standard"])
        if len(set(defaults.values())) > 1:
            listed = ", ".join(f"{k}={v}" for k, v in sorted(defaults.items()))
            raise ConfigError(f"its series name different writing standards ({listed})")
        if defaults:
            name = next(iter(defaults.values()))
    if name is None:
        name = default
    if name is None or str(name) == "none":
        return None
    return str(name)


def parse_severity_overrides(items, source: str) -> dict[str, str]:
    """`key=severity` strings (or a mapping) -> {key: severity}, shape-checked."""
    out: dict[str, str] = {}
    pairs = items.items() if isinstance(items, dict) else (
        (i.partition("=")[0], i.partition("=")[2]) if "=" in i else (i, None) for i in items)
    for key, sev in pairs:
        if sev not in SEVERITIES:
            raise ConfigError(f"{source}: {key}={sev}: severity must be one of {'|'.join(SEVERITIES)}")
        out[str(key)] = str(sev)
    return out


def validate_severity_keys(keys, standards: dict[str, Standard], source: str) -> None:
    """Every key names an existing <standard>.<check>, or a bare check of some standard."""
    all_checks = {cid for std in standards.values() for cid in std.checks}
    for key in keys:
        std_name, dot, cid = key.rpartition(".")
        if dot:
            if std_name not in standards:
                raise ConfigError(f"{source}: {key}: no writing standard {std_name!r}")
            if cid not in standards[std_name].checks:
                raise ConfigError(f"{source}: {key}: standard {std_name} has no check {cid!r}")
        elif key not in all_checks:
            raise ConfigError(f"{source}: {key}: no writing standard has a check {key!r}")


def effective_severity(standard: Standard, cid: str, layers: list[dict[str, str]]) -> str:
    """Standard default, then each layer in order (config, then CLI); within
    a layer the qualified key beats the bare one."""
    severity = standard.checks[cid].severity
    for layer in layers:
        qualified = layer.get(f"{standard.name}.{cid}")
        severity = qualified or layer.get(cid) or severity
    return severity


def parse_waivers(text: str) -> tuple[dict[int, list[str]], list[Hit]]:
    """In-source waivers: {line the waiver covers: [check, ...]}, and a
    `waiver_reason` failure for each waiver with no reason. Only prose lines
    count (never fenced or inline code). A waiver covers the next line that is
    neither blank nor itself only waivers, so waivers can stack."""
    lines = _mask_code("\n".join(_prose_source_lines(text))).splitlines()
    waiver_only = re.compile(r"(?:\s*" + _WAIVER.pattern + r")+\s*")
    covers: dict[int, list[str]] = {}
    bad: list[Hit] = []
    for i, line in enumerate(lines):
        for m in _WAIVER.finditer(line):
            if not (m.group(2) or "").strip():
                bad.append(Hit("waiver_reason", "fail", i + 1,
                               f"waiver for {m.group(1)} gives no reason"))
                continue
            target = next((j for j in range(i + 1, len(lines))
                           if lines[j].strip() and not waiver_only.fullmatch(lines[j])), i + 1)
            covers.setdefault(target + 1, []).append(m.group(1))
    return covers, bad


def front_matter_waivers(fm: dict, standard: Standard,
                         standards: dict[str, Standard]) -> tuple[set[str], list[Hit]]:
    """Page-level waivers from `writing_standard_waive`. A key that names no
    check of any standard (nor a page-level kind) is a ConfigError, like an
    unknown --severity key; a sentence-level check of this standard fails."""
    raw = fm.get("writing_standard_waive") or {}
    if not isinstance(raw, dict):
        raise ConfigError("writing_standard_waive is not a mapping")
    known = {cid for std in standards.values() for cid in std.checks} | PAGE_LEVEL_KINDS
    waived, bad = set(), []
    for cid, reason in raw.items():
        cid = str(cid)
        if cid not in known:
            raise ConfigError(f"writing_standard_waive: no writing standard has a check {cid!r}")
        spec = standard.checks.get(cid)
        if not str(reason or "").strip():
            bad.append(Hit("waiver_reason", "fail", 1, f"front matter waiver for {cid} gives no reason"))
        elif spec is not None and spec.kind not in PAGE_LEVEL_KINDS:
            bad.append(Hit("waiver_reason", "fail", 1,
                           f"{cid} is not a page-level check: waive one hit in the source"))
        else:
            waived.add(cid)
    return waived, bad


def apply_waivers(hits: list[Hit], covers: dict[int, list[str]], page_waived: set[str]) -> list[Hit]:
    remaining = {line: list(cids) for line, cids in covers.items()}
    out = []
    for h in hits:
        if h.check in page_waived:
            continue
        if h.check in remaining.get(h.line, []):
            remaining[h.line].remove(h.check)
            continue
        out.append(h)
    return out


def git_toplevel(path: str) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(Path(path).resolve().parent), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, check=False)
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def read_terms_file(path: str) -> list[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def load_terms(page_path: str, config_terms, extra_terms) -> list[str]:
    """Terms beyond the standard's own: config, the page's toplevel terms file,
    and the CLI's (already read) --terms/--term."""
    terms = [str(t) for t in config_terms or []]
    top = git_toplevel(page_path)
    if top and (Path(top) / ".writing-standard-terms").is_file():
        terms += read_terms_file(str(Path(top) / ".writing-standard-terms"))
    return terms + list(extra_terms)


def split_page(text: str) -> dict:
    """The page's front matter mapping ({} when it has none)."""
    import yaml
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            try:
                data = yaml.safe_load("\n".join(lines[1:end]))
            except yaml.YAMLError as e:
                raise ConfigError(f"front matter does not parse: {e}") from e
            return data if isinstance(data, dict) else {}
    return {}


def page_stats(page: Page, standard: Standard) -> str:
    sentences = page.sentences
    lengths = [count_words(s.text) for s in sentences]
    limit = next((c.params for c in standard.checks.values() if c.kind == "sentence_length"), None)
    over = 0
    if limit:
        over = sum(1 for s, n in zip(sentences, lengths)
                   if n > (limit["procedural_max"] if s.in_step else limit["descriptive_max"]))
    avg = sum(lengths) / len(lengths) if lengths else 0.0
    return (f"sentences={len(lengths)} avg={avg:.1f} max={max(lengths, default=0)} "
            f"over_limit={over}")


# ------------------------------------------------------------------ CLI

def _expand(paths: list[str]) -> list[str]:
    import glob
    out = []
    for p in paths:
        if any(c in p for c in "*?["):
            matches = sorted(m for m in glob.glob(p, recursive=True) if Path(m).is_file())
            if not matches:
                raise ConfigError(f"{p}: no files match")
            out.extend(matches)
        elif not Path(p).is_file():
            raise ConfigError(f"{p}: no such file")
        else:
            out.append(p)
    return out


def _parser():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--default")
    ap.add_argument("--severity", action="append", default=[])
    ap.add_argument("--terms", action="append", default=[])
    ap.add_argument("--term", action="append", default=[])
    ap.add_argument("--preserve-from")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("paths", nargs="+")
    return ap


def load_config(path: str) -> dict:
    """The blog config, shape-checked where the checker reads it (exit 2 on a bad one)."""
    import yaml
    try:
        config = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: does not parse: {e}") from e
    if not isinstance(config, dict):
        raise ConfigError(f"{path}: is not a mapping")
    if not isinstance(config.get("series") or [], list):
        raise ConfigError(f"{path}: series is not a list")
    quality = config.get("quality") or {}
    if not isinstance(quality, dict):
        raise ConfigError(f"{path}: quality is not a mapping")
    ws = quality.get("writing_standard") or {}
    if not isinstance(ws, dict):
        raise ConfigError(f"{path}: quality.writing_standard is not a mapping")
    if not isinstance(ws.get("severities") or {}, dict):
        raise ConfigError(f"{path}: quality.writing_standard.severities is not a mapping")
    if not isinstance(ws.get("terms") or [], list):
        raise ConfigError(f"{path}: quality.writing_standard.terms is not a list")
    return config


@dataclass(frozen=True)
class Setup:
    """Everything that is the same for every page of one run."""
    config: dict | None
    standards: dict[str, Standard]
    config_terms: list
    layers: list[dict[str, str]]
    extra_terms: list[str]


def _setup(args) -> Setup:
    if args.preserve_from:
        raise ConfigError("--preserve-from: not implemented yet")
    config = load_config(args.config) if args.config else None
    ws = ((config or {}).get("quality") or {}).get("writing_standard") or {}
    standards = {n: load_standard(n) for n in list_standards()}
    layers = []
    for items, source in ((ws.get("severities") or {}, "quality.writing_standard.severities"),
                          (args.severity, "--severity")):
        layer = parse_severity_overrides(items, source)
        validate_severity_keys(layer, standards, source)
        layers.append(layer)
    extra = [t for f in args.terms for t in read_terms_file(f)] + list(args.term)
    return Setup(config, standards, ws.get("terms") or [], layers, extra)


def _check_page(path: str, text: str, default: str | None, setup: Setup):
    """(standard, hits, page) for one page, or (None, None, None) when it is skipped."""
    fm = split_page(text)
    name = resolve_standard(fm, setup.config, default)
    if name is None:
        return None, None, None
    if name not in setup.standards:
        raise ConfigError(f"unknown writing standard {name!r} "
                          f"(available: {', '.join(sorted(setup.standards)) or 'none'})")
    standard = setup.standards[name]
    severities = {cid: effective_severity(standard, cid, setup.layers) for cid in standard.checks}
    terms = load_terms(path, setup.config_terms, setup.extra_terms)
    result = run_checks(text, standard, terms=terms, severities=severities)
    covers, bad = parse_waivers(text)
    page_waived, bad_fm = front_matter_waivers(fm, standard, setup.standards)
    hits = apply_waivers(result.hits, covers, page_waived) + bad + bad_fm
    return standard, sorted(hits, key=lambda h: (h.line, h.check)), result.page


def main(argv: list[str]) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        setup = _setup(args)
        paths = _expand(args.paths)
    except (ConfigError, StandardError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    checked = skipped = 0
    failed = errored = False
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
            standard, hits, page = _check_page(path, text, args.default, setup)
        except (ConfigError, StandardError, OSError, UnicodeDecodeError) as e:
            print(f"ERROR: {path}: {e}", file=sys.stderr)
            errored = True
            continue
        if standard is None:
            skipped += 1
            continue
        checked += 1
        for h in hits:
            print(f"{h.severity.upper()}: {path}:{h.line}: {h.check}: {h.message}")
            failed = failed or h.severity == "fail"
        if args.stats:
            print(f"STATS: {path}: {standard.name}: {page_stats(page, standard)}")
    if errored:
        return 2
    if failed:
        print(f"WRITING STANDARD FAILED: {checked} checked, {skipped} skipped")
        return 1
    print(f"WRITING STANDARD OK: {checked} checked, {skipped} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
