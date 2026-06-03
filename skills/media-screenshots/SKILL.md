---
name: media-screenshots
description: Fill the screenshot placeholders in a blog post by automatically capturing them from a real browser, then replacing the placeholders with rendered shortcodes. The autonomous-screenshot companion to /media. Use when the user wants to grab the screenshots for a post, fill in the screenshot placeholders, capture the dashboards/web-UIs a post references, or says "take the screenshots for this post", "fill the media placeholders with screenshots", or "screenshot everything this post needs". Works in any blog using the shared <!-- MEDIA: --> placeholder contract (frank's blog and blog-craft blogs alike). Handles only screenshot-type placeholders; /media still covers asciinema, photos, and youtube.
---

# Media Screenshots

The bridge between a post's screenshot placeholders and a real browser. For each
`screenshot` placeholder in a post, this skill: confirms the URL with you,
captures it via the generic `browser-screenshot` skill, drops the PNG at the
placeholder's exact `src=` filename, optimizes it, then replaces the placeholder
with its rendered shortcode.

**Announce at start:** "Using media-screenshots to capture and fill screenshot placeholders in `<post>`."

## Why this is separate from /media

`/media` already inserts assets and records asciinema. What it *doesn't* do is
go get a screenshot for you. This skill does exactly that one thing — drive a
browser to produce the screenshot asset — and then hands off to the same
replacement logic `/media` uses. Keeping it separate keeps `/media` lean and
lets the screenshot path improve on its own.

It is **contract-driven, not blog-specific**: all it needs is a post with the
shared placeholder pair, so it runs in frank's repo-local blog and in any
blog-craft blog without a `.blog-craft.yaml` gate.

## The placeholder contract

Screenshot placeholders are a two-line comment pair:

```
<!-- MEDIA: screenshot | <description> | <capture instructions, often a URL> -->
<!-- {{</* screenshot src="<filename>.png" caption="..." */>}} -->
```

The `src="<filename>.png"` is the pin: produce a file at that exact name in the
post's bundle directory and the replacement just works.

## Workflow

### Step 1 — Locate the post and its screenshot placeholders

If the user named a post, target its bundle directory (the folder containing
`index.md`). Otherwise, scan for screenshot placeholders and let the user pick:

```bash
grep -rn "<!-- MEDIA: screenshot" <content-dir> --include="*.md"
```

(`<content-dir>` is `blog/content` in frank, `content/docs` in a blog-craft
blog. Walk up from the post path if you're unsure where the root is.)

For each screenshot placeholder, read the pair and extract:
- **`src`** — the target filename (from the shortcode line)
- **description** — what the screenshot should show
- **capture instructions** — usually contains a URL and any framing hints

### Step 2 — Confirm the URL and framing with the user (one per placeholder)

Do **not** silently guess URLs. For each screenshot placeholder, show the user
the description + instructions and the URL you parsed (if any), and ask them to
confirm or supply:

- the **URL** to capture
- the **mode**: `viewport` (default, ~1200px), `full` (whole page), or
  `element` (one region — then ask for a CSS selector)
- **dark mode** (default yes for dashboards / the house style)
- whether the target needs **login**, and if so which env vars hold the
  credentials (see the auth note below)

This human-in-the-loop step is deliberate: the post's instructions describe
intent, but the exact route/panel/state is a judgement call the author should
make. Confirm all of them up front so the capture run is unattended.

### Step 3 — Capture each via the browser-screenshot skill

Use the **browser-screenshot** skill for the actual capture. Set `SHOT_OUT` to
the placeholder's `src` inside the bundle so the file lands where the
replacement expects it:

```bash
SHOT_URL="<confirmed url>" \
SHOT_OUT="<post-bundle>/<src-from-placeholder>" \
SHOT_MODE="viewport" SHOT_WIDTH=1200 SHOT_DARK=1 \
  browser-harness < ~/.agents/skills/browser-screenshot/scripts/capture.py
```

For `element` mode add `SHOT_MODE=element SHOT_SELECTOR="<css>"`; for full-page
use `SHOT_MODE=full`. For auth-walled targets pass the `SHOT_LOGIN_*` params
(read browser-screenshot's SKILL.md). On the Mac, bracket the whole batch with
`brave-clawdia` / `brave-clawdia-stop` once — not per shot.

If a capture returns `AUTH_WALL` (exit 3), stop and tell the user which target
needs credentials or a richer login recipe; don't fill that placeholder.

### Step 4 — Optimize each PNG (500KB budget)

```bash
asset="<post-bundle>/<src>"
[ "$(wc -c < "$asset")" -gt 512000 ] && echo "WARN: over 500KB"
if command -v pngquant >/dev/null; then
  pngquant --quality=65-80 --strip --force --output "$asset" "$asset"
elif command -v optipng >/dev/null; then
  optipng -o3 "$asset"
else
  echo "WARN: no pngquant/optipng — skipping optimization"
fi
file "$asset"   # expect: PNG image data
```

If it's still over budget after optimization, recapture with `SHOT_SCALE=1`
(if you used 2) or `viewport` instead of `full`.

### Step 5 — Replace the placeholders with shortcodes

Run the bundled, idempotent helper. It replaces every placeholder pair **whose
asset is now present** and leaves the rest untouched:

```bash
python3 <skill-dir>/scripts/media-fill.py "<post-bundle>"
```

(`<skill-dir>` is this skill's directory. The bundled `media-fill.py` mirrors
blog-craft's `tools/media-fill.py`, so this works even in frank's blog where
that tool isn't on disk.)

Expected output: `filled N placeholder(s) in <bundle>/index.md`, with any
still-missing assets reported as skipped.

### Step 6 — Verify the Hugo build

Find the blog root (the dir with `hugo.toml`/`config.toml`/`.blog-craft.yaml`)
and build:

```bash
( cd "<blog-root>" && hugo --minify 2>&1 | tail -5 )
```

Confirm exit 0 and no `ERROR` lines. Suggest the user preview with their
blog's dev-server command if they want to eyeball the rendered figures.

## Standards (shared with /media)

- **PNG**: max 500KB after optimization; kebab-case filename matching `src=`
- **Caption**: keep the placeholder's `caption=`; frank requires one, blog-craft
  recommends it
- **Dark mode**: preferred for dashboards and the house screenshot style
- **Only screenshots**: leave `asciinema`/`photo`/`youtube` placeholders for
  `/media` — this skill ignores them

## Reference

- Generic capture engine: the **browser-screenshot** skill (modes, auth, gotchas)
- Replacement logic: `scripts/media-fill.py` (this skill) — mirror of
  blog-craft `tools/media-fill.py`
- Placeholder format: `<!-- MEDIA: <type> | <description> | <instructions> -->`
