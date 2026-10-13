#!/usr/bin/env python3
"""Propose abbreviation candidates from a post's prose (docs/CONFIG.md §9).

The scanner is deliberately dumb: it finds tokens that *look* like technical
abbreviations and are genuinely in prose, and hands them to the authoring skill
with the sentence each was found in. Deciding what a term means — and whether it
is worth defining at all — is the one step that needs a model, and it is not
here.

`excluded_spans()` is public on purpose. glossary_apply.py and
validate_glossary.py import it rather than re-deriving "is this token inside a
code fence / heading / link / frontmatter?", because three implementations of
that question would eventually disagree and the failure mode of disagreement is
a corrupted post.

Library:
  excluded_spans(text, opaque_shortcodes=()) -> [(start, end), ...]   not prose
  candidates(text, opaque_shortcodes=()) -> [{term, display, start, end}, ...]
  load_opaque_shortcodes(config_path) -> (name, ...)   a blog's declared extras

`opaque_shortcodes` names a blog's own renderer-source shortcodes
(`features.glossary.opaque_body_shortcodes`); they are merged OVER the shipped
OPAQUE_BODY_SHORTCODES, never in place of them.

CLI:
  glossary_scan.py --config <.blog-craft.yaml> <path…>   # JSON to stdout
"""
from __future__ import annotations

import functools
import re

# Capitalized tokens that are never a technical abbreviation worth defining.
# Terms like HTTP, URL, API and CI stay OUT — a reader may not know them, and the
# author drops any candidate not worth a glossary entry.
STOPLIST = frozenset({
    "OK", "TODO", "FIXME", "NOTE", "WARNING", "AM", "PM", "USD", "EUR",
    "BEGIN", "END",
})

# 2–10 chars, uppercase letters/digits, first char a letter, plus an optional
# lowercase inflection. "SLOs" and "SLO's" are the term SLO shown as SLOs/SLO's —
# the registry key stays uninflected so plurals never fork an entry.
TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9})('s|s)?\b")

# An already-marked term: {{< abbr "NUT" … >}} — the key is the first quoted arg.
MARKER_RE = re.compile(r"\{\{<\s*abbr\s+\"([^\"]+)\"", re.I)

_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")
_MAX_SENTENCE = 200

_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_HEADING = re.compile(r"^ {0,3}#{1,6}(?:\s|$)")
_INDENTED = re.compile(r"^(?: {4}|\t)")

# Paired shortcodes whose BODY is not prose — it is source handed to a renderer.
# `papers/landscape` wraps its `.Inner` in `<pre class="mermaid">` after a
# `quadrantChart` header, so a marker there expands to a whole
# `<button popovertarget>` + `<span popover>` tree inside a chart axis and
# mermaid dies with `Lexical error on line 4. Unrecognized text.`
#
# The criterion is "the body is handed to a renderer", NOT "the shortcode has a
# body": `papers/pullquote` and `papers/scar` also take `.Inner` and it is
# ordinary prose that SHOULD be marked. Excluding every shortcode body would
# silently drop legitimate markers. Audited against every shipped shortcode —
# landscape is the only one that qualifies; capability-matrix, dossier-link and
# references-index take no body at all.
#
# This is the FLOOR, not the ceiling: a blog that ships its own renderer-source
# shortcode (Vega, PlantUML, a mermaid wrapper) declares it in
# `features.glossary.opaque_body_shortcodes`, and every caller merges those over
# this set (blog-craft#68).
OPAQUE_BODY_SHORTCODES = frozenset({"papers/landscape"})

# The same hazard without a shortcode: a post that writes the mermaid block as
# raw HTML. `_INLINE_PATTERNS` excludes the <pre> TAG, not the element's
# content, so diagram source read as prose (blog-craft#68). Scoped to a `mermaid`
# class — a plain `<pre>` of program output is not handed to a renderer and
# stays markable, as it always was. `mermaid` must be a whole class token, so
# `class="mermaid-legend"` does not qualify. The body is tempered against another
# `<pre` opener for the same reason the shortcode body is: an unclosed opener
# must exclude nothing rather than reach the next block's `</pre>`.
RAW_MERMAID_PRE = '<pre class="mermaid">'
_RAW_MERMAID_PRE_RE = re.compile(
    r"<pre\b[^<>]*?\bclass\s*=\s*([\"'])(?:(?!\1)[^<>])*?(?<![\w-])mermaid(?![\w-])"
    r"(?:(?!\1)[^<>])*\1[^<>]*>"
    r"(?P<body>(?:(?!<pre\b).)*?)"
    r"(?=</pre\s*>)",
    re.S | re.I,
)

def _opaque_pattern(name: str, lo: str, hi: str) -> re.Pattern:
    """opening tag … body … (closing tag), for one shortcode and one delimiter pair.

    The body is TEMPERED — it may not contain another opening tag for the same
    shortcode. Without that, a `*?` body reaches past an unclosed opener to the
    NEXT block's closer, swallowing every paragraph in between; the unclosed
    opener then silently un-marks prose instead of matching nothing.
    """
    esc, lo_e, hi_e = re.escape(name), re.escape(lo), re.escape(hi)
    return re.compile(
        # Opening tag — TEMPERED so it cannot run past its own closing delimiter.
        # A plain `.*?` here is not enough: when the body fails to match, the
        # engine backtracks by EXTENDING the tag, so an opener inside inline code
        # will happily reach the next block's `>}}` and report that block's body
        # as its own. Tempering the body without tempering the tag just moves the
        # bug.
        lo_e + r"\s*" + esc + r"\b(?:(?!" + hi_e + r").)*?" + hi_e
        # Body — tempered so it cannot contain another opening tag for the same
        # shortcode; otherwise an unclosed opener reaches the NEXT block's closer
        # and every paragraph between them becomes unmarkable.
        + r"(?P<body>(?:(?!" + lo_e + r"\s*" + esc + r"\b).)*?)"
        + r"(?=" + lo_e + r"\s*/\s*" + esc + r"\s*" + hi_e + r")",
        re.S,
    )


@functools.lru_cache(maxsize=None)
def _opaque_body_patterns(extra: frozenset[str]) -> tuple:
    """(name, pattern) for the shipped floor plus a blog's declared extras.

    Both Hugo delimiter pairs. `{{%` renders its body as markdown, which breaks a
    diagram just as thoroughly — and an asymmetry here would be a trap rather
    than a saving. Cached per name set: a series-wide sweep calls this per file.
    """
    return tuple(
        (name, _opaque_pattern(name, lo, hi))
        for name in sorted(OPAQUE_BODY_SHORTCODES | extra)
        for lo, hi in (("{{<", ">}}"), ("{{%", "%}}"))
    ) + ((RAW_MERMAID_PRE, _RAW_MERMAID_PRE_RE),)

# Inline constructs. Each requires a closing delimiter, so an unmatched opener in
# prose can never swallow the rest of the document.
_INLINE_PATTERNS = (
    re.compile(r"(`+)(?:(?!\1)[^\n]|\n(?!\n))*?\1"),   # `code` / ``code``
    re.compile(r"\{\{<.*?>\}\}", re.S),                # {{< shortcode >}}
    re.compile(r"\{\{%.*?%\}\}", re.S),                # {{% shortcode %}}
    re.compile(r"<[^<>\n]+>"),                         # raw HTML tag
    re.compile(r"!?\[[^\]\n]*\]\([^)\n]*\)"),          # [text](target)
    re.compile(r"!?\[[^\]\n]*\]\[[^\]\n]*\]"),         # [text][ref]
    re.compile(r"https?://[^\s)<>\]]+"),               # bare URL
)


def _block_spans(text: str, code_only: bool = False) -> list[tuple[int, int]]:
    """Frontmatter, fenced blocks, indented code, ATX headings — line-based.

    `code_only` drops the heading spans: it selects the regions where markup is
    shown *as literal text* rather than executed, which is what
    validate_glossary needs (a post documenting the shortcode inside a fence must
    not be gated on it, but a marker in a heading really does run).
    """
    spans: list[tuple[int, int]] = []
    lines = text.splitlines(keepends=True)
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln)

    start_i = 0
    # YAML frontmatter, only when it opens the document.
    if lines and lines[0].rstrip("\r\n") == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip("\r\n") in ("---", "..."):
                spans.append((0, offsets[i] + len(lines[i])))
                start_i = i + 1
                break

    fence = None          # (char, length) of the open fence
    prev_blank = True     # start-of-document counts as a blank line
    for i in range(start_i, len(lines)):
        raw = lines[i]
        line = raw.rstrip("\r\n")
        span = (offsets[i], offsets[i] + len(raw))

        if fence is not None:
            spans.append(span)
            m = _FENCE_OPEN.match(line)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
            continue

        m = _FENCE_OPEN.match(line)
        if m:
            fence = (m.group(1)[0], len(m.group(1)))
            spans.append(span)
            prev_blank = False
            continue

        if _HEADING.match(line):
            if not code_only:
                spans.append(span)
        elif prev_blank and _INDENTED.match(line) and line.strip():
            spans.append(span)

        prev_blank = not line.strip()

    return spans


def excluded_spans(text: str,
                   opaque_shortcodes=()) -> list[tuple[int, int]]:
    """Character spans that are NOT prose, and so must never be marked.

    Public because glossary_apply.py and validate_glossary.py consume it — one
    answer to "is this token in prose?", shared by every caller.
    """
    spans = _block_spans(text)
    for pat in _INLINE_PATTERNS:
        spans.extend((m.start(), m.end()) for m in pat.finditer(text))
    spans.extend(opaque_body_spans(text, opaque_shortcodes))
    return sorted(spans)


def _opaque_bodies(text: str, opaque_shortcodes=()) -> list[tuple[str, int, int]]:
    """(name, body_start, body_end) for each renderer-source body — the shipped
    shortcodes, a blog's declared extras, and raw `<pre class="mermaid">`.

    Separate from `_block_spans` because this is a construct question, not a
    line one: the body is delimited by the shortcode's own tags and can hold
    blank lines, indentation and anything else.

    A block whose OPENING TAG sits inside a code region is documentation — a
    post showing what the shortcode looks like — so it is skipped. Without that,
    an opener inside inline code pairs with a real block further down and the
    prose between them becomes unmarkable, which is exactly the over-broad
    exclusion this feature must not have.
    """
    skip = code_spans(text)
    out: list[tuple[str, int, int]] = []
    for name, pat in _opaque_body_patterns(frozenset(opaque_shortcodes)):
        for m in pat.finditer(text):
            if _in_any(m.start(), m.start("body"), skip):
                continue
            out.append((name, m.start("body"), m.end("body")))
    return out


def opaque_body_spans(text: str, opaque_shortcodes=()) -> list[tuple[int, int]]:
    """Bodies handed to a renderer, not to prose (see `_opaque_bodies`)."""
    return [(s, e) for _, s, e in _opaque_bodies(text, opaque_shortcodes)]


def misplaced_markers(text: str, opaque_shortcodes=()) -> list[tuple[str, int]]:
    """Executed {{< abbr >}} markers sitting in an opaque body, as (shortcode, line).

    `excluded_spans` stops NEW ones being proposed or inserted; this reports the
    ones already in a post. Both are needed: a blog swept before the exclusion
    existed carries markers the scanner will now never touch again — idempotent
    means it also never removes them — so without this check they stay until a
    build fails somewhere that names a mermaid lexer position and nothing points
    back at the glossary.

    "Executed" is the operative word, and it is why `code_spans` is subtracted
    here exactly as `markers_in` subtracts it: a post that DOCUMENTS the
    shortcode inside a fence must not be failed by its own example. Two
    functions disagreeing about what counts as a marker is the drift this
    module's shared scanner exists to prevent.
    """
    skip = code_spans(text)
    out: list[tuple[str, int]] = []
    for name, start, end in _opaque_bodies(text, opaque_shortcodes):
        for mark in MARKER_RE.finditer(text[start:end]):
            pos = start + mark.start()
            if _in_any(pos, pos + len(mark.group(0)), skip):
                continue
            out.append((name, text.count("\n", 0, pos) + 1))
    return sorted(out, key=lambda t: t[1])


def code_spans(text: str) -> list[tuple[int, int]]:
    """Regions where markup is shown as literal text: fences, indented code,
    inline code, frontmatter. Consumed by validate_glossary so a post that
    *documents* {{< abbr >}} inside a fence is not gated on that example.
    """
    spans = _block_spans(text, code_only=True)
    spans.extend((m.start(), m.end()) for m in _INLINE_PATTERNS[0].finditer(text))
    return sorted(spans)


def _in_any(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(s < end and start < e for s, e in spans)


def markers_in(text: str) -> list[tuple[str, int]]:
    """Executed {{< abbr "KEY" … >}} markers as (key, 1-based line)."""
    skip = code_spans(text)
    return [(m.group(1), text.count("\n", 0, m.start()) + 1)
            for m in MARKER_RE.finditer(text)
            if not _in_any(m.start(), m.end(), skip)]


def candidates(text: str, opaque_shortcodes=()) -> list[dict]:
    """Every prose occurrence of a candidate token, in document order."""
    spans = excluded_spans(text, opaque_shortcodes)
    out: list[dict] = []
    for m in TOKEN_RE.finditer(text):
        term = m.group(1)
        if term in STOPLIST or _in_any(m.start(), m.end(), spans):
            continue
        out.append({"term": term, "display": m.group(0),
                    "start": m.start(), "end": m.end()})
    return out


def _sentence_at(text: str, start: int, end: int) -> str:
    """The sentence containing [start, end) — the grounding a definition is written from."""
    para = text.rfind("\n\n", 0, start)
    left = 0 if para < 0 else para + 2
    for m in _SENTENCE_END.finditer(text, left, start):
        left = m.end()
    m = _SENTENCE_END.search(text, end)
    right = m.end() if m else len(text)
    right = min(right, left + _MAX_SENTENCE)
    return " ".join(text[left:right].split())


def scan_file(path: str, registry: dict | None = None,
              opaque_shortcodes=()) -> list[dict]:
    """Candidates in one file, deduped by term, richest-first metadata.

    A term already marked with {{< abbr >}} anywhere in the file is not proposed —
    the marker sits in an excluded span, so this falls out of `candidates()`
    rather than needing a second rule. A term already in `registry` IS still
    proposed when unmarked: that is how a series-wide run marks post 7 using the
    definition written for post 3. It carries `known: true` so the skill knows not
    to write a definition for it.
    """
    registry = registry or {}
    with open(path) as f:
        text = f.read()

    found: dict[str, dict] = {}
    for c in candidates(text, opaque_shortcodes):
        term = c["term"]
        if term in found:
            found[term]["occurrences"] += 1
            continue
        found[term] = {
            "term": term,
            "display": c["display"],
            "file": path,
            "line": text.count("\n", 0, c["start"]) + 1,
            "sentence": _sentence_at(text, c["start"], c["end"]),
            "occurrences": 1,
            "known": term in registry,
        }
    return list(found.values())


def load_opaque_shortcodes(config_path: str) -> tuple[str, ...]:
    """`features.glossary.opaque_body_shortcodes` — a blog's renderer shortcodes.

    Merged over OPAQUE_BODY_SHORTCODES by every caller, so declaring one can
    only widen the exclusion. A malformed value is validate_config's to report;
    here it reads as "none declared" rather than crashing a sweep.
    """
    import yaml
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
    gl = ((cfg.get("features") or {}).get("glossary") or {})
    names = gl.get("opaque_body_shortcodes") if isinstance(gl, dict) else None
    if not isinstance(names, list):
        return ()
    return tuple(n for n in names if isinstance(n, str) and n.strip())


def load_registry(config_path: str) -> dict:
    """`<blog>/<site_dir>/data/glossary.yaml`, tolerating absence."""
    import os

    import yaml
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
    root = os.path.dirname(os.path.abspath(config_path))
    site_dir = (cfg.get("site_dir") or ".").rstrip("/")
    path = os.path.join(root, site_dir, "data", "glossary.yaml")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _main(argv: list[str]) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    registry = load_registry(a.config)
    opaque = load_opaque_shortcodes(a.config)
    out: list[dict] = []
    for p in a.paths:
        out.extend(scan_file(p, registry, opaque))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
