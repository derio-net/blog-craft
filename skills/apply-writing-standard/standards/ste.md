# STE writing rules, based on ASD-STE100

Use this standard for procedures and reference pages. The reader must act on
each sentence, so each sentence must be short and must say one thing.

## Source

These are STE writing rules, based on ASD-STE100 (Simplified Technical
English). blog-craft wrote these rules and the replacement list below in its
own words. No text from the ASD-STE100 dictionary is in this file. A page that
passes this checker follows blog-craft's STE writing rules. It is not an
ASD-STE100 document, and nothing here says that it is.

## The rules

When you rewrite a page under this standard, change only the language. Keep
the structure, the code, the links, the numbers and every fact.

### 1. Keep sentences short

A sentence in a numbered step has no more than 20 words. Any other sentence
has no more than 25 words. Inline code counts as one word.

- Before: When the build finishes and you have looked at the output, open the
  report, which lists every page that the checker could not parse.
- After: Open the report when the build stops. The report lists each page that
  the checker could not parse.

### 2. Write one instruction in each step

A numbered step tells the reader to do one thing. If a step has two
instructions, make two steps.

- Before: 1. Open the file and run the tests.
- After:
  1. Open the file.
  2. Run the tests.

### 3. Do not use contractions

Write the full words.

- Before: Don't push until it's green.
- After: Do not push until the build is green.

### 4. Use the active voice in steps

In a step, the reader does the action. Name who does it.

- Before: 3. The cache is deleted.
- After: 3. Delete the cache.

### 5. Do not use -ing forms

Use a verb or a noun instead. Product terms are not changed.

- Before: Before pushing, check the branch.
- After: Before you push, check the branch.

### 6. Use the approved words

Use the simple word from the list below in place of the long word.

- Before: Ensure the script can utilize the cache.
- After: Make sure that the script can use the cache.

### 7. Keep paragraphs short

A paragraph has no more than six sentences. Start a new paragraph for a new
topic.

- Before: one paragraph of eight sentences about setup and about use.
- After: one paragraph about setup and one paragraph about use.

## Checker data

The checker reads this block. Each check has an id, a kind, a severity and the
parameters of its kind. Add product terms to `terms` so that the vocabulary and
-ing checks do not flag them.

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
                     words: {ensure: make sure, ensures: makes sure,
                             allow: let, allows: lets,
                             create: make, creates: makes,
                             refuse: do not accept, refuses: does not accept,
                             require: need, requires: needs,
                             utilize: use, utilizes: uses,
                             provide: give, provides: gives,
                             commence: start, terminate: stop,
                             assist: help, assists: helps,
                             obtain: get, purchase: buy,
                             approximately: about, additional: more,
                             sufficient: enough, numerous: many,
                             subsequently: then, prior to: before,
                             in order to: to, regarding: about,
                             modify: change, modifies: changes,
                             indicate: show, indicates: shows,
                             locate: find, retain: keep,
                             attempt: try, verify: make sure,
                             perform: do, performs: does,
                             initiate: start, demonstrate: show,
                             facilitate: help, determine: find}}
  paragraph_length: {kind: paragraph_length, severity: warn, max_sentences: 6}
terms: []
```
