---
name: update
description: Non-destructively update an existing blog-craft blog to the latest blog-craft. Migrates the config up the schema ladder, re-renders to staging, and 3-way-merges shipped changes into the blog — surfacing conflicts, never clobbering operator edits. Use when pulling a newer blog-craft into a blog, or when .blog-craft.yaml is behind the current schema version.
---

# Update a blog-craft blog

Two axes move independently: the **config schema** (`version:`) and the
**blog-craft release** (`blog_craft_version:`). Updating handles both,
non-destructively.

## 1. Migrate the config (schema ladder)

```bash
python <blog-craft>/tools/migrate_config.py --check .blog-craft.yaml   # is it behind?
python <blog-craft>/tools/migrate_config.py .blog-craft.yaml           # upgrade (writes .bak)
```

Applies `migrations/NNN_to_MMM.py` in order from the config's `version:` to the
latest — pure, idempotent, and non-destructive (a `.bak` is written).

## 2. Re-apply blog-craft (3-way merge)

```bash
python <blog-craft>/tools/update.py --config .blog-craft.yaml --blog .           # dry-run
python <blog-craft>/tools/update.py --config .blog-craft.yaml --blog . --apply   # apply
```

Renders to a staging tree and classifies every path via the manifest:

| Class | Action |
|---|---|
| `framework` | **replace** (shipped; overwritten) |
| `content`   | **leave** (your posts, images, config, data) |
| `merged`    | **3-way merge** — base (re-rendered at the recorded `blog_craft_version`) vs your on-disk copy vs the new render |

The dry-run prints the per-path plan. On `--apply`, clean merges are written and
**conflicts are surfaced for you to resolve** — never auto-resolved. After
applying, bump `blog_craft_version` and verify with `hugo --buildDrafts`.

**Path mapping (site_dir blogs).** Destinations honour the blog's config: the
Hugo site's paths land under `site_dir` (a blog with `.blog-craft.yaml` at the
repo root and the site under `blog/` gets `blog/scripts/…`, `blog/layouts/…`),
while config-rooted paths follow their declared locations (`.reference-pool/**`
→ `image.reference_pool`, `prompt_for_images.yaml` → `image.prompts_file`).
`--blog` always points at the **config root**, not the site dir.

**Scoping.** `--only '<glob>'` (repeatable, staging-relative) limits the plan —
the way to migrate just the image machinery into an existing blog:

```bash
python <blog-craft>/tools/update.py --config .blog-craft.yaml --blog . \
    --only 'scripts/**' --apply
```

## 2b. Adopting a blog that was never bootstrapped

A blog that predates blog-craft (or vendored its scripts by hand) has no
rendered baseline. That's fine: `framework` paths replace/add regardless of
base; `merged` paths without a base surface as `conflict (no base to merge
from)` and are left untouched — resolve by inspection or scope the run with
`--only`. After the first apply, record `blog_craft_version` in
`.blog-craft.yaml` so future updates get a real 3-way base.

**Parity check (image machinery).** Before migrating, snapshot every composed
prompt; after, diff — migration must not change generation:

```bash
mkdir -p /tmp/prompts-before /tmp/prompts-after
for k in $(python <site_dir>/scripts/generate-images.py --config .blog-craft.yaml --list); do
  python <site_dir>/scripts/generate-images.py --config .blog-craft.yaml --print-prompt "$k" > "/tmp/prompts-before/$k.txt"
done
# ... migrate (config ladder + scoped apply) ... then re-run into /tmp/prompts-after/
diff -r /tmp/prompts-before /tmp/prompts-after     # MUST be empty
python <site_dir>/scripts/generate-images.py --config .blog-craft.yaml --dry-run   # payload listing — compare before/after too
```

After updating, an existing blog often needs two follow-ups the merge can't do:
add the optional `quality` + `voice_level` blocks to `.blog-craft.yaml`, and
`hugo --buildDrafts` to pick up the new `custom.css` (mermaid theme) and
shortcodes. Seed `voice_level` with:

```
python3 <plugin_root>/tools/seed_config.py --config <blog_root>/.blog-craft.yaml \
    --key voice_level --default balanced \
    --comment "How thick the persona frame is." \
    --values "dry,balanced,rich"
```

The full host runbook — including rewriting existing posts to pass a newly-enabled
gate — is `docs/USING-ON-A-HOST.md`.

## Guardrails

- Always review the **dry-run** first.
- The base is recovered by re-rendering at the recorded release (a git tag) — no
  per-repo baseline is stored, so keep `blog_craft_version` accurate.
- Conflicts leave the on-disk file untouched; resolve, then re-run.
