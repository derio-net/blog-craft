# Using blog-craft on a host: updating a blog and rewriting a post

This is the operator (and agent) runbook for two things: pulling a newer
blog-craft into your setup, and rewriting an existing post with `/post-rewrite`.
The key idea to hold onto: **blog-craft has two update surfaces**, and they
update differently.

| Surface | What's in it | Where it lives | How it updates |
|---|---|---|---|
| **The plugin** | skills (`/blog-post`, `/post-rewrite`, `/educational-writing`, …), the `post-researcher` agent, `tools/` | user-level: `~/.claude/plugins/` | update/reinstall the plugin |
| **Per-blog materialized files** | `assets/css/custom.css` (mermaid theme), `layouts/shortcodes/` (e.g. `last-updated`), blog-side `scripts/` (validators) | *inside each blog repo* | run `/update` **in that blog** |

Updating the plugin does **not** touch a blog's materialized files, and vice
versa. Most "I updated but nothing changed in my blog" confusion is this.

## A. Land a newer blog-craft

1. Merge the change to the plugin's default branch (or install the plugin from a
   branch/tag). A PR against `derio-net/blog-craft`, merged, is the normal path.
2. Update the installed plugin on your host (`/plugin`, or reinstall from the
   marketplace/repo). This refreshes the skills, the `post-researcher` agent, and
   `tools/`.

## B. A brand-new blog

`/bootstrap-blog` already ships the current defaults — the `voice_level` prompt,
the quality gate (default on), and the global mermaid theme. Nothing extra to do.

## C. An existing blog (e.g. to get the mermaid theme + gate)

Run these **in the blog repo** (the one with `.blog-craft.yaml`):

1. `/update` — 3-way-merges the shipped framework/merged files into the blog:
   the new `assets/css/custom.css` (global mermaid theme), the
   `layouts/shortcodes/last-updated.html` shortcode, and
   `scripts/validate_educational.py`. Review the dry-run, then apply.
2. Add the new optional config to `.blog-craft.yaml` (they aren't auto-added):
   ```yaml
   voice_level: balanced          # dry | balanced | rich
   quality:
     enabled: true                # wires the CI gate on content_type: posts
     gate:
       require_reader_goal: true
       require_diataxis_mode: true
       min_command_blocks: 1
       require_actionable_section: true
   ```
   Note: enabling the gate on a blog with **existing** posts that predate it will
   red those posts in CI until they carry `reader_goal` + `diataxis` + an
   actionable section (or `quality_exempt`). Rewrite them (below) before flipping
   `quality.enabled`, or leave it off until they're migrated.
3. Rebuild: `hugo --buildDrafts` — the themed diagrams and the last-updated stamp
   appear now, not before.

## D. Rewrite a post

In the blog repo, with a Claude agent (the plugin installed):

```
/post-rewrite <series>/<NN>-<slug> source=<path-or-repo the post chronicles>
```

- `source` is what feeds the `post-researcher` subagent — usually the repo the
  post is about (often the blog's own source repo). It reads the actual code and
  the design substrate (`docs/superpowers/{specs,plans}`, `implemented/`,
  `docs/investigations/`) and cross-checks intent vs. shipped.
- The skill diagnoses the post, gathers evidence, and re-shapes it at the blog's
  `voice_level` (override per-run: `voice_level=rich`), keeping the persona a thin
  frame and the cover untouched. It's non-destructive — backs up to `.bak`, shows
  the draft for approval, then re-runs the gate.

For a **new** post, `/blog-post` applies the same methodology inline and runs the
gate before it finishes.

## What's a dial vs. what's methodology

- **Deterministic knobs:** `quality.gate.*` (the mechanical floor), and
  `voice` + `voice_level` (the tone — `voice` is the character, `voice_level` is
  how loud it is over the teaching; see
  `skills/educational-writing/references/voice.md`).
- **Everything else** — evidence discipline, Diátaxis mode choice, orientation,
  the missteps table — is methodology the skill applies from
  `skills/educational-writing/`, not a config knob. Prose quality can't be
  mechanized; the gate is the deterministic backstop.
