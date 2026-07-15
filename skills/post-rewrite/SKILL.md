---
name: post-rewrite
description: Rewrite an existing blog-craft post into a genuinely educational one. Diagnoses it against the educational-writing methodology (session-narrative, in-jokes, Diátaxis mode-inversion, missing evidence), gathers the evidence the original omitted via the post-researcher subagent, and re-shapes it — leading with the how-to, adding a reference block and a recovery path, keeping the persona as a thin frame and the cover image untouched. Use when an existing post reads like prose about the session that made it instead of something a reader can build/operate/fix from.
user-invocable: true
disable-model-invocation: false
arguments:
  - name: post
    description: "Path to the post's index.md, or `<series>/<NN>-<slug>`."
    required: true
  - name: source
    description: "Optional path/URL of the source repo or feature the post chronicles, for evidence gathering. If omitted, inferred from frontmatter/links or asked."
    required: false
  - name: voice_level
    description: "Optional override for persona thickness: dry | balanced | rich. Defaults to the blog's .blog-craft.yaml voice_level, or balanced."
    required: false
---

# Rewrite a post into something genuinely useful

**Announce at start:** "I'm using post-rewrite to diagnose and rewrite
`<post>` against the educational-writing methodology."

This skill does **not** regenerate the cover image, change the post's number,
weight, or URL, or touch other posts. It rewrites the body and frontmatter of
one post, in place, only after you approve the new draft.

## Plugin internals

- **Methodology (load first):** `<plugin_root>/skills/educational-writing/SKILL.md` and its `references/`. This is the standard you rewrite *to*.
- **Evidence subagent:** `<plugin_root>/agents/post-researcher.md` — read-only, gathers evidence from a source repo.
- **Gate:** `<plugin_root>/tools/validate_educational.py`.

## Procedure

### Step 1: Load the methodology

Read `educational-writing/SKILL.md` and its three references
(`diataxis.md`, `evidence.md`, `checklist.md`). Everything below applies them.

### Step 2: Find the blog and resolve the post

Walk up from CWD for `.blog-craft.yaml` (the **blog root**). If none, refuse:

> **Not in a blog-craft blog.** `cd` to the blog that contains the post.

Resolve `post`: if it's a path to an `index.md`, use it. If it's
`<series>/<NN>-<slug>`, the post is at
`<blog-root>/content/docs/<series>/<NN>-<slug>/index.md`. If it doesn't exist,
refuse and list the posts in that series.

Confirm the post's series is `content_type: posts` (narrative/how-to). If it's a
`papers` or `explainers` series, stop — those have their own skills and
structure; this rewrite doesn't apply.

### Step 3: Diagnose the current post

Read the post. Write a short, concrete diagnosis, citing lines:

- **Failure signatures** (methodology §4): where it's session narrative, in-jokes / "you had to be there", explanation crowding out how-to, assertions without artifacts, missing recovery path, buried commands.
- **Diátaxis inversion**: what mode it *is* vs. what mode a reader needs. Name the target mode(s). (The common finding: "written as explanation-narrative; the reader needs a how-to guide + a reference block.")
- **Missing evidence**: the claims that need artifacts the post doesn't have.

Also run the gate to get the mechanical failures:

```bash
python <plugin_root>/tools/validate_educational.py --config <blog-root>/.blog-craft.yaml <post-path>
```

Show the diagnosis to the user before rewriting.

### Step 4: Gather the missing evidence

Identify the source repo/feature the post chronicles — from the `source` arg,
frontmatter, in-post links, or by asking the user one question if it's not
inferable. Dispatch the **post-researcher** subagent at that target. It **reads
the actual code** (not commit messages or docs alone), reads the repo's design
substrate — `docs/superpowers/{specs,plans}` and
`docs/superpowers/implemented/{specs,plans}` (plus any `docs/investigations/` the
post references), if present — and **cross-checks the spec's intent against what
the code shipped**. It returns a structured evidence brief (design-intent-vs-shipped,
real commands, `file:line`, config values, tests, the failure/recovery path). The
divergences it surfaces are often the post's most useful troubleshooting material.
See `agents/post-researcher.md`.

If the source is unavailable (no repo access), proceed with the evidence already
in the post and the user's input, and **flag** in the draft what still needs live
capture rather than inventing artifacts. Never fabricate a command, output,
`file:line`, or commit.

### Step 5: Determine reader_goal and mode

From the diagnosis + brief, write the `reader_goal` (one line: what the reader
can DO afterward) and pick `diataxis` mode(s). These become frontmatter and
drive the structure.

### Step 6: Rewrite (side-by-side, don't clobber)

Resolve the **voice level** first: the `voice_level` arg, else the blog's
`.blog-craft.yaml::voice_level`, else `balanced`. It sets how thick the persona
frame is (see `educational-writing/references/voice.md`) — a "too dry" complaint
usually means bumping `balanced` warmer, or the blog was left at `dry`.

Compose the new body to the methodology:

- **Set the stage first** (methodology §2a) — open with motivation (the concrete problem, felt), what it solves, and the one load-bearing design choice. Then **name the foundation**: "to build this you need A, B, C" with **links to the earlier posts** where A/B/C were built, rather than re-explaining. A reader must feel oriented, not dropped into `Step 1`.
- **Persona frame at the resolved `voice_level`** — keep the blog's `voice`/`metaphor.persona` register; `dry` = minimal, `balanced` = thin frame + warm orientation + memory-aiding asides, `rich` = voiced throughout but the how-to still leads.
- **Lead with the how-to** — the runnable steps first, the one command that matters in a copy-pasteable block near the top of its section.
- **Reference block** — tabulate the config keys, flags, thresholds, paths a reader looks up.
- **A missteps table** — the design-time wrong turns as *assumed → why wrong → what it cost*, each with enough context to stand alone (`references/evidence.md`). Keep it distinct from the runtime symptom→cause→fix troubleshooting table.
- **Recovery path** — an unmissable "when it breaks, do this" for operational posts.
- **Explanation, labelled** — move the war-story / *why* into a clearly-marked Explanation section (or suggest splitting it into a companion post in the "why" track). Don't delete the interesting story — demote it.
- **Evidence inline** — real commands/output, `file:line`, commit SHAs, test names from the brief. Snippets **expanded/multi-line**, not compressed flow-style; comment non-obvious lines. Every **Verify** step is the real command + its success/failure signature. Mark anything needing live capture with a `<!-- MEDIA: ... -->` marker.

Write the new draft to `/tmp/post-rewrite-<timestamp>.md` (full file: rewritten
frontmatter + body). Preserve from the original frontmatter: `title`, `date`,
`weight`, `tags`, `summary` (update the summary only if it now misdescribes the
post), cover/image fields, and any cross-link fields. **Add** `reader_goal` and
`diataxis`. If the post mirrors code state (no in-post Update logs), also add
`last_updated` + `last_updated_commit` (date + commit URL of the source state you
reconciled to) and a `{{< last-updated >}}` shortcode near the top. Do not change
`weight` or the bundle path.

Show the user the diagnosis recap and the new draft. Ask:

> Approve rewrite? (y / regen / edit)
> - **y** — write it to the post
> - **regen** — re-gather evidence / re-shape and recompose
> - **edit** — paste a hand-edited version

Loop until approved.

### Step 7: Apply

Back up the original to `<post-path>.bak`, then write the approved draft to
`<post-path>`. Tell the user the `.bak` is there to diff/restore.

### Step 8: Fill any new media markers

If the rewrite added `<!-- MEDIA: ... -->` markers, invoke the media skill on the
post:

> /blog-craft:media post=<series>/<NN>-<slug>

If none, skip silently.

### Step 9: Gate + preview

Re-run the gate — it must pass:

```bash
python <plugin_root>/tools/validate_educational.py --config <blog-root>/.blog-craft.yaml <post-path>
```

If it still fails, surface the failures and return to Step 6 (do not leave a post
that fails the gate). On pass, tell the user:

> Rewrote `<post-path>`. Original backed up at `<post-path>.bak`. Preview with:
>
> ```bash
> cd <blog-root> && bash scripts/hugo-serve.sh --buildDrafts
> ```

Do **not** auto-launch the server, regenerate the cover, or commit.

## Notes

- **Non-destructive:** the original is always backed up to `.bak`; the new draft is shown for approval before anything is written.
- **The cover stays.** Rewriting the words doesn't invalidate the art. If the user wants a new cover, that's `/blog-post`'s image flow, run separately.
- **Idempotent:** re-running on an already-rewritten post just re-diagnoses (it'll likely pass the gate) and offers further tightening.
