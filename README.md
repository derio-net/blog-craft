# blog-craft

Portable teaching-blog scaffolding and authoring skills for [Claude Code](https://claude.ai/code).

## What is blog-craft

blog-craft is a Claude Code plugin that ships three skills for the lifecycle of a teaching-style blog:

- **`/bootstrap-blog`** — wizard that scaffolds a fresh Hugo + Hextra blog with a custom central metaphor, configurable series structure ("tracks"), and an image-generation pipeline. Run once per new blog.
- **`/blog-post`** — creates a new post in the relevant series, composes a Gemini image prompt from the per-blog metaphor, generates the cover, and updates the series overview. Run per post.
- **`/media`** — finds `<!-- MEDIA: ... -->` placeholders in drafts and fills them by capturing/optimizing assets and rendering the right Hugo shortcode. Run per draft.

Each bootstrapped blog stores its identity in a `.blog-craft.yaml` at the repo root. The post and media skills consume that config, so the same plugin serves any number of blogs with different personas, tracks, and voices.

## Install

```bash
/plugin install derio-net/blog-craft
```

(Or, for local development of the plugin itself: `/plugin install /path/to/blog-craft`.)

## The three skills

After install, all three become available as slash commands. Run `/bootstrap-blog` in a fresh directory to spin up a new blog. Inside any directory containing `.blog-craft.yaml`, `/blog-post` and `/media` work end-to-end.

What blog-craft does **not** ship: a deploy pipeline, multi-SSG support (Hugo only), or a theme wizard (Hextra only). These are intentional cuts — KISS for v1.
