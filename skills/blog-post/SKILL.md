---
name: blog-post
description: Create a new Hugo blog post in a blog-craft blog. Generates a cover image from the configured central metaphor and updates the relevant series overview.
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

- **Helper script:** `<plugin_root>/tools/blog-post-create.sh` — does the mechanical bits (page bundle, prompts entry, image-gen, overview update).
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

### Step 4: Collect the per-post image brief

Ask the user:

> What should the cover image show? Give me one paragraph describing the scene — what `<persona>` is doing, the setting, the mood. I'll wrap it with the standing style/persona/visual constraints from `.blog-craft.yaml` to compose the full Gemini prompt.

Capture the user's reply as `<brief>`.

### Step 5: Compose the full image prompt

Read `metaphor` from `.blog-craft.yaml`. Concatenate, in order, separated by blank lines:

1. `metaphor.base_style`
2. `metaphor.persona`
3. The bullets in `metaphor.visual_constants`, one per line, prefixed with `- `
4. `<brief>` (the user's per-post scene)
5. `metaphor.reference_guidance`

Show the full composed prompt to the user and ask:

> Approve this prompt? (y / regen / edit)
> - **y** — proceed to image generation
> - **regen** — ask for a new brief and recompose
> - **edit** — let the user paste a hand-edited version

Repeat until the user approves. Save the final approved text to `/tmp/blog-post-prompt-<timestamp>.txt`.

### Step 6: Confirm the API key is in the environment

Read `image_gen.api_key_env` from `.blog-craft.yaml` (default `GEMINI_API_KEY`). Check whether it's set in the current shell (e.g. `printenv $api_key_env` returns non-empty). If missing:

> I need your `<api_key_env>` value for image generation. Paste it here and I'll export it for this session only — I will not write it to disk.

Capture and `export <api_key_env>=<value>` for the helper invocation.

### Step 7: Run the helper

```bash
bash <plugin_root>/tools/blog-post-create.sh \
  <blog_root> <series> <number> <slug> <title> /tmp/blog-post-prompt-<timestamp>.txt
```

The helper:
1. Creates the page bundle at `<blog_root>/content/docs/<series>/<number>-<slug>/index.md` with weight `<number>+1` (preserves leading zeros for parsing) and a media-placeholder reminder comment.
2. Appends a `key: <series>-<number>` entry to `<blog_root>/prompt_for_images.yaml`, copying the approved prompt under `prompt: |`.
3. Runs `python scripts/generate-images.py --only <series>-<number>`. Requires PyYAML + Pillow + google-genai installed (see the blog's `README.md` for venv setup). Honors the `<api_key_env>` from Step 6.
4. If `features.series_overview_posts: true`: inserts a numbered list line under `## Series Index` in `00-overview/index.md` and a row under `## Topic / Evolution Map`.

If the helper exits non-zero, surface the error and stop.

### Step 8: Show the cover and offer regen

Display the generated cover at `<blog_root>/static/images/<series>-<number>-cover.png`. Ask:

> Cover looks right? (y / regen)
> - **y** — done
> - **regen** — re-run only image-gen with the same prompt (or a tweaked one):
>   ```bash
>   ( cd <blog_root> && python scripts/generate-images.py --only <series>-<number> )
>   ```

### Step 9: Print the preview command and stop

Tell the user:

> Draft created at `<blog_root>/content/docs/<series>/<number>-<slug>/index.md`. Add `<!-- MEDIA: ... -->` placeholders as you write; run `/media post=<series>/<number>-<slug>` to fill them later. Preview with:
>
> ```bash
> cd <blog_root> && hugo server --buildDrafts
> ```

Do **not** auto-launch the server. Do **not** insert media placeholders for the user — they go in as the author writes.

## Idempotency and re-runs

- Re-running with the same `<series>/<number>-<slug>` is refused at Step 3.
- The user can manually regenerate just the image (Step 7's regen branch) or hand-edit the page bundle and rerun nothing.
- The helper's overview-update step is idempotent (same insert won't duplicate), so if the helper crashed midway and you re-run after fixing the page bundle, the overview won't get a second entry.
