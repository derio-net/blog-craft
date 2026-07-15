---
name: blog-post
description: Create a new Hugo blog post in a blog-craft blog. Composes the body and summary from context, generates a cover image from the configured central metaphor, and runs /media to fill any media markers the body contains. The series overview lists the new post automatically (page-derived).
user-invocable: true
disable-model-invocation: false
arguments:
  - name: series
    description: "Series key — must match a series[].key in .blog-craft.yaml"
    required: true
  - name: number
    description: "Post number (zero-padded, e.g. 07)"
    required: true
  - name: slug
    description: "URL slug (kebab-case)"
    required: true
  - name: title
    description: "Post title"
    required: true
---

# Create a new blog-craft post

**Announce at start:** "I'm using blog-post to scaffold post `<NN>-<slug>` in the `<series>` series."

## Plugin internals

- **Helper script:** `<plugin_root>/tools/blog-post-create.sh` — does the mechanical bits (page bundle, prompts entry, image-gen). Takes both a prompt-file and a body-file.
- **YAML reader:** `<plugin_root>/tools/render-template/main.go` `--get-bool` mode (used by helper).

## Procedure

### Step 1: Find and validate the blog

Walk up from CWD looking for `.blog-craft.yaml`. If not found anywhere up to root, refuse:

> **Not in a blog-craft blog.** Run `/bootstrap-blog` first, or `cd` to a blog-craft repo (one that contains `.blog-craft.yaml` at its root).

The directory containing `.blog-craft.yaml` is the **blog root**. Cache that path.

### Step 2: Validate the `series` arg

Read `.blog-craft.yaml` and check that the `series` arg is one of the `series[].key` values. If not:

> Series `<series>` is not configured in this blog. Valid keys: `<list>`.

### Step 3: Validate other args

- `number` — must match `^[0-9]{2,3}$` (zero-padded).
- `slug` — must match `^[a-z][a-z0-9-]*$` (kebab-case).
- `title` — non-empty.

If `<blog-root>/content/docs/<series>/<number>-<slug>/` already exists, refuse:

> Post `<series>/<number>-<slug>` already exists at `<path>`. Pick a different number or slug.

### Step 4: Compose the post body and summary

**Load the methodology first.** Read `<plugin_root>/skills/educational-writing/SKILL.md`
and its `references/`. It is the standard this post is held to and the gate in
Step 10 enforces it. In short: pick the Diátaxis mode before writing, ground
every claim in a citable artifact, and keep the persona as a thin frame — never
prose about the session that generated the post.

The body and summary are both written by the agent from available context, not by hand. Survey:

- The most recent commits in the blog repo since the last post in this series (or, if applicable, the linked source repo for what the post chronicles).
- Any user-supplied ticket, feature reference, or notes about what is being chronicled.
- Prior posts in the same series (read a few to match register).
- Read `.blog-craft.yaml::voice` for tone, and `.blog-craft.yaml::metaphor.persona` for narrator stance.

**Gather evidence.** If the post chronicles work in a source repo (the classic
building/operating case), dispatch the `post-researcher` subagent
(`<plugin_root>/agents/post-researcher.md`) at that repo/feature. It **reads the
actual code** (not commit messages or docs alone), reads the repo's design
substrate — `docs/superpowers/{specs,plans}` and
`docs/superpowers/implemented/{specs,plans}` (plus any `docs/investigations/` the
post references), if present — **cross-checks the spec against what shipped**, and
returns a structured evidence brief (design-intent-vs-shipped, real commands,
`file:line`, config values, tests, the failure/recovery path) so the post cites
instead of asserts and heavy exploration stays out of this context. Never
fabricate a command, output, `file:line`, or commit; mark anything needing live
capture with a MEDIA marker.

**Reader goal + mode.** State the **`reader_goal`** in one line (what the reader
can *do* after reading) and pick the **`diataxis`** mode(s) (one or more of
tutorial / how-to / reference / explanation). If you can't state the reader_goal,
the post has no job yet — go back to the evidence. These become frontmatter.

**Body.** Compose a draft body to the methodology. **Set the stage first**
(methodology §2a): open with the motivation (the concrete problem, felt), what it
solves, and the one load-bearing design choice, then **name the foundation** ("to
follow this you need A, B, C") with links to the earlier posts where A/B/C were
built — a reader must feel oriented, not dropped into `Step 1`. Then **lead with
the how-to** / runnable steps (the one command that matters in a copy-pasteable
block near the top of its section), tabulate reference facts, include an
unmissable recovery path for operational posts, and demote the war-story / *why*
into a clearly-labelled Explanation section.

**Seed `voice_level` if missing:**

```
python3 <plugin_root>/tools/seed_config.py --config <blog_root>/.blog-craft.yaml \
    --key voice_level --default balanced \
    --comment "How thick the persona frame is." \
    --values "dry,balanced,rich"
```

Then frame at the blog's `voice_level` (`dry`/`balanced`/`rich`, default `balanced`
— see `<plugin_root>/skills/educational-writing/references/voice.md`): keep the
persona a frame, never the substance. Write code snippets **expanded/multi-line**
(not compressed flow-style) with non-obvious lines commented, and make every
**Verify** step the real command + its success/failure signature. Use ` ```mermaid `
for diagrams, not hand-drawn ASCII (themed + aligned by default). For a
build/operating chronicle, report what *we* did (first-person-plural past) rather
than bare imperatives. Where a screenshot, asciinema recording, or photo would
meaningfully advance the post, insert a
`<!-- MEDIA: <type> | <description> | <capture instructions> -->` marker — see the
blog's `MEDIA-GUIDE.md`. Reserve markers for media that genuinely deepens
understanding; do not insert markers for decoration.

**Summary.** Compose a one-sentence summary (≤25 words) for the frontmatter `summary:` field. The summary is what shows up in series indexes, RSS, and search results — it should state what the post is about, not tease at it. Match the blog's voice. Single line, no markdown, no trailing period if the voice avoids them; double-quotes inside the summary are fine (they'll be escaped on insertion).

Show the draft body, the draft summary, and the proposed `reader_goal` + `diataxis` to the user and ask:

> Approve body, summary, reader_goal and mode? (y / regen / edit)
> - **y** — proceed
> - **regen** — re-survey context (or take user-provided notes) and recompose
> - **edit** — let the user paste hand-edited versions

Loop until approved. Save the final approved body to `/tmp/blog-post-body-<timestamp>.md`, the final approved summary to `/tmp/blog-post-summary-<timestamp>.txt`, and the final approved reader_goal to `/tmp/blog-post-readergoal-<timestamp>.txt` (each single line where noted, no surrounding quotes — the helper handles YAML escaping). Keep the approved `diataxis` mode(s) as a comma-separated string (e.g. `how-to,reference`) for Step 8.

### Step 5: Collect the per-post image brief

Now that the body is approved, propose a one-paragraph cover-image scene that matches what the post is about — `<persona>`'s posture, the setting, the mood. Show the proposal and ask:

> Cover scene brief? (y to use this proposal / paste your own / regen for a different proposal)

Capture the final brief as `<brief>`.

### Step 6: Compose the full image prompt

Read `metaphor` from `.blog-craft.yaml`. Concatenate, in order, separated by blank lines:

1. `metaphor.base_style`
2. `metaphor.persona`
3. The bullets in `metaphor.visual_constants`, one per line, prefixed with `- `
4. `<brief>` (the per-post scene)
5. `metaphor.reference_guidance`

Show the full composed prompt to the user and ask:

> Approve this prompt? (y / regen / edit)
> - **y** — proceed to image generation
> - **regen** — ask for a new brief and recompose
> - **edit** — let the user paste a hand-edited version

Repeat until the user approves. Save the final approved text to `/tmp/blog-post-prompt-<timestamp>.txt`.

### Step 7: Confirm the API key is in the environment

Read `image_gen.api_key_env` from `.blog-craft.yaml` (default `GEMINI_API_KEY`). Check whether it's set in the current shell (e.g. `printenv $api_key_env` returns non-empty). If missing:

> I need your `<api_key_env>` value for image generation. Paste it here and I'll export it for this session only — I will not write it to disk.

Capture and `export <api_key_env>=<value>` for the helper invocation.

### Step 8: Run the helper

```bash
bash <plugin_root>/tools/blog-post-create.sh \
  <blog_root> <series> <number> <slug> <title> \
  /tmp/blog-post-prompt-<timestamp>.txt \
  /tmp/blog-post-body-<timestamp>.md \
  /tmp/blog-post-summary-<timestamp>.txt \
  /tmp/blog-post-readergoal-<timestamp>.txt \
  "<diataxis>"    # comma-separated modes from Step 4, e.g. how-to,reference
```

The helper:
1. Creates the page bundle at `<blog_root>/content/docs/<series>/<number>-<slug>/index.md` with weight `<number>+1`, the **approved summary**, **`reader_goal`**, and **`diataxis`** in the frontmatter, and the **approved body** (markers and all) below it.
2. Appends a `key: <series>-<number>` entry to `<blog_root>/prompt_for_images.yaml`, copying the approved prompt under `prompt: |`.
3. Runs `python scripts/generate-images.py --only <series>-<number>`. Requires PyYAML + Pillow + google-genai installed (see the blog's `README.md` for venv setup). Honors the `<api_key_env>` from Step 7.
4. Does **not** touch the series overview — its `{{< series-index >}}` shortcode lists the new post automatically on the next Hugo build (page-derived, always in sync).

If the helper exits non-zero, surface the error and stop.

### Step 9: Show the cover and offer regen

Display the generated cover at `<blog_root>/static/images/<series>-<number>-cover.png`. Ask:

> Cover looks right? (y / regen)
> - **y** — proceed to media fill
> - **regen** — re-run only image-gen with the same prompt (or a tweaked one):
>   ```bash
>   ( cd <blog_root> && python scripts/generate-images.py --only <series>-<number> )
>   ```

### Step 10: Run /media to fill any markers

If the approved body contained at least one `<!-- MEDIA: ... -->` marker, invoke the media skill on the new post:

> /blog-craft:media post=<series>/<number>-<slug>

This walks each marker, helps the user capture/record/optimize the asset, and replaces the markers with rendered Hugo shortcodes (see `<plugin_root>/skills/media/SKILL.md`).

If the body contained no markers, skip this step silently — there is nothing to fill.

### Step 11: Run the quality gate

Run the educational-writing gate on the new post:

```bash
python <plugin_root>/tools/validate_educational.py --config <blog_root>/.blog-craft.yaml \
    <blog_root>/content/docs/<series>/<number>-<slug>/index.md
```

It checks `reader_goal`, `diataxis`, at least one command/output block, and an
actionable section (Reproduce / Runbook / Steps / Verify / Recover). If it fails,
surface the failures and return to Step 4 to strengthen the draft — do not leave a
post that fails the gate. On pass, continue. (A genuinely non-teaching post — a
pure announcement — may carry `quality_exempt: <reason>` in frontmatter instead;
use rarely.)

### Step 12: Print the preview command and stop

Tell the user:

> Draft created at `<blog_root>/content/docs/<series>/<number>-<slug>/index.md`. Preview with:
>
> ```bash
> cd <blog_root> && bash scripts/hugo-serve.sh --buildDrafts
> ```

Do **not** auto-launch the server.

## Idempotency and re-runs

- Re-running with the same `<series>/<number>-<slug>` is refused at Step 3.
- The user can manually regenerate just the image (Step 9's regen branch), edit the page bundle by hand, or re-run `/blog-craft:media` separately on the post path.
- The series overview needs no maintenance — it derives its index from the pages that exist, so a crashed/re-run helper, a hand-created post, or a deleted post are all reflected on the next build with no manual edit.
- `/blog-craft:media` is itself idempotent — re-invoking it after some assets are added fills those without disturbing already-filled or still-empty markers.
