---
name: blog-post
description: Create a new Hugo blog post in a blog-craft blog. Composes the body and summary from context, generates a cover image from the configured central metaphor, updates the relevant series overview, and runs /media to fill any media markers the body contains.
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

- **Helper script:** `<plugin_root>/tools/blog-post-create.sh` — does the mechanical bits (page bundle, prompts entry, image-gen, overview update). Takes both a prompt-file and a body-file.
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

The body and summary are both written by the agent from available context, not by hand. Survey:

- The most recent commits in the blog repo since the last post in this series (or, if applicable, the linked source repo for what the post chronicles).
- Any user-supplied ticket, feature reference, or notes about what is being chronicled.
- Prior posts in the same series (read a few to match register).
- Read `.blog-craft.yaml::voice` for tone, and `.blog-craft.yaml::metaphor.persona` for narrator stance.

**Body.** Compose a draft body in that voice. Where a screenshot, asciinema recording, or photo would meaningfully advance the post, insert a `<!-- MEDIA: <type> | <description> | <capture instructions> -->` marker — see the blog's `MEDIA-GUIDE.md` for marker syntax. Reserve markers for media that genuinely deepens understanding; do not insert markers for decoration.

**Summary.** Compose a one-sentence summary (≤25 words) for the frontmatter `summary:` field. The summary is what shows up in series indexes, RSS, and search results — it should state what the post is about, not tease at it. Match the blog's voice. Single line, no markdown, no trailing period if the voice avoids them; double-quotes inside the summary are fine (they'll be escaped on insertion).

Show both the draft body and the draft summary to the user and ask:

> Approve body and summary? (y / regen / edit)
> - **y** — proceed
> - **regen** — re-survey context (or take user-provided notes) and recompose both
> - **edit** — let the user paste hand-edited versions

Loop until approved. Save the final approved body to `/tmp/blog-post-body-<timestamp>.md` and the final approved summary to `/tmp/blog-post-summary-<timestamp>.txt` (single line, no surrounding quotes — the helper handles YAML escaping).

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
  /tmp/blog-post-summary-<timestamp>.txt
```

The helper:
1. Creates the page bundle at `<blog_root>/content/docs/<series>/<number>-<slug>/index.md` with weight `<number>+1`, the **approved summary** in the frontmatter, and the **approved body** (markers and all) below it.
2. Appends a `key: <series>-<number>` entry to `<blog_root>/prompt_for_images.yaml`, copying the approved prompt under `prompt: |`.
3. Runs `python scripts/generate-images.py --only <series>-<number>`. Requires PyYAML + Pillow + google-genai installed (see the blog's `README.md` for venv setup). Honors the `<api_key_env>` from Step 7.
4. If `features.series_overview_posts: true`: inserts a numbered list line under `## Series Index` in `00-overview/index.md` and a row under `## Topic / Evolution Map`.

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

### Step 11: Print the preview command and stop

Tell the user:

> Draft created at `<blog_root>/content/docs/<series>/<number>-<slug>/index.md`. Preview with:
>
> ```bash
> cd <blog_root> && hugo server --buildDrafts
> ```

Do **not** auto-launch the server.

## Idempotency and re-runs

- Re-running with the same `<series>/<number>-<slug>` is refused at Step 3.
- The user can manually regenerate just the image (Step 9's regen branch), edit the page bundle by hand, or re-run `/blog-craft:media` separately on the post path.
- The helper's overview-update step is idempotent (same insert won't duplicate), so if the helper crashed midway and you re-run after fixing the page bundle, the overview won't get a second entry.
- `/blog-craft:media` is itself idempotent — re-invoking it after some assets are added fills those without disturbing already-filled or still-empty markers.
