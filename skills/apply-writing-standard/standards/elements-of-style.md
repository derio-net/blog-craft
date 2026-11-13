# Elements of Style rules, after Strunk (1918)

Use this standard for prose that keeps its narrative: explainers, essays and
the long-form parts of a guide. It does not limit sentence length and it does
not flatten the voice. It asks for vigorous writing: every word earns its
place, the verbs act, and the sentence puts its weight where the reader will
feel it.

## Source

These rules follow William Strunk Jr.'s *The Elements of Style* as he printed
it for his students at Cornell in 1918. That edition is in the public domain.
blog-craft restates its principles here in its own words, with its own
examples. Nothing in this file comes from any later edition: the revisions
published from 1959 onward are under copyright, and none of their text is
quoted or paraphrased here. The two word lists in the checker data name
wordy phrases and their plain forms; they are blog-craft's lists, built on the
1918 principles.

A page that passes this checker follows blog-craft's reading of Strunk's 1918
rules. The checker can find some faults by rule; it cannot judge style, and a
clean result says only that it found nothing on its lists.

## The rules

When you rewrite a page under this standard, change only the language. Keep
the structure, the code, the links, the numbers and every fact.

### 1. Omit needless words

A sentence should hold no word it does not need, for the same reason a
machine should hold no part it does not use. This does not make every sentence
short. It makes every word work.

Some phrases are always padding: "in order to" says what "to" says, and "the
fact that" can almost always go. The checker fails these. Other phrases are
padding only some of the time: "who is" and "which was" often just link a noun
to a description that could stand next to it. The checker warns on those, and
you decide.

- Before: In order to build the site, you run the script, owing to the fact
  that the theme needs its assets.
- After: To build the site, run the script: the theme needs its assets.
- Before: The reviewer, who is a careful reader, caught the error.
- After: The reviewer, a careful reader, caught the error.

### 2. Use the active voice

Let the subject of the sentence do the action. The active voice is shorter
and names who acts. Keep the passive for a sentence where the actor truly does
not matter, or where the thing acted on is the topic. The checker warns on
every passive it finds, so you can decide each one.

- Before: The page was rebuilt by the deploy job.
- After: The deploy job rebuilt the page.

### 3. Put statements in positive form

Say what is, not what is not. A negative phrase often has a positive word
that says the same thing with more force: "did not remember" means "forgot",
and "not honest" means "dishonest". The checker warns on the phrases on its
list and names the positive word.

- Before: The script did not pay any attention to the warning.
- After: The script ignored the warning.

### 4. Avoid a succession of loose sentences

A loose sentence is two clauses joined by "and", "but", "so", "which" or
"who". One is fine. Three in a row read like a list someone forgot to edit, and
the rhythm goes slack. The checker warns on a run of three or more in one
paragraph. Vary them: make one a simple sentence, or turn one around so that
its point comes last.

- Before: We opened the log, and it was long. We searched it, but the error
  hid. We read every line, so we found it.
- After: We opened a long log. A search found nothing. Only a slow read, line
  by line, found the error.

### 5. Put the emphatic words at the end

The end of a sentence is its strongest place. Put there the word or idea you
want the reader to keep. The checker does not test this rule; apply it as you
rewrite.

- Before: The cache was the cause of the slow build, as we learned.
- After: We learned what slowed the build: the cache.

## Checker data

```yaml
name: elements-of-style
title: Elements of Style rules, after Strunk (1918)
checks:
  needless_words:   {kind: phrases, severity: fail,
                     phrases: {the fact that: "(omit, or: since / though)", in order to: to,
                               there is no doubt but that: no doubt,
                               the question as to whether: whether,
                               owing to the fact that: since,
                               due to the fact that: because,
                               in spite of the fact that: though,
                               call your attention to the fact that: remind you,
                               in the event that: if,
                               for the purpose of: to,
                               until such time as: until,
                               at this point in time: now,
                               in a hasty manner: hastily}}
  maybe_needless:   {kind: phrases, severity: warn,
                     phrases: {who is: "(omit if it only links)", who was: "(omit if it only links)",
                               which is: "(omit if it only links)", which was: "(omit if it only links)"}}
  active_voice:     {kind: passive, severity: warn, scope: all}
  positive_form:    {kind: phrases, severity: warn,
                     phrases: {not honest: dishonest, not important: trifling,
                               did not remember: forgot, did not pay any attention to: ignored,
                               did not have much confidence in: distrusted,
                               not able: unable, not possible: impossible,
                               did not succeed: failed, not often: rarely, not many: few}}
  loose_sentences:  {kind: loose_sentences, severity: warn, run: 3}
terms: []
```
