---
name: blog-craft-media
description: Capture, optimize, and insert media (screenshots, CLI animations, photos) into blog-craft posts. Fills <!-- MEDIA: ... --> placeholders with rendered Hugo shortcodes.
user-invocable: true
disable-model-invocation: false
arguments:
  - name: post
    description: "Post path relative to content/docs/ (e.g. tutorials/07-monitoring). If omitted, lists all posts with remaining placeholders."
    required: false
---

# Fill media placeholders in a blog-craft post

Walk through every `<!-- MEDIA: ... -->` placeholder in a post, help the user capture/record/optimize the asset, then run the placeholder-replacement helper.

**Announce at start:** "I'm using media to fill placeholders in `<post>`."

## Plugin internals

- **Helper:** `<plugin_root>/tools/media-fill.py` — scans a post bundle and replaces every placeholder whose referenced asset (`src="..."`) is present on disk. Skips placeholders whose assets are missing. Idempotent.

## Discovery contract

Walk up from CWD looking for `.blog-craft.yaml`. The directory containing it is the **blog root**. If not found, refuse:

> **Not in a blog-craft blog.** Run `/bootstrap-blog` first or `cd` to a blog-craft repo.

## Procedure

### Step 1: Identify target post(s)

If `post` argument is supplied, target `<blog_root>/content/docs/<post>/index.md`. Confirm it exists; otherwise refuse.

If `post` is omitted, scan every post and present a checklist:

```bash
grep -rn "<!-- MEDIA:" "<blog_root>/content/docs" --include="*.md"
```

Show the user a summary grouped by post (path → number of remaining placeholders). Ask which one to work on.

### Step 2: For each placeholder, walk the user through capture

Read the placeholder pair:

```
<!-- MEDIA: <type> | <description> | <capture instructions> -->
<!-- {{</* <type> src="<filename>" caption="..." */>}} -->
```

`<type>` is one of `screenshot`, `asciinema`, `photo`, `youtube`. The `<description>` and `<capture instructions>` tell the user what's needed.

Branch by type:

#### Screenshots, photos

1. Show the user the description + instructions verbatim.
2. Remind them: dark mode preferred, ~1200px window width, PNG, crop to relevant area, kebab-case filename matching the placeholder's `src=`.
3. Wait for them to capture and confirm the file is at `<post-bundle>/<filename>`.

> **Auto-capture instead of waiting for a manual screenshot:** when the
> placeholder's instructions point at a URL/web-UI, use the `media-screenshots`
> skill — it drives a real browser (via `browser-screenshot`) to capture each
> screenshot placeholder, drops the PNG at the `src=` filename, and runs the
> same fill step. This `/media` flow still handles asciinema, photos, and youtube.

#### CLI animations (asciinema)

The skill can record these for the user automatically when they have a scripted command:

1. Confirm `asciinema` is on PATH (`which asciinema`). If not, instruct the user to install it (`brew install asciinema` or `pip install asciinema`).
2. Ensure the user's shell has whatever env vars the recorded commands depend on. **The skill does not source any env files** — Frank's pattern of `source .env` / `source .env_hop` is Frank-specific and intentionally dropped here.
3. Record:
   ```bash
   asciinema rec --cols 120 --rows 30 --idle-time-limit 2 \
     --command "<commands separated by ; >" \
     "<post-bundle>/<filename>.cast"
   ```
4. Validate the resulting `.cast` file: it must be valid JSON with header `version: 2`. Warn if the recording exceeds 60 seconds.

#### YouTube

No capture step — the user supplies the video ID. The shortcode is `{{< youtube <id> >}}` (Hugo built-in). Update the placeholder by hand to substitute the ID, or treat as a custom case (the helper will fill once the comment is well-formed).

### Step 3: Validate and optimize the asset

For PNG screenshots/photos, run a size check and optimize if available:

```bash
# Warn if over 500KB
size=$(wc -c < "<asset>")
[[ $size -gt 512000 ]] && echo "WARN: $size bytes (over 500KB)"

# Optimize (use whichever is installed)
if command -v pngquant; then
  pngquant --quality=65-80 --strip --force --output "<asset>" "<asset>"
elif command -v optipng; then
  optipng -o3 "<asset>"
else
  echo "WARN: neither pngquant nor optipng found — skipping optimization"
fi

# Sanity-check it's still a PNG
file "<asset>"   # expect "PNG image data"
```

For `.cast` files: validate JSON structure (`python3 -c "import json; json.load(open('<asset>'))"`), check header for `"version": 2`.

For all assets: confirm the filename is kebab-case and matches the placeholder's `src=`.

### Step 4: Run the helper

```bash
python3 <plugin_root>/tools/media-fill.py "<blog_root>/content/docs/<post>"
```

Output:
- `filled N placeholder(s) in <path>` — N placeholders successfully replaced
- `skipped N placeholder(s) — asset(s) missing` — placeholders left as-is because their assets weren't present
- `no <!-- MEDIA: --> placeholders found` — nothing to do

The helper is idempotent: re-running it after some assets are added will fill those without disturbing already-filled or still-empty ones.

### Step 5: Verify Hugo build

```bash
( cd "<blog_root>" && hugo --minify --quiet )
```

Confirm exit code 0 and no `ERROR` lines. Tell the user to preview with `bash scripts/hugo-serve.sh --buildDrafts` if they want to see the rendered output (the wrapper handles Hextra's Go-module PATH requirement — see `scripts/hugo-serve.sh` header).

## Standards

- **PNG screenshots/photos**: max 500KB after optimization
- **`.cast` files**: valid asciinema v2 JSON, under 60 seconds preferred
- **Filenames**: kebab-case, descriptive (`grafana-node-metrics.png`, not `screenshot-1.png`)
- **Captions**: strongly recommended for screenshots, but not enforced. The Hugo `screenshot` shortcode renders no `<figcaption>` element when `caption=` is absent. The helper only requires `src=`
- **Dark mode**: preferred for screenshots; light is acceptable
- **Recording dimensions**: default 120×30 unless content needs more

## Reference

- Placeholder format: `<!-- MEDIA: <type> | <description> | <capture instructions> -->`
- Shortcode source: `<blog_root>/layouts/shortcodes/screenshot.html`, `<blog_root>/layouts/shortcodes/asciinema.html`
- Capture conventions and examples: `<blog_root>/MEDIA-GUIDE.md`
