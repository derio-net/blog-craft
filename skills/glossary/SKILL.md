---
name: glossary
description: Scan a post, a series, or a whole blog for technical abbreviations, curate definitions into data/glossary.yaml, and mark each first occurrence with a click-to-expand {{< abbr >}} shortcode. Requires features.glossary.enabled in .blog-craft.yaml.
user-invocable: true
disable-model-invocation: false
arguments:
  - name: target
    description: "A series key (e.g. tutorials) or a post path relative to content/docs/ (e.g. tutorials/07-monitoring). If omitted, scans every post in the blog."
    required: false
---

# Curate the abbreviation glossary

Find the technical abbreviations a reader may not know, write a short definition for each, and mark them so the reader can click and find out without leaving the page.

**Announce at start:** "I'm using glossary to scan `<target>` for abbreviations."

## Plugin internals

Three helpers do the deterministic work. **Do not re-implement any of it in prose** — the exclusion rules in particular are shared machinery, and a second opinion about what counts as prose is how a marker ends up inside a code sample.

- **`<plugin_root>/tools/glossary_scan.py`** — `--config <cfg> <path…>`, prints JSON candidates to stdout. Finds 2–10 character uppercase tokens that are genuinely in prose, skipping code fences, inline code, frontmatter, headings, links, URLs, existing shortcodes and HTML tags. Returns `{term, display, file, line, sentence, occurrences, known}` per term, deduped.
- **`<plugin_root>/tools/glossary_apply.py`** — `--config <cfg> [--all] <path…>`, inserts `{{< abbr "TERM" >}}` at the first occurrence per post. Idempotent: running it twice changes nothing.
- **`<plugin_root>/tools/validate_glossary.py`** — `--config <cfg> <path…>`, the CI gate. Errors on a marker with no registry entry, an entry with no name/description, or a marker inside a shortcode body that is renderer source rather than prose (currently `{{< papers/landscape >}}`, whose body Hugo hands to mermaid).

  That last error means the marker **renders into a diagram** and breaks the build. The registry key is usually valid, so adding an entry will not clear it — delete the marker and leave the term as plain text. The scanner no longer proposes markers there, but it cannot remove ones an earlier sweep inserted: `glossary_apply` is idempotent and only ever adds.

## Discovery contract

Walk up from CWD looking for `.blog-craft.yaml`. The directory containing it is the **blog root**. If not found, refuse:

> **Not in a blog-craft blog.** Run `/bootstrap-blog` first or `cd` to a blog-craft repo.

## Procedure

### Step 1: Check the feature is on

Read `features.glossary.enabled` from the config. If it is not `true`, stop and offer:

> **The glossary feature is off for this blog.** I can enable it: set `features.glossary.enabled: true` in `.blog-craft.yaml` and run `/update` to materialize the shortcodes and stylesheet. Want me to do that?

Do not scan until it is on — marking posts with a shortcode the blog cannot render would fail the next build.

### Step 2: Resolve the target

| `target` | Scan |
|---|---|
| *(omitted)* | `<blog_root>/<site_dir>/content/docs/*/*/index.md` |
| a series key | `<blog_root>/<site_dir>/content/docs/<key>/*/index.md` |
| `<series>/<NN>-<slug>` | that one post's `index.md` |

Confirm the paths exist; refuse with the resolved glob if nothing matches.

### Step 3: Scan

```bash
python <plugin_root>/tools/glossary_scan.py --config <blog_root>/.blog-craft.yaml <paths…>
```

Consume the JSON. Entries with `known: true` are already defined — they need marking, not defining. Skip straight to step 5 for those.

### Step 4: Write the definitions

For each candidate, write two fields, using the `sentence` the scanner returned as your grounding:

- **`name`** — what the letters stand for, expanded. "Network UPS Tools", not "a UPS daemon".
- **`description`** — one or two sentences on what it *is* and why a reader of this post cares. Aim for the sentence you would say out loud if the reader asked "sorry, what's that?"

**Drop what you cannot establish.** If the post does not make the expansion clear and you are not confident, leave the term out rather than guessing. A wrong expansion in a teaching blog is worse than no expansion — the reader has no way to know it is wrong, and it will be quoted back. Say which terms you dropped and why.

Also drop terms that are not worth a reader's click: an abbreviation the post itself defines in the next sentence, or one so universal to the audience that a panel would be noise. Use judgement; the scanner deliberately does not.

Optionally add **`url`** for a canonical home page (absolute `http(s)` only — the validator enforces it).

### Step 5: Show the diff before writing

Present the proposed additions to `<blog_root>/<site_dir>/data/glossary.yaml` and ask for confirmation. Never silently rewrite an entry that already exists — if a definition is already there and you would have written something different, say so and let the author choose.

Write the file with keys sorted alphabetically (the validator warns otherwise). Create it if this is the blog's first run.

### Step 6: Mark the posts

```bash
python <plugin_root>/tools/glossary_apply.py --config <blog_root>/.blog-craft.yaml <paths…>
```

Report each edit as `file:line  TERM`. Pass `--all` only if the author explicitly wants every occurrence marked rather than the first per post.

### Step 7: Hand back

Tell the author to check the result:

```bash
python <plugin_root>/tools/validate_glossary.py --config .blog-craft.yaml content/docs/*/*/index.md
bash scripts/hugo-serve.sh
```

Mention what to look at: the marked terms should read as ordinary prose with a dotted underline, and clicking one should open the panel. If they want a full list on a page of their own, `{{< glossary-index >}}` renders the whole registry alphabetically — they create the page, blog-craft does not.

## Notes

- The registry is **blog-wide**. A term defined while writing post 3 is available to post 7, and a later run marks it there without asking again.
- `data/glossary.yaml` is operator-owned (`content` class in the path manifest), so `/update` never touches it.
- A term whose plural or possessive appears in prose is marked `{{< abbr "SLO" "SLOs" >}}` — the registry key stays uninflected so plurals never fork an entry.
