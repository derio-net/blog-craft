# Writing standards — a pluggable standard registry, a checker, and `apply-writing-standard` (STE first)

- **Branch:** `feat/ste-writing-standard`
- **Date:** 2026-11-13
- **Type:** feature (new skill + new agent + new tool + standard data + blog integration)
- **Downstream consumer:** derio-net/super-fr (renders its docs site with this repo's
  `tools/render_explainer.py`, pinned by commit in its `.github/blog-craft.ref`)

## Problem

blog-craft controls *how a post is structured* (the educational-writing methodology:
Diátaxis modes, evidence first, the structural gate) and *how it sounds* (`voice`,
`voice_level`). It has nothing that controls *the language itself*: sentence length,
one instruction per step, a restricted vocabulary. That is what a controlled-language
standard such as ASD-STE100 (Simplified Technical English) gives a procedure or a
reference page.

The need is concrete. super-fr's published guides and reference pages follow no language
standard: three of them, measured on prose sentences only, average 17–18 words per
sentence, with a longest sentence of 44–64 words and 8–17% of sentences over 25 words.
Hand-written ASD-STE100 rewrites of the same three pages (same facts) came out at 9–11
words on average, longest ≤ 20 (one splitter artefact at 31), and no sentence over 25.
The same exercise showed what STE costs a narrative explainer: the "why" storytelling
flattens and the sentence count doubles. So a standard must be chosen per page, not per
blog.

Three things in blog-craft today stop it from doing this:

1. `tools/validate_educational.py` (and its AI-tells lint layer) runs only inside a
   `.blog-craft.yaml` blog, and only on `content_type: posts`. super-fr has no blog config
   and its pages are not posts.
2. `/post-rewrite` restructures a post (Diátaxis re-shaping, evidence gathering). A
   language-standard pass must do the opposite: keep the structure and every fact, and
   change only the language.
3. There is no notion of a writing standard at all, so there is nowhere to put a second
   one.

## Operator decisions (2026-11-13, one question per turn)

1. **Scope of the first release: checker + rewrite + fact check.** The deterministic
   checker and a rules reference, a batch rewrite that works on any Markdown files, and a
   read-only subagent that confirms each rewrite keeps the original's facts.
2. **Strictness: exact checks fail, heuristic checks warn.** Sentence length, contractions
   and one instruction per step fail the run; passive voice, `-ing` forms and vocabulary
   hits warn. Every check's severity can be overridden (`fail | warn | off`), like
   `quality.lint`.
3. **Vocabulary: blog-craft's own replacement list.** No ASD dictionary text ships. The
   feature is described as "STE writing rules, based on ASD-STE100", never as
   STE-conformant. Product terms are exempt.
4. **Opt-in: front matter plus a group default.** A page's `writing_standard:` always wins;
   otherwise a series default (blogs) or a CLI `--default` (repos without a blog config)
   applies.
5. **Home: a new skill, `apply-writing-standard`, with the standard as a parameter.** The
   operator's words: "new skill, apply-writing-standard with the standard passed as a
   parameter. We can even ship multiple writing standards". So a standard is data in a
   registry, and STE is its first entry.
6. **Verification: CI plus one live rewrite before merge.** Unit tests for the checker,
   registry and selection; one `client-live` walk of the skill on two super-fr pages. No
   post-merge gate. super-fr adopting it is a separate super-fr feature.

## Requirements

R1. A writing standard is one reference file that holds its rules as prose for the rewriter and its checker data as one fenced YAML block, so instruction and mechanics cannot drift apart.
R2. blog-craft ships exactly one standard in this feature, `ste`; adding another standard that uses only existing checks needs a new reference file and no code change.
R3. A standard's data names the checks it uses from a closed set the checker implements; an unknown check name, or an unknown standard name, is an error, never a silent skip.
R4. The checker validates any Markdown file, inside or outside a blog-craft blog, and needs only Python 3 and PyYAML.
R5. Each page's standard is resolved in this order: its front matter `writing_standard:` (a standard name, or `none` to opt out); else the default of its series in `.blog-craft.yaml` when a blog config is given; else the CLI `--default`; else the page is skipped and counted as skipped.
R6. The checker examines prose only: front matter, fenced code blocks, inline code spans, tables, HTML comments and link URLs are never checked.
R7. Under `ste`, these checks fail by default: a sentence in a numbered step over 20 words; any other sentence over 25 words; a contraction; a numbered step that holds more than one instruction.
R8. Under `ste`, these checks warn by default: passive voice in a numbered step; an `-ing` word form; a word on the replacement list; a paragraph of more than six sentences.
R9. Each check's severity can be overridden to `fail`, `warn` or `off`, from the blog config or the CLI, and one line can be waived with an in-source comment that names the check and gives a reason; a waiver without a reason is itself a failure.
R10. A terms list exempts product terms (for example `worktree`, `commit`, `push`) from the vocabulary and `-ing` checks; terms come from the standard, from a repo terms file or the blog config, and from the CLI.
R11. The `ste` vocabulary is blog-craft's own replacement list (word → suggested replacement); no ASD-STE100 dictionary text ships, and every user-facing description calls the standard "STE writing rules, based on ASD-STE100" and never claims conformance.
R12. The checker can compare a page with its version at a git ref and fail when the fenced code blocks, inline code spans, link targets or numbers in the page differ from that version.
R13. The checker prints one line per hit as `FAIL` or `WARN` with path, line, check and message; it exits 0 when nothing fails, 1 when a check fails, and 2 on a usage or configuration error; an optional stats mode prints each page's sentence count, average and longest sentence.
R14. The `apply-writing-standard` skill takes a standard name and a list of Markdown paths or globs, and rewrites the pages in place, in batches of 3 to 5, changing only the language: front matter keys, section order, fenced code, inline code, links and every fact stay.
R15. When the skill changes a heading's text, it finds every link in the repository to that heading's old anchor and either updates it or lists it in the batch summary.
R16. After each batch the skill runs the checker with the git-ref comparison against the pre-rewrite version, dispatches the fact check for each page, shows one summary line per page, and waits for the operator's approval before the next batch.
R17. The whole rewrite runs in one agent session (the fact checks as subagents of it), never as one `claude -p` invocation per page.
R18. A `fact-keeper` agent, read-only and given only the original and the rewritten page, returns every fact of the original marked kept, changed or lost, and every fact the rewrite added.
R19. In a blog, `/blog-post` and `/post-rewrite` apply a post's resolved standard's rules while drafting, and `scripts/batch-gate.sh` and the shipped CI template run the checker.
R20. `.blog-craft.yaml` accepts a per-series `writing_standard` and a `quality.writing_standard` block (`enabled`, `severities`, `terms`), the config validator checks them, and `docs/CONFIG.md` documents them.
R21. A materialized blog gets the checker and the standards' reference files in `scripts/` as byte-identical copies of the plugin's canonical files, guarded by the existing mirror test.

## Design

### 1. The standard registry (R1–R3, R11)

A standard is one Markdown file:

```
skills/apply-writing-standard/standards/<name>.md
```

Its prose is the rule set as the rewriter must apply it (with short before/after
examples). Its one fenced ` ```yaml ` block is the checker's data, parsed the same way
`load_lint_data()` parses `ai-tells.md` today:

```yaml
name: ste
title: STE writing rules, based on ASD-STE100
checks:                         # closed set; the checker refuses unknown names
  sentence_length:   {severity: fail, procedural_max: 20, descriptive_max: 25}
  contractions:      {severity: fail}
  one_instruction:   {severity: fail}
  passive_in_steps:  {severity: warn}
  ing_forms:         {severity: warn}
  vocabulary:        {severity: warn}
  paragraph_length:  {severity: warn, max_sentences: 6}
step_verbs: [add, apply, attach, close, copy, delete, do, find, give, go, install,
             keep, make, merge, move, open, push, put, read, remove, run, select,
             set, show, start, stop, tell, use, write]
replacements:                   # blog-craft's own list, not ASD's dictionary
  ensure: make sure
  allow: let
  allows: lets
  create: make
  refuse: do not accept
  require: must / is necessary
  utilize: use
  # ...
terms: []                       # standard-level exemptions (usually empty)
```

`skills/apply-writing-standard/standards/README.md` documents the block's schema and the
closed check set, so a second standard (say, a plain-language one) is a new file. The STE
file's prose states the licensing position of R11 in one paragraph.

### 2. The checker — `tools/validate_writing_standard.py` (R4–R13)

```
validate_writing_standard.py [--config .blog-craft.yaml] [--default <standard>]
    [--severity <check>=<fail|warn|off> ...] [--terms <file>] [--term <word> ...]
    [--preserve-from <git-ref>] [--stats] <path-or-glob> [...]
```

- **Dependencies:** stdlib + PyYAML. No NLP library; every check is a rule over text.
- **Standard resolution (R5):** front matter `writing_standard` → series default (only
  with `--config`) → `--default` → skipped. `none` skips explicitly. An unknown name is a
  configuration error (exit 2) naming the page.
- **Standards lookup:** like `load_lint_data()`: the plugin checkout
  (`skills/apply-writing-standard/standards/`), else siblings next to the script (a
  materialized blog's `scripts/`). super-fr runs it straight from its pinned blog-craft
  checkout, so the first path is the one it uses.
- **Prose extraction (R6):** reuse the CommonMark-correct fence tracking of
  `validate_educational._prose_lines`, then drop tables, HTML comments and inline code,
  and keep link text without the URL. Heading text is prose. Each prose unit keeps its
  source line number.
- **Procedural vs descriptive:** a sentence inside an ordered-list item is procedural;
  every other sentence is descriptive. That is the whole classification. It is mechanical
  and explainable, and it matches how the hand rewrites were written.
- **Sentence splitting:** split on `.`, `!`, `?` and `:` followed by whitespace and a
  capital, a backtick, or an opening bracket; a list item or a table cell boundary also
  ends a sentence. A bold question that runs into its answer counts as two sentences
  (this was the 31-word artefact in the hand measurement, and a test pins it).
- **Checks.** Exact checks (R7):
  - `sentence_length` counts words, with inline code counted as one word.
  - `contractions` matches `n't`, `'re`, `'ll`, `'ve`, `'d`, and `'s` after a pronoun.
  - `one_instruction` fails a numbered step that holds two sentences, each starting with
    a verb from `step_verbs`. It also fails one sentence that joins two such verbs with
    `and`, `, then` or `then`. Exact relative to the verb list: what the list does not
    name, it does not see.

  Heuristic checks (R8):
  - `passive_in_steps` matches a form of *be* followed by a word ending in `-ed` or `-en`,
    inside a numbered step.
  - `ing_forms` matches `\w+ing\b`, minus a stop-list (`during`, `string`, `thing`,
    `nothing`…) and the terms.
  - `vocabulary` matches the `replacements` keys on word boundaries, minus the terms.
  - `paragraph_length` counts sentences per paragraph.
- **Severities and waivers (R9):** per-check default from the standard, overridden by
  `quality.writing_standard.severities`, then by `--severity`. A waiver is an HTML comment
  on the line before the hit:
  `<!-- writing-standard: ignore sentence_length — a list of flag names -->`. A waiver
  with no reason after the dash fails as `waiver_reason`.
- **Terms (R10):** union of the standard's `terms`, `quality.writing_standard.terms`, a
  `.writing-standard-terms` file at the repo root when present (one term per line, `#`
  comments), `--terms <file>` and `--term`.
- **Preservation (R12):** `--preserve-from <ref>` reads each page with `git show
  <ref>:<path>`. It compares four multisets between the two versions: fenced code blocks
  (content), inline code spans, link targets, and number tokens in prose (`\b\d+(\.\d+)?%?`).
  Any difference fails as `preserve` and names what appeared or disappeared. A page that
  does not exist at the ref is reported and skipped. This is the deterministic floor under
  the fact check: it catches a changed command, path, flag, link or figure for free.
- **Output (R13):** `FAIL: <path>:<line>: <check>: <message>` and `WARN: …`. The summary
  ends with `WRITING STANDARD OK: N checked, M skipped` or `WRITING STANDARD FAILED`.
  `--stats` adds `STATS: <path>: <standard>: sentences=… avg=… max=… over_limit=…`.

### 3. The skill — `skills/apply-writing-standard/SKILL.md` (R14–R17)

Arguments: `standard` (required), `paths` (required, files or globs), `batch_size`
(optional, 3–5, default 4).

Procedure:

1. Load `standards/<standard>.md`; refuse an unknown name and list the shipped ones.
2. Resolve `paths`. For each page, record its current blob as the baseline: the git ref
   for R12 is `HEAD`, so the working tree must be clean for those files. Refuse with the
   dirty paths listed otherwise.
3. For each batch:
   - Rewrite each page in place, language only (R14). Keep:
     - every front matter key (only the `title` and `tldr` values may be reworded);
     - section order;
     - code blocks, inline code, link targets and numbers byte for byte.
   - If a heading's text changes, grep the repository for links to the old anchor
     (`#<old-slug>` in Markdown links), update links inside the rewritten pages, and list
     the others (R15).
   - Run `validate_writing_standard.py --default <standard> --preserve-from HEAD --stats`
     on the batch. Fix every `FAIL` before going on; the skill may not waive a check to
     pass.
   - Dispatch `fact-keeper` once per page (R18). Every fact marked changed or lost is
     fixed in the rewrite, or explained in the summary when the operator must decide.
   - Print the batch summary, one line per page: path, sentences and average before → after,
     checker result, facts kept/changed/lost/added, headings changed, inbound links listed.
   - Stop for the operator's approval (R16). Git is the safety net, as in post-rewrite's
     batch mode: no `/tmp` copies, no `.bak` files.
4. All of it happens in the invoking session (R17). The skill text says so, and it names
   the `no-claude-p-batch` rule.

The skill does not touch the cover image or any `weight` or URL, and it does not run the
educational restructure. A blog post that also needs `/post-rewrite` gets that first, then
this.

### 4. The agent — `agents/fact-keeper.md` (R18)

Read-only (Read, Grep, Glob), modelled on `cold-reader`. The dispatch gives it exactly two
paths: the original (a temporary file written from `git show HEAD:<path>` by the skill) and
the rewrite. It reads nothing else and reports any over-share. It returns a table with one
row per fact of the original (`kept | changed | lost`, with both wordings for `changed`)
and one row per fact the rewrite added. A "fact" is any claim a reader could act on or
verify: a behaviour, a condition, a default, a limit, an order of steps, a name.

### 5. Blog integration (R19–R21)

- `.blog-craft.yaml`:
  - per series: `writing_standard: <name>`;
  - `quality.writing_standard`: `enabled` (CI wiring, like `quality.enabled`), `severities`
    and `terms`;
  - `validate_config.py` checks the shapes, and that each named standard exists.
- `docs/CONFIG.md` §15 documents the keys, the resolution order and the waiver syntax.
- `/blog-post` and `/post-rewrite`: when the post resolves to a standard, load that
  standard's reference while drafting, and run the checker in the existing gate step.
- `templates/hugo-hextra/scripts/batch-gate.sh` runs `validate_writing_standard.py
  --config` after `validate_educational.py`. The CI template adds the step when
  `quality.writing_standard.enabled` is true.
- Materialization: `tools/validate_writing_standard.py` and every
  `skills/apply-writing-standard/standards/*.md` are copied byte for byte into
  `templates/hugo-hextra/scripts/` (standards under `scripts/writing-standards/`), and
  added to the mirror test's pairs.

### 6. The consumer contract for super-fr

super-fr will run, from its pinned checkout, something like:

```bash
python <blog-craft>/tools/validate_writing_standard.py --default ste \
    docs/*.md docs/reference/*.md
```

No blog config, no install step, and nothing beyond what super-fr's `site-build` job
already installs (PyYAML). The precedent is the explainers skill's standalone mode
(`scaffold-explainer.sh --standalone`, `render_explainer.py`), the one blog-craft surface
that already works with no `.blog-craft.yaml` and the one super-fr uses today. Like it,
`apply-writing-standard` and the checker need no blog root, and use the blog config only
when one is given. This feature commits to that invocation working. Pinning the
new blog-craft commit, choosing super-fr's page groups, and rewriting its pages are a
super-fr feature, not part of this one.

## Non-goals

- A second standard. The format admits one; this feature ships `ste` only.
- Any ASD-STE100 dictionary text, or a claim of conformance.
- Natural-language parsing. The checks are rules over text, and the heuristic ones warn.
- super-fr's adoption (pin bump, page groups, rewrites, CI wiring).
- Changing `validate_educational.py`'s gate or its AI-tells lint.

## Verification

strategy: client-live

- writing-standard-registry: none — unit tests in CI (`test` job) prove the registry; no install step to walk
- writing-standard-checker: none — unit tests in CI over fixture pages, inside and outside a blog
- writing-standard-selection: none — unit tests in CI
- writing-standard-ste-checks: none — unit tests in CI, one fixture per check, severity and waiver
- writing-standard-preservation: none — unit tests in CI against a temporary git repository
- writing-standard-blog-integration: none — unit tests in CI (config validator, mirror test, batch-gate, CI template)
- writing-standard-apply-skill: client-live — an agent runs the skill on two super-fr pages in a scratch copy before merge

## Test Plan

Unit (CI, `tests/unit/`):

1. `test_writing_standard_registry.py` — the shipped `ste.md` block parses. An unknown
   check name and an unknown standard name each error. A fixture second standard that
   uses only existing checks loads with no code change.
2. `test_writing_standard_checker.py` — prose extraction ignores front matter, code
   fences (including a nested ```` fence), inline code, tables, HTML comments and URLs. The
   procedural/descriptive split follows ordered lists. A bold question and its answer are
   two sentences. Exit codes are 0/1/2. `--stats` prints its line. It runs with no
   `--config`.
3. `test_writing_standard_selection.py` — front matter beats the series default, the
   series default beats `--default`, and `none` skips. An unknown name exits 2 and names
   the page.
4. `test_writing_standard_ste_checks.py` — one passing and one failing fixture per check.
   Severity overrides from config and CLI work. A waiver with a reason suppresses one hit;
   one without a reason fails. Terms exempt vocabulary and `-ing`.
5. `test_writing_standard_preserve.py` — in a temporary git repo, a changed code block,
   inline code span, link target or number fails `preserve`, and a reworded sentence
   passes.
6. Blog integration — `validate_config.py` accepts and refuses the new keys. The mirror
   test covers the new copies. `batch-gate.sh` runs the checker. The CI template adds the
   step only when enabled.

Live (pre-merge, `client-live`):

7. In a scratch copy of super-fr at its current `main`, an agent runs `/apply-writing-standard
   ste docs/reference/install.md docs/merge-protection.md`. Pass when:
   - the checker reports no `FAIL` on both pages, `preserve` included;
   - `fact-keeper` reports no `lost` fact, and every `changed` fact was fixed or accepted
     by the operator in the batch summary;
   - the run used one session (no `claude -p` in the transcript).

   Evidence: the batch summary and the checker output, recorded on the row.

## Implementation Plans

To be written by `fr-plan`.
