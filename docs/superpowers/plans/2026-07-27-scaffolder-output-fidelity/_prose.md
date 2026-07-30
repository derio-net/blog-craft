# Scaffolder output fidelity + glossary display text

Four defects from one `/blog-post` run against `derio-net/frank`
([#65](https://github.com/derio-net/blog-craft/issues/65)). Spec:
`docs/superpowers/specs/2026-07-27-scaffolder-output-fidelity-design.md`.

## Why the phases are ordered this way

The data-corrupting defect goes first and alone. `tools/prompts_append.py` is
built and tested against the file shapes directly (phase 1) before
`blog-post-create.sh` is allowed to depend on it (phase 2), because the append is
the one operation in this scaffolder that can destroy an operator's file — a
~1900-line entries file that every subsequent `generate-images.py` invocation
reads. Phases 3 and 4 then change what the scaffolder *writes*, which is only
safe to iterate on once the write itself is verified.

Phase 5 (glossary) has no dependency on 1–4 and is ordered last-but-one only so
the riskiest work lands first; it could run in parallel.

## The two rejected designs, recorded

**Load-append-dump.** The issue offers it as the safest fix for item 1. It is
rejected in the spec (D1): `yaml.safe_dump` over a real entries file reflows
every block scalar, re-quotes every string and reorders keys. That is the
tradeoff `tools/migrate_prompts.py:16-17` explicitly accepts for a one-shot
migration ("yaml round-trip drops comments — hand-migrate when comments matter")
and it is the wrong trade for a helper that runs on every post. Detecting the
file's own indentation leaves every byte above the insertion point untouched.

**Detecting a key convention.** Rejected (D6). The reporting blog's
`ops-30-silent-failure` requires an `operating` → `ops` abbreviation that exists
in no config key — `series[]` carries `{key, title, description, content_type}`
and nothing else. Detection would be guesswork applied to the field that *names*
the entry, so `--key` is an explicit override instead. Detecting the `output`
convention (D7) is different in kind: the file states the answer, the rule is a
count, and every existing blog keeps its current default.

## What the existing tests could not see

`tests/unit/test_blog_post_create.py:37` seeds the entries file as `"images:\n"`.
An empty sequence parses identically whether the appended item is indented or
not, and it establishes no convention to detect — so six passing tests coexisted
with a defect that corrupts the file on the first real blog. Phase 2 adds a
`prompts_seed` hook to the fixture precisely to close that blind spot, and every
new assertion in phases 2–4 uses it.

`tests/smoke-blog-post.sh:93` has the mirror-image problem: an awk terminator
hardcoded to `/^  - key:/`. It is not wrong today, but it stops terminating the
moment indentation varies, which turns the scene-only assertion vacuous rather
than red. Phase 2 relaxes it.

## Two things that must not regress

- **Anchors stay keyed on the key.** `abbr.html` derives `$id` and the CSS anchor
  name from `anchorize $key`. Phase 5 changes only the *display* resolution;
  moving anchors onto shared display text would collide two senses of `GC` onto
  one anchor name and reintroduce the panel-placement bug #49 fixed.
- **The mirrors.** `tools/validate_glossary.py` ships into blogs byte-identical
  (`tests/unit/test_mirrors.py:34`), and both edited skills have OpenCode copies
  (`tests/unit/test_opencode_sync.py`). Phase 5 re-mirrors; phase 6 re-syncs.
