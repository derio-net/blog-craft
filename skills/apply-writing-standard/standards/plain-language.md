# Plain language rules, based on the US Federal Plain Language Guidelines

Use this standard for pages a reader must understand on the first read:
guides, policies, setup pages and anything a newcomer meets early. It keeps
the narrative of a page but asks for short sentences, common words and a
direct address to the reader.

## Source

These rules are based on the Federal Plain Language Guidelines, written by
the Plain Language Action and Information Network for United States federal
agencies (revision of May 2011). The guidelines are a work of the United
States government and are not under copyright, so blog-craft may adapt them.
blog-craft wrote these rules in its own words and adapted the word list in
the checker data from the guidelines' list of simpler words.

A page that passes this checker follows blog-craft's plain language rules,
based on the guidelines. The checker can find some faults by rule; it cannot
judge whether a reader understands the page.

## The rules

When you rewrite a page under this standard, change only the language. Keep
the structure, the code, the links, the numbers and every fact.

### 1. Write for "you"

Talk to the reader. Call the reader "you", and call your project or team
"we". A direct address is shorter and makes clear who does what.

- Before: Users should save their changes before the session ends.
- After: Save your changes before the session ends.

### 2. Keep sentences short: 20 words on average

The page's sentences average no more than 20 words. One long sentence is
fine when the page around it is short, but a sentence over 35 words is hard
to follow. The checker fails a page whose average is over 20 and warns on
each sentence over 35. Inline code counts as one word.

- Before: When the build finishes, the report that it writes lists every page
  that could not be parsed, and you should read it before you push again.
- After: The build writes a report when it finishes. The report lists each
  page it could not parse. Read it before you push again.

### 3. Use common words

Choose the everyday word over the formal one: "start" over "commence", "use"
over "utilize", "before" over "prior to". The checker warns on each word on
its list and names the simpler word.

- Before: Prior to commencing the upgrade, ascertain the current version.
- After: Before you start the upgrade, find out the current version.

### 4. Use the active voice

Let the subject do the action, so the reader knows who acts. The checker warns
on every passive it finds.

- Before: The form must be signed by the applicant.
- After: You must sign the form.

### 5. Use "must", not "shall"

"Shall" is ambiguous: readers take it as a duty, a promise or a future. Use
"must" for a duty and "will" for a future. The checker fails every "shall".

- Before: The applicant shall attach a photo.
- After: You must attach a photo.

### 6. Use verbs, not nouns made from verbs

A noun made from a verb hides the action behind a weak verb: "make a
decision" for "decide", "conduct an analysis" for "analyze". The checker warns
on a weak verb, an article and a noun of that shape.

- Before: The team will make a decision after it conducts an analysis of the
  logs.
- After: The team will decide after it analyzes the logs.

### 7. Spell out abbreviations at their first use

A reader who meets an unknown abbreviation stops. Write the full form the
first time, with the abbreviation in parentheses after it, or the abbreviation
with the full form in parentheses. After that, the short form is enough. The
checker warns on an all-capitals abbreviation whose first use has no full form
next to it. Add a term to the terms list when every reader knows it.

- Before: Open a PR when the CI passes.
- After: Open a pull request (PR) when the continuous integration (CI) build
  passes.

### 8. Keep paragraphs short

A paragraph holds one topic in no more than six sentences. The checker warns
on a paragraph with more.

- Before: one paragraph of nine sentences about install, setup and use.
- After: one short paragraph for each of install, setup and use.

### 9. Write headings as questions

A heading that asks the reader's question tells the reader where to look.
The checker does not test this rule; apply it as you rewrite.

- Before: Credential Requirements
- After: What do you need to sign in?

## Checker data

```yaml
name: plain-language
title: Plain language rules, based on the US Federal Plain Language Guidelines
checks:
  average_sentence_length: {kind: average_sentence_length, severity: fail, max: 20}
  long_sentence:    {kind: sentence_length, severity: warn, procedural_max: 35, descriptive_max: 35}
  must_not_shall:   {kind: replacements, severity: fail, words: {shall: must}}
  active_voice:     {kind: passive, severity: warn, scope: all}
  simple_words:     {kind: replacements, severity: warn,
                     words: {commence: start, commencing: starting, utilize: use,
                             prior to: before, subsequent to: after, in accordance with: under,
                             approximately: about, facilitate: help, accordingly: so,
                             additional: more, advise: tell, anticipate: expect,
                             ascertain: find out, assist: help, attempt: try,
                             consequently: so, demonstrate: show, endeavor: try,
                             expedite: speed up, furnish: give, in lieu of: instead of,
                             in the event that: if, methodology: method,
                             notwithstanding: despite, numerous: many, obtain: get,
                             purchase: buy, pursuant to: under, remainder: rest,
                             sufficient: enough, terminate: end, transmit: send,
                             with the exception of: except for, a number of: some,
                             in order to: to, initiate: start, inquire: ask}}
  nominalizations:  {kind: nominalizations, severity: warn}
  abbreviations:    {kind: abbreviations, severity: warn}
  paragraph_length: {kind: paragraph_length, severity: warn, max_sentences: 6}
terms: []
```
