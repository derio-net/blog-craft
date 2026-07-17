#!/usr/bin/env python3
"""Validate explainer frontmatter + the weight invariant + archetype structure.

weight == post_number + content_types.explainers.weight_offset (default 1).

Every explainer declares an `archetype` (one of the six modes below). When the
post body is available, the validator enforces that the post's `##` sections
match that archetype's canonical section structure — every recipe heading
present and in order (extra sections are allowed). An unknown archetype fails.

Library: `validate_post(fm: dict, weight_offset: int = 1, explainers_key: str = "explainers", body: str | None = None) -> list[str]`
CLI:     `validate_explainers.py --config <.blog-craft.yaml> <index.md> [<index.md> ...]`
"""
from __future__ import annotations

import re
import sys

REQUIRED_FIELDS = ["title", "date", "draft", "weight", "series",
                   "post_number", "archetype", "tldr"]

# The six explainer archetypes ("modes") and their canonical `##` section
# structure (heading text without the leading `## `). scaffold-explainer.sh
# emits exactly these headings per archetype; the validator enforces them.
# Source of truth shared with the scaffold and skills/explainers.
ARCHETYPE_SECTIONS: dict[str, list[str]] = {
    "feature-deep-dive": [
        "Overview", "Why it exists", "How it works", "Code walkthrough",
        "Tradeoffs & alternatives", "Try it yourself",
    ],
    "skill-presentation": [
        "Overview", "When it triggers", "Workflow", "Configuration",
        "Try it yourself",
    ],
    "skill-comparison": [
        "Overview", "Side-by-side", "When to choose which",
        "Concrete divergence", "Try it yourself",
    ],
    "testing-pyramid": [
        "Overview", "The pyramid", "One example per layer",
        "Gaps and tradeoffs", "Try it yourself",
    ],
    "deployment-strategy": [
        "Overview", "The pipeline", "Environments", "Rollback path",
        "Try it yourself",
    ],
    "security-posture": [
        "Threat surface", "What's enforced in CI", "What's manual",
        "One concrete control", "Try it yourself",
    ],
}


def parse_frontmatter(text: str) -> dict:
    import yaml
    if not text.startswith("---"):
        raise ValueError("missing opening `---` frontmatter")
    rest = text.split("\n", 1)[1]
    m = re.search(r"^---\s*$", rest, re.MULTILINE)
    if m is None:
        raise ValueError("missing closing `---` frontmatter")
    data = yaml.safe_load(rest[: m.start()])
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data


def split_body(text: str) -> str:
    """Return the markdown body after the closing `---` (empty-safe)."""
    if not text.startswith("---"):
        return text
    rest = text.split("\n", 1)[1]
    m = re.search(r"^---\s*$", rest, re.MULTILINE)
    if m is None:
        return text
    return rest[m.end():].lstrip("\n")


def extract_h2(body: str) -> list[str]:
    """Ordered level-2 (`## `) headings in `body`.

    Fenced code blocks (``` or ~~~) are stripped first, so a `## ` line inside a
    fence (a shell comment, a markdown example) is never mistaken for a section.
    Only plain ATX `## ` headings count; `###`+ and setext headings are ignored.
    """
    no_fences = re.sub(r"(```|~~~).*?\1", "", body, flags=re.DOTALL)
    return [m.group(1).strip()
            for m in re.finditer(r"^##[ \t]+(.+?)\s*$", no_fences, re.MULTILINE)]


def _series_contains(series_field, key: str) -> bool:
    if isinstance(series_field, str):
        return series_field == key or key in [s.strip() for s in series_field.split(",")]
    if isinstance(series_field, list):
        return any(s == key for s in series_field if isinstance(s, str))
    return False


def validate_post(fm: dict, weight_offset: int = 1, explainers_key: str = "explainers",
                  body: str | None = None) -> list[str]:
    f: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in fm:
            f.append(f"missing required field: {field}")
    pn = fm.get("post_number")
    if pn is not None and (isinstance(pn, bool) or not isinstance(pn, int) or pn < 0):
        f.append(f"post_number must be a non-negative integer, got {pn!r}")
    weight = fm.get("weight")
    if isinstance(pn, int) and pn >= 0:
        expected = pn + weight_offset
        if not isinstance(weight, int):
            f.append(f"weight must be an integer, got {weight!r}")
        elif weight != expected:
            f.append(f"weight invariant: post_number={pn}, weight={weight}, "
                     f"expected {expected} (weight = post_number + {weight_offset})")
    if "series" in fm and not _series_contains(fm["series"], explainers_key):
        f.append(f"series must contain '{explainers_key}', got {fm['series']!r}")

    # Archetype: value must be known; structure (when body given) must match.
    archetype = fm.get("archetype")
    if archetype is not None and archetype not in ARCHETYPE_SECTIONS:
        f.append(f"unknown archetype: {archetype!r} "
                 f"(known: {sorted(ARCHETYPE_SECTIONS)})")
    elif body is not None and archetype in ARCHETYPE_SECTIONS:
        required = ARCHETYPE_SECTIONS[archetype]
        found = extract_h2(body)
        found_set = set(found)
        req_set = set(required)
        for r in required:
            if r not in found_set:
                f.append(f"missing section for archetype {archetype!r}: {r!r}")
        present = [h for h in found if h in req_set]
        expected_order = [r for r in required if r in found_set]
        if present != expected_order:
            f.append(f"section order does not match archetype {archetype!r}: "
                     f"expected {expected_order}, got {present}")
    return f


def _main(argv):
    import argparse
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    cfg = (yaml.safe_load(open(a.config)).get("content_types") or {}).get("explainers") or {}
    offset = int(cfg.get("weight_offset", 1))
    ek = "explainers"
    series = (yaml.safe_load(open(a.config)).get("series") or [])
    for s in series:
        if s.get("content_type") == "explainers":
            ek = s["key"]
            break
    failed = {}
    for p in a.paths:
        try:
            text = open(p).read()
            fm = parse_frontmatter(text)
            fails = validate_post(fm, offset, ek, body=split_body(text))
        except Exception as e:  # noqa: BLE001
            fails = [f"parse error: {e}"]
        if fails:
            failed[p] = fails
    if failed:
        print("EXPLAINER FRONTMATTER VALIDATION FAILED", file=sys.stderr)
        for p, fs in failed.items():
            print(f"  {p}:", file=sys.stderr)
            for x in fs:
                print(f"    x {x}", file=sys.stderr)
        return 1
    print(f"EXPLAINER FRONTMATTER OK: {len(a.paths)} explainer(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
