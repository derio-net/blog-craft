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

Paths are relative to wherever you run it — the documented form above works from
the blog root.

Renders to a staging tree and classifies every path via the manifest:

| Class | Action |
|---|---|
| `framework` | **replace** (shipped; overwritten) |
| `content`   | **leave** (your posts, images, config, data) |
| `merged`    | **3-way merge** — base (re-rendered at the recorded `blog_craft_version`) vs your on-disk copy vs the new render |

The dry-run prints the per-path plan. On `--apply`, clean merges are written and
**conflicts are surfaced for you to resolve** — never auto-resolved. After
applying, bump `blog_craft_version` and verify with `hugo --buildDrafts`.

### Where each path lands (`site_dir` blogs)

`--blog` always points at the **config root**, not the site dir. From there,
`templates/manifest.yaml`'s `roots:` section answers, per path, the question
that decides its destination:

> **Who defines this path's location — the Hugo site, or a tool that reads it
> from the repository root?**

| Root | Destination | Examples |
|---|---|---|
| `site` | under `site_dir` | `layouts/**`, `scripts/**`, `content/**`, `hugo.toml`, `.gitignore` |
| `repo` | the config root, unprefixed | `.github/**`, `.claude/**`, `.blog-craft.yaml` |

The distinction is **not** "is it a dotfile". A nested `.gitignore` governs its
own subtree, so it is site-rooted. GitHub Actions loads workflows from
`<repo>/.github/workflows/` and nowhere else, and Claude Code's hookify globs
`.claude/hookify.*.local.md` from the project root, so both are repo-rooted —
placing them under `site_dir` produces a file that is not an error and not a
workflow, just inert (blog-craft#61).

Two repo-rooted paths are additionally renamed by your config:
`.reference-pool/**` → `image.reference_pool`, `prompt_for_images.yaml` →
`image.prompts_file`.

### Relocation — when a path's home changed

When a release moves a path (a new root, a rename, or both), `/update` **moves
your copy** rather than adding a fresh one beside it:

```
RELOCATE blog/.github/workflows/blog-ci.yml -> .github/workflows/blog-ci.yml [merged]
PRUNE    blog/.hookify.warn-hextra-weight-zero.md  (stale — now at .claude/hookify.warn-hextra-weight-zero.local.md) [framework]
```

- `RELOCATE` — the file moves. Your edits come with it: the old copy is the
  `local` side of the 3-way merge, so a `MERGE` line for a relocated path means
  your changes are being carried to the new destination.
- `PRUNE` — a correct file already sits at the new destination and the stale
  duplicate is removed.
- On a **conflict**, nothing is written and **nothing is removed** — both copies
  stay and both are named, so you can see there are two before resolving.

A re-run after a successful apply plans no further relocation. The dry-run is
the migration notice — read it before applying.

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
