# Writing standards

Each `<name>.md` in this directory, except this README, is one writing
standard. `tools/validate_writing_standard.py --default <name>` checks a page
against it, and the `apply-writing-standard` skill rewrites a page to it.

| Standard | Use it for | Source |
|---|---|---|
| `ste` | procedures and reference pages | STE writing rules, based on ASD-STE100 |
| `elements-of-style` | explainers and essays that keep their narrative | Strunk's 1918 edition, public domain |
| `plain-language` | guides and pages a newcomer reads first | the US Federal Plain Language Guidelines, a US government work |

## What a standard file holds

A standard file has two parts, so the rules and the checks cannot drift apart:

1. **Prose.** The rules as the rewriter applies them, each with a short
   `- Before:` and `- After:` example, and a `## Source` section that names the
   source and its licensing position. Every `- After:` example must pass the
   standard's own checker.
2. **One fenced `yaml` block**, the checker's data. Only the first `yaml` block
   is read.

The block has this schema:

```yaml
name: <name>              # the file name without .md
title: <one line>         # what the standard is, and what it is based on
checks:                   # named check instances
  <check id>: {kind: <kind>, severity: fail | warn | off, <the kind's parameters>}
terms: []                 # words no check flags (product names, known acronyms)
```

The check id is what the output, `--severity`, the blog config's
`quality.writing_standard.severities` and the waivers name. Two checks may
share a kind: `plain-language` uses `replacements` once for simpler words
(`warn`) and once for "shall" (`fail`). A kind outside the set below, a missing
or extra parameter, a parameter of the wrong type or a bad severity is an
error, never a silent skip.

## The kinds

A kind is exact when it matches the text with no judgement, and heuristic
when it can misfire. The shipped standards set exact kinds to `fail` and
heuristic kinds to `warn`, apart from the phrase and word lists, whose
severity each standard chooses.

| Kind | Exact? | Parameters | What it matches |
|---|---|---|---|
| `sentence_length` | exact | `procedural_max`, `descriptive_max` (integers) | a sentence over the limit for its class: a sentence in an ordered-list item is procedural, any other is descriptive; inline code counts as one word |
| `average_sentence_length` | exact | `max` (a number) | a page whose mean sentence length is over `max`, reported on line 1; waive it in front matter with `writing_standard_waive: {<check id>: <reason>}` |
| `contractions` | exact | none | `n't`, `'re`, `'ll`, `'ve`, `'d`, `I'm`, and `'s` after a pronoun |
| `one_instruction` | exact | `step_verbs` (a list) | a numbered step with two sentences that each start with a step verb, or one that joins a second step verb after `and`, `, then` or `then` |
| `replacements` | exact | `words` (word or phrase: replacement) | a listed word or phrase on word boundaries, case-insensitive, minus the terms; the message gives the replacement |
| `phrases` | exact | `phrases` (phrase: hint) | a listed phrase on word boundaries, case-insensitive; the message gives the hint; a phrase inside a longer listed phrase reports once |
| `passive` | heuristic | `scope` (`steps` or `all`) | a form of *be*, an optional adverb, then a word ending in `-ed` or `-en` |
| `ing_forms` | heuristic | none | a word ending in `-ing`, minus a stop-list and the terms |
| `paragraph_length` | heuristic | `max_sentences` (an integer) | a paragraph with more sentences than `max_sentences` |
| `loose_sentences` | heuristic | `run` (an integer) | `run` or more sentences in a row in one paragraph, each two clauses joined by a comma and `and`, `but`, `so`, `which` or `who` |
| `nominalizations` | heuristic | none | a weak verb (`make`, `give`, `take`, `have`, `conduct`, `perform`, `carry out`), an article, then a noun ending in `-ion`, `-ment`, `-ance`, `-ence`, `-al` or `-sis`, minus a stop-list |
| `abbreviations` | heuristic | none | a capitalized token of 2 to 6 letters whose first use has no full form in parentheses next to it, minus the terms |

The checker reads prose only. Front matter, fenced code, inline code, tables,
HTML comments and link targets are never checked.

## Add a standard

1. Write `<name>.md` in this directory: the rules as prose with before and
   after examples, a `## Source` section, and the `yaml` block, using only the
   kinds above.
2. Run `python3 tools/validate_writing_standard.py --default <name>` on a
   scratch page that holds only your `- After:` examples, and fix each example
   until nothing fails or warns.
3. Run the unit tests (`bash tests/run-unit.sh tests/unit/ -k writing_standard`).
   No code changes: a standard that uses only these kinds needs none. A new
   kind needs a matcher in the checker, and that is a code change.
