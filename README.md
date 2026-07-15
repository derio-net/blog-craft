# blog-craft

Portable teaching-blog scaffolding and authoring skills for [Claude Code](https://claude.ai/code).

## What is blog-craft

blog-craft is a Claude Code plugin of skills for the lifecycle of a teaching-style blog:

- **`/bootstrap-blog`** — wizard that scaffolds a fresh Hugo + Hextra blog with a custom central metaphor, configurable series structure ("tracks"), and an image-generation pipeline. Run once per new blog.
- **`/blog-post`** — creates a new post in the relevant series, composes a Gemini image prompt from the per-blog metaphor, generates the cover, and updates the series overview. Applies the educational-writing methodology and runs the quality gate. Run per post.
- **`/media`** — finds `<!-- MEDIA: ... -->` placeholders in drafts and fills them by capturing/optimizing assets and rendering the right Hugo shortcode. Run per draft.
- **`/explainers`** — opt-in content-type for technical deep-dive posts (like feature walkthroughs, skill presentations, or cross-cutting concern explainers). Scaffolds a six-section skeleton, validates frontmatter + weight, and ships a research subagent for codebase exploration. Requires `content_types.explainers.enabled` in `.blog-craft.yaml`.
- **`/educational-writing`** — the methodology blog-craft holds every post to: reader-first structure ([Diátaxis](https://diataxis.fr/)), evidence-grounding, and a thin-persona rule that keeps the character from crowding out the substance. Loaded by `/blog-post` and `/post-rewrite`; invoke directly to diagnose whether a post is actually useful.
- **`/post-rewrite`** — rewrites an existing post that reads like *prose about the session that made it* into something a reader can build/operate/fix from. Diagnoses it against the methodology, gathers the evidence the original omitted, and re-shapes it — leading with the how-to, adding a reference block and a recovery path, keeping the persona thin and the cover untouched.

Each bootstrapped blog stores its identity in a `.blog-craft.yaml` at the repo root. The post and media skills consume that config, so the same plugin serves any number of blogs with different personas, tracks, and voices.

### The quality gate

A regular post (`content_type: posts`) is held to a structural gate — the mechanical floor under the educational-writing methodology. It enforces the evidence a genuinely useful teaching post carries: a `reader_goal` (what the reader can *do* after reading), a declared Diátaxis mode, at least one real command/output block, and an actionable section (Reproduce / Runbook / Verify). New blogs wire it into CI by default; see [`docs/CONFIG.md` §7](docs/CONFIG.md).

## Install

```bash
/plugin install derio-net/blog-craft
```

(Or, for local development of the plugin itself: `/plugin install /path/to/blog-craft`.)

## The skills

After install, all become available as slash commands. Run `/bootstrap-blog` in a fresh directory to spin up a new blog. Inside any directory containing `.blog-craft.yaml`, `/blog-post`, `/media`, `/explainers`, and `/post-rewrite` work end-to-end; `/educational-writing` is the shared methodology the authoring skills load (and you can invoke it directly to diagnose a post).

What blog-craft does **not** ship: a deploy pipeline, multi-SSG support (Hugo only), or a theme wizard (Hextra only). These are intentional cuts — KISS for v1.
