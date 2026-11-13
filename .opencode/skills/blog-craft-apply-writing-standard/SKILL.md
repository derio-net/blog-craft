---
name: blog-craft-apply-writing-standard
description: Rewrite existing Markdown pages to a writing standard (STE, Elements of Style, Plain Language), language only. Works in batches of 3 to 5 pages. Each batch runs the writing-standard checker against the page at HEAD, sends each page to the fact-keeper agent, and stops for approval. Use when the operator asks to apply a writing standard to pages, docs or posts, or to "rewrite this in STE" or "in plain language".
user-invocable: true
disable-model-invocation: false
arguments:
  - name: standard
    description: "The standard to apply: a file name in standards/ without .md, for example `ste`."
    required: true
  - name: paths
    description: "Markdown files or globs to rewrite."
    required: true
  - name: batch_size
    description: "Pages in one batch, from 3 to 5. Default: 4."
    required: false
---

# Apply a writing standard to existing pages

**Announce at start:** "I'm using apply-writing-standard to rewrite `<paths>` to the
`<standard>` writing standard, language only."

This skill changes the words of a page and nothing else. It does not touch the cover
image, a `weight` or the address (URL) of a page. It does not restructure a page for teaching. A blog post that
also needs `/post-rewrite` gets that skill first, then this one.

## Plugin internals

- **Standards:** `<plugin_root>/skills/apply-writing-standard/standards/<standard>.md`.
  Each file states the rules in prose and lists its checks in one `yaml` block.
  `standards/README.md` explains the check kinds.
- **Checker:** `<plugin_root>/tools/validate_writing_standard.py`. It reports `FAIL`
  and `WARN` hits. With `--preserve-from <ref>` it also fails when code, link targets or
  numerals differ from the page at that ref.
- **Fact check:** `<plugin_root>/agents/fact-keeper.md`. A read-only subagent. It
  compares the original page with the rewrite and lists each fact.

## One session, no `claude -p`

The whole rewrite runs in the invoking session. Each fact check is a subagent of this
session. Never start one `claude -p` process per page. That rule is `no-claude-p-batch`:
each `claude -p` call starts a new session from nothing, and N pages would cost N cold
starts. Keep all the work in one session.

## Step 1: Load the standard

Read `standards/<standard>.md`. If no such file exists, stop with "unknown standard
`<standard>`" and list the shipped standards: `ste`, `elements-of-style` and
`plain-language`, plus any other file in `standards/` except `README.md`.

Read the whole standard before you write. The prose rules matter as much as the checks.
The checker cannot find every rule break.

## Step 2: Resolve the pages

Expand `paths` to a list of Markdown files. The baseline for the checker and for the fact
check is each page at `HEAD`, so check each page first:

```bash
git -C <page directory> status --porcelain -- <page>
git -C <page directory> cat-file -e HEAD:./<page file name>
```

Refuse a page with uncommitted changes (the first command prints a line). Refuse a page
with no version at `HEAD` (the second command fails). List every refused page with its
reason. Go on with the others only if the operator agrees.

Then find the standard of each page before you rewrite it. The front matter key
`writing_standard` or the series of a page can pick a standard other than `<standard>`.
Run the checker once on all the pages:

```bash
python3 <plugin_root>/tools/validate_writing_standard.py --default <standard> --stats <pages>
```

The command can exit 1, because you have not rewritten the pages yet. Read only the `STATS`
lines. Each line names the standard of one page. A page with no `STATS` line resolves to
`none`, and the checker skips it. For each page with no `STATS` line or with another
standard, ask the operator before you rewrite it.

Split the remaining pages into batches of `batch_size` pages.

## Step 3: Rewrite one batch

Do these steps for each batch, in this order.

### 3a. Rewrite each page in place

Write each new page over the old file. Change the language only. Keep these things:

- every front matter key, in the same order (you may reword only the `title` and `tldr`
  values);
- the section order;
- fenced code blocks and inline code, byte for byte;
- numerals, byte for byte (write "3", not "three", if the page said "3");
- link targets, except the anchors that step 3b updates.

You may split one step into two steps to keep one instruction in each step. The list then
gets new numbers, and the checker accepts that.

### 3b. Fix links to a changed heading

When you change the text of a heading, its anchor changes too. The anchor is the
GitHub slug of the heading text: lowercase, punctuation removed, spaces changed to
hyphens, and `-1`, `-2` added to a repeated slug. A heading that ends in `{#id}` keeps
`id` as its anchor. Find each link to the old anchor in the repository of the page:

```bash
git -C <page toplevel> grep -nE '#<old-slug>([)"'"'"' >]|$)'
```

This search finds inline links, links with a title, links in `<...>` and reference
definitions. Keep only the matches whose path resolves to the renamed page. Update the
links inside the pages of this batch. List the other links in the batch summary. Do not
edit a page outside the batch.

### 3c. Run the checker

```bash
python3 <plugin_root>/tools/validate_writing_standard.py --default <standard> --preserve-from HEAD --stats <pages of the batch>
```

Fix every `FAIL` and run the command again until it exits 0. You must never add a waiver
to make a check pass. A `WARN` is advice: fix it when a better sentence exists.

The output must have one `STATS` line for each page of the batch, and each line must name
`<standard>`. If a line is missing or names another standard, the checker did not check
that page against `<standard>`. Stop and ask the operator what to do.

The checker can find no page for some link targets: a path from the site root, a target
with encoded characters, or a shortcode it cannot read. It then fails an updated anchor in
that link as `preserve`. In that case, restore the old link and list it in the summary as
an inbound link that you did not update.

### 3d. Check the facts

Run the `fact-keeper` agent once per page. Give it exactly two paths:

1. the original page;
2. the rewritten page.

To make the original, create a baseline directory outside the repository with
`mktemp -d`. Write each page to `<baseline>/<path relative to the toplevel>`, so that two
pages with the same file name (two `index.md` files) do not share one copy:

```bash
git -C <page directory> show HEAD:./<file name> > <baseline>/<path relative to the toplevel>
```

This copy is a baseline for the agent, not a draft.

Fix each fact that the agent marks `changed` or `lost`. If only the operator can decide,
explain the fact in the summary. After the batch, delete the baseline directory.

### 3e. Print the summary

Print one line per page:

```text
<path>: sentences 41 -> 47, avg 24.3 -> 15.8; checker OK; facts kept 18, changed 0, lost 0, added 0; headings changed 1; inbound links listed 2
```

Below the lines, list each fact that the operator must decide and each inbound link that
you did not update.

### 3f. Stop for the operator's approval

Stop for the operator's approval before the next batch. Do not commit for the operator.
Git is the safety net: you write the pages in place, as in the batch mode of
`/post-rewrite`. Do not keep `/tmp` copies of drafts, and do not write `.bak` files.

## Step 4: Finish

After the last batch, tell the operator which pages changed. Also list the pages that you
refused in step 2.
