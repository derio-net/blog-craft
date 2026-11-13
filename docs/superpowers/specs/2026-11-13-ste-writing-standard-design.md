# Writing standards — a pluggable standard registry, a checker, and `apply-writing-standard` (STE, Elements of Style, Plain Language)

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

One standard is not enough for one site. STE suits guides and reference pages, and it
flattens a narrative explainer. An explainer still benefits from a standard, as long as
the standard is about clarity rather than control: cut needless words, prefer the active
voice, keep sentences short on average, and use common words. Two established guides say
exactly that, for different readers: Strunk's *The Elements of Style* (general prose) and
the US Federal Plain Language Guidelines (public-facing writing). So this feature ships
three standards: `ste` for procedures and reference, and `elements-of-style` and
`plain-language` as candidates for explainers.

## Operator decisions (2026-11-13, one question per turn)

1. **Scope of the first release: checker + rewrite + fact check.** The deterministic
   checker and a rules reference, a batch rewrite that works on any Markdown files, and a
   read-only subagent that confirms each rewrite keeps the original's facts.
2. **Strictness: exact checks fail, heuristic checks warn.** Sentence length, contractions
   and one instruction per step fail the run; passive voice, `-ing` forms and vocabulary
   hits warn. Every check's severity can be overridden (`fail | warn | off`), like
   `quality.lint`. The later standards follow the same rule: a page's average sentence
   length, "shall" and the unambiguous needless-word phrases are exact and fail; every
   phrase that depends on context warns.
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
6. **Verification: CI only.** Every row is verified by unit tests in CI. The operator
   first chose one pre-merge `client-live` rewrite, then dropped it: "verify: none, the
   tests should suffice". blog-craft has no `.fr/candidate-install` for a live strategy to
   install from. The skill and agent are held by contract tests on their text, like the
   existing `cold-reader` contract test. No post-merge gate. super-fr adopting it is a
   separate super-fr feature.
7. **Three standards, not one.** The operator asked for "a second and third standard":
   *The Elements of Style* (Strunk & White) for general prose ("brevity, rhythm, active
   verbs, omitting needless words") and Plain English / Plain Language ("active voice,
   short sentences, common terms"), adding "we could try these for the explainers". Both
   ship beside `ste`. The Elements of Style standard is built on Strunk's 1918 edition,
   which is in the public domain; the later Strunk & White editions (E. B. White's
   revisions, 1959 on) are under copyright, so none of their text ships (R25).

## Requirements

R1. A writing standard is one reference file that holds its rules as prose for the rewriter and its checker data as one fenced YAML block, so instruction and mechanics cannot drift apart.
R2. Adding a standard whose checks use only existing check kinds needs a new reference file and no code change.
R3. A standard's data declares named check instances, each of a kind from a closed set the checker implements and with that kind's parameters; an unknown kind, a bad parameter, or an unknown standard name is an error, never a silent skip.
R4. The checker validates any Markdown file, inside or outside a blog-craft blog, and needs only Python 3 and PyYAML.
R5. Each page's standard is resolved in this order: its front matter `writing_standard:` (a standard name, or `none` to opt out); else, when a blog config is given, the default of the series its front matter `series` names (when those series name different defaults, that is a configuration error); else the CLI `--default`; else the page is skipped and counted as skipped.
R6. The checker examines prose only: front matter, fenced code blocks, inline code spans, tables, HTML comments and link URLs are never checked.
R7. Under `ste`, these checks fail by default: a sentence in a numbered step over 20 words; any other sentence over 25 words; a contraction; a numbered step that holds more than one instruction.
R8. Under `ste`, these checks warn by default: passive voice in a numbered step; an `-ing` word form; a word on the replacement list; a paragraph of more than six sentences.
R9. Each check's severity can be overridden to `fail`, `warn` or `off`, from the blog config or the CLI, per standard and check; an override naming a standard or check that does not exist is a configuration error. One hit can be waived with an in-source comment that names the check and gives a reason, and a page-level hit with a front matter waiver; a waiver without a reason is itself a failure.
R10. A terms list exempts product terms (for example `worktree`, `commit`, `push`) from the `replacements`, `ing_forms` and `abbreviations` checks; terms come from the standard, from a terms file at the page's git toplevel or the blog config, and from the CLI.
R11. The `ste` vocabulary is blog-craft's own replacement list (word → suggested replacement); no ASD-STE100 dictionary text ships, and every user-facing description calls the standard "STE writing rules, based on ASD-STE100" and never claims conformance.
R12. The checker can compare a page with its version at a git ref and fail when the fenced code blocks, inline code spans, link targets or numerals in its prose differ from that version; ordered-list markers are not numerals, and a link whose only change is its anchor passes when the new anchor names a heading of the page it points to.
R13. The checker prints one line per hit as `FAIL` or `WARN` with path, line, check and message; it exits 0 when nothing fails, 1 when a check fails, and 2 on a usage or configuration error; an optional stats mode prints each page's sentence count, average and longest sentence.
R14. The `apply-writing-standard` skill takes a standard name and a list of Markdown paths or globs, and rewrites the pages in place, in batches of 3 to 5, changing only the language: front matter keys, section order, fenced code, inline code, link targets (apart from R15's anchors) and every fact stay.
R14a. The skill refuses a page with uncommitted changes or with no version at `HEAD`, and lists those pages, because the baseline for R12 and R18 is the page at `HEAD`.
R15. When the skill changes a heading's text, it finds every link in the repository to that heading's old anchor and either updates it or lists it in the batch summary.
R16. After each batch the skill runs the checker with the git-ref comparison against the pre-rewrite version, dispatches the fact check for each page, shows one summary line per page, and waits for the operator's approval before the next batch.
R17. The whole rewrite runs in one agent session (the fact checks as subagents of it), never as one `claude -p` invocation per page.
R18. A `fact-keeper` agent, read-only and given only the original and the rewritten page, returns every fact of the original marked kept, changed or lost, and every fact the rewrite added.
R19. In a blog, `/blog-post` and `/post-rewrite` apply a post's resolved standard's rules while drafting and run the checker in their gate step, and `scripts/batch-gate.sh` and the shipped CI template run the checker.
R20. `.blog-craft.yaml` accepts a per-series `writing_standard` and a `quality.writing_standard` block (`enabled`, `severities`, `terms`) as optional keys of config contract v7, with no version bump or migration; the config validator checks them, and `docs/CONFIG.md` §15 documents them.
R21. A materialized blog gets the checker and the standards' reference files in `scripts/` as byte-identical copies of the plugin's canonical files, guarded by the existing mirror test.
R22. blog-craft ships two more standards beside `ste`, `elements-of-style` and `plain-language`, meant for prose that keeps its narrative, such as explainers.
R23. Under `elements-of-style`, a phrase from the standard's list of always-needless phrases fails; a context-dependent needless phrase (such as "who is", "which was"), passive voice anywhere, a negative-form phrase with a positive replacement, and a run of three or more loose sentences warn; there is no sentence-length limit.
R24. Under `plain-language`, a page whose average sentence is over 20 words fails, and the word "shall" fails; a sentence over 35 words, passive voice anywhere, a word with a simpler replacement, a nominalization, an abbreviation used before it is spelled out, and a paragraph of more than six sentences warn.
R25. Each standard's reference names its source: `elements-of-style` draws only on Strunk's 1918 edition (public domain), in blog-craft's own words, and quotes no later edition; `plain-language` draws on the US Federal Plain Language Guidelines (a US government work) and may adapt their word list; `ste` follows R11.

## Design

### 1. The standard registry (R1–R3, R11, R22, R25)

A standard is one Markdown file:

```
skills/apply-writing-standard/standards/<name>.md
```

Its prose is the rule set as the rewriter must apply it, with short before/after
examples, and it names the standard's source (R25). Its one fenced ` ```yaml ` block is
the checker's data, parsed the same way `load_lint_data()` parses `ai-tells.md` today.

The block declares **check instances**. Each instance has an id (what severities, waivers
and output name), a `kind` from the checker's closed set, a default `severity`, and that
kind's parameters (R3). Two instances may share a kind: `plain-language` uses
`replacements` twice, once for simpler words (warn) and once for "shall" (fail).

```yaml
name: ste
title: STE writing rules, based on ASD-STE100
checks:
  sentence_length:  {kind: sentence_length, severity: fail, procedural_max: 20, descriptive_max: 25}
  contractions:     {kind: contractions, severity: fail}
  one_instruction:  {kind: one_instruction, severity: fail,
                     step_verbs: [add, apply, close, copy, delete, do, find, give, go, install,
                                  keep, make, merge, move, open, push, put, read, remove, run,
                                  select, set, show, start, stop, tell, use, write]}
  passive_in_steps: {kind: passive, severity: warn, scope: steps}
  ing_forms:        {kind: ing_forms, severity: warn}
  vocabulary:       {kind: replacements, severity: warn,
                     words: {ensure: make sure, allow: let, create: make,
                             refuse: do not accept, utilize: use}}     # ... blog-craft's own list
  paragraph_length: {kind: paragraph_length, severity: warn, max_sentences: 6}
terms: []
```

```yaml
name: elements-of-style
title: Elements of Style rules, after Strunk (1918)
checks:
  needless_words:   {kind: phrases, severity: fail,
                     phrases: {the fact that: "(omit, or: since / though)", in order to: to,
                               there is no doubt but that: no doubt,
                               the question as to whether: whether, owing to the fact that: since,
                               in spite of the fact that: though}}     # ... own list, unambiguous only
  maybe_needless:   {kind: phrases, severity: warn,
                     phrases: {who is: "(omit if it only links)", which was: "(omit if it only links)"}}
  active_voice:     {kind: passive, severity: warn, scope: all}
  positive_form:    {kind: phrases, severity: warn,
                     phrases: {not honest: dishonest, not important: trifling,
                               did not remember: forgot, did not pay any attention to: ignored,
                               did not have much confidence in: distrusted}}
  loose_sentences:  {kind: loose_sentences, severity: warn, run: 3}
terms: []
```

```yaml
name: plain-language
title: Plain language rules, based on the US Federal Plain Language Guidelines
checks:
  average_sentence_length: {kind: average_sentence_length, severity: fail, max: 20}
  long_sentence:    {kind: sentence_length, severity: warn, procedural_max: 35, descriptive_max: 35}
  must_not_shall:   {kind: replacements, severity: fail, words: {shall: must}}
  active_voice:     {kind: passive, severity: warn, scope: all}
  simple_words:     {kind: replacements, severity: warn,
                     words: {commence: start, utilize: use, prior to: before,
                             subsequent to: after, in accordance with: under,
                             approximately: about, facilitate: help, accordingly: so}}  # ... adapted list
  nominalizations:  {kind: nominalizations, severity: warn}
  abbreviations:    {kind: abbreviations, severity: warn}
  paragraph_length: {kind: paragraph_length, severity: warn, max_sentences: 6}
terms: []
```

`elements-of-style` has no length limit and only one failing check, the needless-word
list: it is a style guide, not a controlled language, and an explainer under it keeps its
voice. `plain-language` fails only on two exact facts (the page's average sentence length,
and "shall"), and warns on everything that needs judgement.

`skills/apply-writing-standard/standards/README.md` documents the block's schema, the
closed set of kinds and their parameters, and how to add a standard (R2). The registry is
every `standards/*.md` except `README.md`; the README's schema example is never loaded as
a standard. Each standard
file's prose states its source and licensing position (R11, R25).

### 2. The checker — `tools/validate_writing_standard.py` (R4–R13, R23, R24)

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
  (`skills/apply-writing-standard/standards/`), else `writing-standards/` next to the
  script (a materialized blog's `scripts/writing-standards/`). super-fr runs it straight from its pinned blog-craft
  checkout, so the first path is the one it uses.
- **Prose extraction (R6):** reuse the CommonMark-correct fence tracking of
  `validate_educational._prose_lines`, then drop tables and HTML comments, keep link text
  without the URL, and replace each inline code span with one placeholder token. The
  placeholder counts as one word and no other check matches it. Typographic apostrophes
  and quotes normalise to ASCII. Heading text is prose. Each prose unit keeps its source
  line number, and a hit on a sentence is reported on the line where the sentence starts.
- **Series and roots:** the page's series comes from its front matter `series` (a string,
  a comma list or a list), never from its path. The terms file and `git show` both work
  from each page's own git toplevel, so the checker can run from one repository against
  pages in another.
- **Procedural vs descriptive:** a sentence inside an ordered-list item is procedural;
  every other sentence is descriptive. That is the whole classification. It is mechanical
  and explainable, and it matches how the hand rewrites were written.
- **Sentence splitting:** a sentence ends at `.`, `!` or `?`, optionally followed by
  closing emphasis (`*`, `_`) or a closing quote or bracket, then whitespace and a capital,
  a backtick, an opening bracket or emphasis. A colon ends a sentence only before a list
  or a code block, so "Run this command:" before a fence is one sentence and a colon inside
  a sentence is not a break. A list item boundary also ends a sentence. The abbreviations
  `e.g.`, `i.e.`, `etc.`, `vs.`, `cf.` and `approx.` never end one. So `**Why?** Because`
  is two sentences (the 31-word artefact in the hand measurement), and a test pins each
  rule.
- **Check kinds.** The closed set. A kind is exact when it matches the text with no
  judgement, and heuristic when it can misfire; the standards set exact kinds to `fail`
  and heuristic kinds to `warn` by default (operator decision 2), apart from the phrase
  and replacement lists, whose severity each standard chooses per list.

  | Kind | Exact? | Parameters | What it matches |
  |---|---|---|---|
  | `sentence_length` | exact | `procedural_max`, `descriptive_max` | a sentence over the limit for its class; inline code counts as one word |
  | `average_sentence_length` | exact | `max` | a page whose mean prose sentence length is over `max` (reported on line 1) |
  | `contractions` | exact | — | `n't`, `'re`, `'ll`, `'ve`, `'d`, `'m` after *I*, and `'s` after a pronoun (typographic apostrophes normalised first) |
  | `one_instruction` | exact | `step_verbs` | a numbered step with two sentences that each START with a step verb, or one sentence that starts with a step verb and joins a second one directly after `and`, `, then` or `then`; verbs elsewhere in a clause never count |
  | `replacements` | exact | `words` (word → replacement) | a listed word or phrase on word boundaries, minus the terms; the message gives the replacement |
  | `phrases` | exact | `phrases` (phrase → hint) | a listed multi-word phrase, case-insensitive; the message gives the hint |
  | `passive` | heuristic | `scope: steps \| all` | a form of *be* followed by a word ending in `-ed` or `-en` |
  | `ing_forms` | heuristic | — | `\w+ing\b`, minus a stop-list (`during`, `string`, `thing`, `nothing`…) and the terms |
  | `paragraph_length` | heuristic | `max_sentences` | a paragraph with more sentences than `max_sentences` |
  | `loose_sentences` | heuristic | `run` | `run` or more sentences in a row, each two clauses joined by `and`, `but`, `so`, `which` or `who` |
  | `nominalizations` | heuristic | — | a weak verb (`make`, `give`, `take`, `have`, `conduct`, `perform`, `carry out`) + an article + a noun ending `-ion`, `-ment`, `-ance`, `-ence`, `-al` or `-sis` (so "make a decision" and "conduct an analysis" count), minus a stop-list of nouns that hide no verb |
  | `abbreviations` | heuristic | — | an all-capitals token of 2–6 letters whose first use has no spelled-out form in parentheses next to it, minus the terms |

- **Severities and waivers (R9):** keyed `<standard>.<check>` (for example
  `plain-language.paragraph_length`); a bare `<check>` applies to every standard that has
  that check, and the qualified key wins over the bare one. A key that names no existing
  standard, or no check of any standard, is a configuration error in `validate_config.py`
  and exit 2 on `--severity`. The default comes from the standard, overridden by
  `quality.writing_standard.severities`, then by `--severity`. A waiver is an HTML comment
  on the line before the hit:
  `<!-- writing-standard: ignore sentence_length -- a list of flag names -->`. The
  delimiter between check and reason is ` -- ` or ` — `; a waiver with no non-blank text
  after it fails as `waiver_reason`. A page-level check (`average_sentence_length`) is
  waived in front matter, `writing_standard_waive: {average_sentence_length: <reason>}`,
  with the same reason rule.
- **Terms (R10):** honoured by `replacements`, `ing_forms` and `abbreviations`. The
  union of the standard's `terms`, `quality.writing_standard.terms`, a
  `.writing-standard-terms` file at the page's git toplevel when present (one term per line, `#`
  comments), `--terms <file>` and `--term`.
- **Preservation (R12):** `--preserve-from <ref>` reads each page with `git show
  <ref>:./<path relative to the page's toplevel>`. It compares four multisets between the
  two versions: fenced code blocks (content), inline code spans, link targets, and numerals
  in prose (`\b\d+(\.\d+)?%?`, ordered-list markers excluded). A link target whose
  path is unchanged and whose anchor now names a heading of the page it points to counts
  as unchanged, which is what lets R15 update anchors. Any other difference fails as
  `preserve` and names what appeared or disappeared. A spelled-out number ("two" for
  "2") is not a numeral; catching that is the fact check's job, not this one's. A page
  that does not exist at the ref is reported as `preserve: no version at <ref>` and fails
  under `--preserve-from`. This is the deterministic floor under
  the fact check: it catches a changed command, path, flag, link or figure for free.
- **Output (R13):** `FAIL: <path>:<line>: <check>: <message>` and `WARN: …`. The summary
  ends with `WRITING STANDARD OK: N checked, M skipped` or `WRITING STANDARD FAILED`.
  `--stats` adds `STATS: <path>: <standard>: sentences=… avg=… max=… over_limit=…`.

### 3. The skill — `skills/apply-writing-standard/SKILL.md` (R14–R17)

Arguments: `standard` (required), `paths` (required, files or globs), `batch_size`
(optional, 3–5, default 4).

Procedure:

1. Load `standards/<standard>.md`; refuse an unknown name and list the shipped ones.
2. Resolve `paths`. The baseline for R12 and R18 is each page at `HEAD`, so refuse, with
   the pages listed, any page with uncommitted changes or with no version at `HEAD`
   (R14a).
3. For each batch:
   - Rewrite each page in place, language only (R14). Keep:
     - every front matter key (only the `title` and `tldr` values may be reworded);
     - section order;
     - code blocks, inline code and numerals byte for byte, and link targets apart from
       the anchors updated below. A step split to satisfy `one_instruction` renumbers the
       list, which the checker ignores.
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
     batch mode: drafts are written in place, never as `/tmp` copies or `.bak` files.
4. All of it happens in the invoking session (R17). The skill text says so, and it names
   the `no-claude-p-batch` rule.

The skill does not touch the cover image or any `weight` or URL, and it does not run the
educational restructure. A blog post that also needs `/post-rewrite` gets that first, then
this.

### 4. The agent — `agents/fact-keeper.md` (R18)

Read-only (Read, Grep, Glob), modelled on `cold-reader`. The dispatch gives it exactly two
paths: the original and the rewrite. The skill writes the original from `git show
HEAD:<path>` into a per-run scratch directory outside the repository and deletes it after
the batch; it is a baseline for the agent, not a draft. It reads nothing else and reports any over-share. It returns a table with one
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
- Materialization: `tools/validate_writing_standard.py` and every standard
  (`skills/apply-writing-standard/standards/*.md` but `README.md`) are copied byte for
  byte into `templates/hugo-hextra/scripts/` (standards under `scripts/writing-standards/`).
  The checker is one more pair in `test_mirrors.py`; the standards are mirrored by a glob
  in both directions, so a new standard needs no edit to the test (R2).

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

- A fourth standard, or any standard's full source text: each standard ships blog-craft's own rules and lists.
- Choosing which standard super-fr's explainers use. That choice belongs to super-fr's adoption feature.
- Any ASD-STE100 dictionary text, any text of the post-1918 Strunk & White editions, or a claim of conformance to any standard.
- Natural-language parsing. The checks are rules over text, and the heuristic ones warn.
- super-fr's adoption (pin bump, page groups, rewrites, CI wiring).
- Changing `validate_educational.py`'s gate or its AI-tells lint.

## Verification

strategy: none

- writing-standard-registry: none — unit tests in CI (`test` job) prove the registry; no install step to walk
- writing-standard-checker: none — unit tests in CI over fixture pages, inside and outside a blog
- writing-standard-selection: none — unit tests in CI
- writing-standard-ste-checks: none — unit tests in CI, one fixture per check, severity and waiver
- writing-standard-elements-of-style: none — unit tests in CI, one fixture per check of the standard
- writing-standard-plain-language: none — unit tests in CI, one fixture per check of the standard
- writing-standard-preservation: none — unit tests in CI against a temporary git repository
- writing-standard-blog-integration: none — unit tests in CI (config validator, mirror test, batch-gate, CI template)
- writing-standard-apply-skill: none — contract tests in CI on the skill and fact-keeper text (Test Plan 8), plus the checker and preservation tests the skill's gate runs; the operator chose no live walk

## Test Plan

Unit (CI, `tests/unit/`):

1. `test_writing_standard_registry.py` — the shipped set is exactly `ste`,
   `elements-of-style` and `plain-language` (`README.md` is not a standard); their blocks
   parse, each reference names its source, and no standard, README or SKILL.md says
   "conformant" or "compliant" (R11). An unknown kind, a bad parameter for a kind, and an
   unknown standard name each error. A fixture fourth standard that uses only existing
   kinds loads with no code change. Two instances of one kind in one standard both run.
2. `test_writing_standard_checker.py` — prose extraction ignores front matter, code
   fences (including a nested ```` fence), inline code, tables, HTML comments and URLs. The
   procedural/descriptive split follows ordered lists. A bold question and its answer are
   two sentences. The splitter pins: closing emphasis after `?`, the listed
   abbreviations, a colon before a list or fence versus inside a sentence. Inline code
   counts as one word; typographic apostrophes normalise. A hit is reported on the line
   where its sentence starts. Exit codes are 0/1/2. `--stats` prints its line. It runs
   with no `--config`, from one repository against pages in another (terms file and
   `git show` resolve at the page's toplevel).
3. `test_writing_standard_selection.py` — front matter beats the series default, the
   series default beats `--default`, and `none` skips; skipped pages appear in the
   `M skipped` count. A post in two series with different defaults exits 2. An unknown
   name exits 2 and names the page.
4. `test_writing_standard_ste_checks.py` — one passing and one failing fixture per check.
   Severity overrides from config and CLI work, qualified (`ste.paragraph_length`) over
   bare, and an override naming an unknown standard or check exits 2. A waiver with a
   reason (either delimiter) suppresses one hit; one without a reason fails; a front
   matter waiver covers `average_sentence_length`. Terms exempt `replacements`, `-ing`
   and abbreviations. A descriptive clause in a step that contains a step verb ("this
   lets you keep working") passes `one_instruction`.
5. `test_writing_standard_elements_of_style.py` and `test_writing_standard_plain_language.py`
   — for each check of the standard, one passing and one failing fixture, at the
   standard's default severity: under `elements-of-style` a 60-word sentence passes,
   "in order to" fails and "who is" only warns; under `plain-language` a page averaging 21 words fails, one
   averaging 19 with a single 30-word sentence passes, and "shall" fails.
6. `test_writing_standard_preserve.py` — in a temporary git repo, a changed code block,
   inline code span, link target or numeral fails `preserve`, and a reworded sentence
   passes. Splitting a step into two (renumbering the list) passes. Changing a heading
   and its in-page `#anchor` link together passes; an anchor to no heading fails. A page
   absent at the ref fails with `no version at <ref>`.
7. Blog integration — `validate_config.py` accepts and refuses the new keys, at v7. The
   mirror test pairs the checker and globs the standards both ways. `batch-gate.sh` runs
   the checker. The CI template adds the step only when enabled. A contract test, like
   `test_cold_reader_contract.py`'s wiring checks, asserts that `/blog-post` and
   `/post-rewrite` load the resolved standard and run the checker in their gate step.

8. `test_apply_writing_standard_contract.py` and `test_fact_keeper_contract.py` — like
   `test_cold_reader_contract.py`: the skill takes `standard`, `paths` and `batch_size`
   (3–5); it refuses an unknown standard, dirty paths and paths with no version at
   `HEAD`; it writes the fact-keeper baseline outside the repository and deletes it; each batch runs the checker with
   `--preserve-from HEAD`, dispatches `fact-keeper` per page and stops for approval; it
   handles changed headings' inbound links; it names the no-`claude -p` rule. The agent is
   read-only (Read, Grep, Glob), takes exactly two paths, and returns kept / changed / lost
   / added.

## Implementation Plans

| Plan | Repo | File | Depends on |
|---|---|---|---|
| 2026-11-13-writing-standards | `derio-net/blog-craft` | `2026-11-13-writing-standards` | — |
