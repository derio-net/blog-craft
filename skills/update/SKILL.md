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
| `merged`    | **3-way merge** — the base (below) vs your on-disk copy vs the new render |

The dry-run prints the per-path plan and a tally. On `--apply`, clean merges are
written and **conflicts are surfaced for you to resolve** — never auto-resolved.
After applying, bump `blog_craft_version` and verify with `hugo --buildDrafts`.

| Outcome | Means |
|---|---|
| `ADD` / `REPLACE` | the file is written |
| `MERGE` | the 3-way merge changed the file |
| `NOOP` | the merge resolved entirely in your copy's favour — **nothing written** |
| `CONFLICT` | left untouched; resolve by hand and re-run |

A `NOOP` on a path you *expected* to change is the signal that the base is
wrong — usually a stale or missing sync snapshot. See below.

### The base — and why `.blog-craft.sync.yaml` matters

The base answers *"what did blog-craft last give this blog?"*, which is
`render(config_at_last_sync, templates_at_recorded_version)`. Both halves are
recorded, in two different places:

- **which templates** — `blog_craft_version` in `.blog-craft.yaml` (a git ref);
- **which config** — `.blog-craft.sync.yaml`, the snapshot written by bootstrap
  and by every conflict-free `--apply`. **Commit it.**

Skip the snapshot and the base has to be rendered with your *current* config —
so anything you changed since the last sync appears in the base as content
blog-craft supposedly already shipped, the merge reads your on-disk file as a
deliberate deletion, and the change is dropped. Enabling a `features.*` flag
became a silent no-op for every `merged` path this way
(derio-net/blog-craft#60). `/update` warns whenever it falls back, and records
the snapshot so the next run is exact.

### The backfilling run is your one chance to spot old drift

Recording the first snapshot fixes every *future* update. What it cannot do is
undo a drop that already happened: it asserts "this blog is synced to this
config" over a tree that may not match, so from the next run onward such a path
is an ordinary `NOOP` with no warning on it — the tool has stopped disagreeing.

So the backfilling run names them. On the one `--apply` that both falls back
*and* records a snapshot, `/update` lists by destination every `merged` path its
fallback base resolved to `NOOP`, and tells you how to check:

```bash
bash <blog-craft>/tools/bootstrap-render.sh <config> /tmp/bc-fresh
diff /tmp/bc-fresh/<staging-relative path> <your copy>
```

A difference there is a change blog-craft shipped and an earlier, pre-#60 run
dropped — copy it across before it becomes invisible. No difference means the
`NOOP` was the harmless kind. The warning is silent on snapshot-backed runs and
on fallback runs whose plan had no `NOOP`s: one that fired on clean plans is one
you would learn to skip.

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

A scoped apply deliberately **does not** update `.blog-craft.sync.yaml`: some
paths were synced and some were not, so recording the config as this blog's sync
state would overstate what landed and give every out-of-scope path a base built
from a config it was never rendered with. Run an unscoped `--apply` to record a
sync.

## 2b. Adopting a blog that was never bootstrapped

A blog that predates blog-craft (or vendored its scripts by hand) has no
rendered baseline. That's fine: `framework` paths replace/add regardless of
base; `merged` paths without a base surface as `conflict (no base to merge
from)` and are left untouched — resolve by inspection or scope the run with
`--only`. After the first apply, record `blog_craft_version` in
`.blog-craft.yaml` so future updates get a real 3-way base.

A blog synced before the snapshot existed is the milder version of the same
thing: it updates normally, warns that its base is approximate, and the first
conflict-free `--apply` backfills `.blog-craft.sync.yaml`. If you are enabling a
feature on such a blog, run `--apply` once to record the snapshot **before**
editing the config — otherwise that first toggle takes the fallback path.

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

- Always review the **dry-run** first — and read the `NOOP` lines, not just the
  `MERGE` ones.
- The base is re-rendered from the recorded release (a git ref) and the sync
  snapshot. No baseline *tree* is stored, so keep `blog_craft_version` accurate
  and keep `.blog-craft.sync.yaml` committed.
- Conflicts leave the on-disk file untouched **and leave the snapshot alone** —
  a half-applied plan must not claim the blog is synced. Resolve, then re-run.
