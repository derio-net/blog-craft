---
name: bootstrap-blog
description: Bootstrap a new Hugo + Hextra teaching blog with a custom central metaphor and configurable series structure. Use once per new blog repo.
user-invocable: true
disable-model-invocation: false
arguments:
  - name: target_dir
    description: "Directory to create the blog in (default: CWD). Refuses if .blog-craft.yaml already exists there."
    required: false
  - name: answers_file
    description: "Path to a YAML file with all wizard answers (testing/automation only — skips the conversational flow)."
    required: false
---

# Bootstrap a new blog-craft blog

Walk the user through a conversational wizard, collect their answers into a YAML file, then invoke the renderer to scaffold a working Hugo + Hextra blog.

**Announce at start:** "I'm using bootstrap-blog to scaffold a new teaching blog."

## Plugin internals

This skill calls into the plugin's tooling. Find the plugin root by walking up from this SKILL.md (the plugin's `tools/` directory sits at `<plugin_root>/tools/`).

- **Renderer:** `<plugin_root>/tools/render-template/main.go` (Go binary, runs via `go run`)
- **Bootstrap orchestrator:** `<plugin_root>/tools/bootstrap-render.sh` (shell helper that does preflight + 3-pass render + Hugo smoke check)
- **Templates:**
  - `<plugin_root>/templates/hugo-hextra/` — one-pass render
  - `<plugin_root>/templates/per-series-always/` — rendered once per series
  - `<plugin_root>/templates/per-series-overview/` — rendered once per series, only if `features.series_overview_posts: true`

## Procedure

### Step 0: Confirm target directory

Resolve the target directory (the `target_dir` arg, or CWD if absent). Verify it does not already contain `.blog-craft.yaml` — if it does, refuse and instruct the user to remove the file manually if they truly want to re-bootstrap. Do NOT offer an "overwrite" path.

If the user passed `answers_file`, skip Steps 1–6 and jump straight to Step 7.

### Steps 1–6: Walk the wizard, one step at a time

Conversational. Ask each question, wait for the answer, validate, repeat. Keep questions short. Show concrete Frank examples for inspiration where the user might be stuck — but make clear they're examples, not requirements.

Collect answers into an in-memory YAML structure. After Step 6, write it to `/tmp/wizard-answers-<timestamp>.yaml`.

#### Step 1: Project basics

Ask in order:
- **`project.name`** — display name (e.g., "Frank, the Talos Cluster")
- **`project.tagline`** — one-line description (e.g., "Tutorial series on building and operating an AI-hybrid Kubernetes homelab")
- **`project.base_url`** — full base URL with trailing slash (e.g., `https://my-blog.example.com/` or `https://example.com/path/`)

Derive these from `base_url`:
- **`project.base_path`** — the URL path component, e.g., `https://example.com/blog/` → `/blog/`. If there's no path, use `/`.
- **`project.module_path`** — host + path, no scheme/trailing-slash, e.g., `https://example.com/blog/` → `example.com/blog`.

#### Step 2: Central metaphor

Free-text. Walk one at a time:
- **`metaphor.persona`** — one or more paragraphs describing the persona/character. Frank's example: "Frank is a chibi Frankenstein monster made of server hardware. Stitched-together, slightly anxious, deeply opinionated, learning by breaking things."
- **`metaphor.visual_constants`** — a list. Prompt: "What should stay the same in every image? Bullet rules. Type each, then `done` when finished." Example bullets: "Green skin", "Black messy hair", "RJ45 neck bolts", "Blue glow comes from environment, NOT eyes."
- **Reference image** (optional) — prompt: "Path to a reference image to anchor consistency? (Type a file path, or `skip` to add later.)" If supplied, store the *source* path now; Step 7 will copy it to `<target>/static/images/reference.png` and write that fixed destination into `metaphor.reference_image`. If the user has no reference yet, that's fine — after bootstrap they can *generate* candidate character design sheets straight from this persona + visual_constants with `scripts/gen-character-sheet.py N`, browse them with `scripts/build-gallery.py`, and promote the keeper to `static/images/reference.png` (see the rendered `.reference-pool/README.md`).
- **`metaphor.base_style`** — one paragraph describing the painter/medium/composition. Wraps every per-post prompt.
- **`metaphor.reference_guidance`** — one paragraph instructing the image model how to use the reference (proportions, palette, outline weight, etc.).

#### Step 3: Series

Show a 3-preset menu:

> Pick a series structure:
> 1. **`single`** — one series called "posts". Best for blogs that don't need parallel narrative structures.
> 2. **`tracks`** — two parallel series at different altitudes. Classic split: a *story track* (chronological narrative — "how we built X, in order") and a *reference track* (atemporal companion — "how to operate X, day-to-day"). Each story post tends to have a sibling in the reference track. The two reinforce each other: story explains *why*, reference tells you *how*. Suggested defaults: `building` + `operating`. Other natural pairings: `tutorials` + `recipes`, `concepts` + `playbooks`.
> 3. **`custom`** — N series. Use for products with separate dimensions, multi-axis blogs, etc.

Capture into `series:` as a list of `{key, title, description}` objects.
- For `single`: `[{key: posts, title: "Posts", description: ""}]`.
- For `tracks`: prompt for the two key/title pairs (default to `building`/`operating` with Frank's titles & descriptions), let user override.
- For `custom`: loop `key` (kebab-case) → `title` → `description` → "Add another? (y/N)".

Validate: every `key` must be kebab-case (`^[a-z][a-z0-9-]*$`) and unique within the list.

#### Step 4: Voice/tone

Show the default and let the user accept or replace:

> Default `voice`: "Technical but approachable. Intermediate practitioners. Real commands and outputs. Gotchas inline. References at the bottom."

Capture into `voice:`.

#### Step 5: Image-gen settings

- **`image_gen.provider`** — must be `gemini` in v1. Tell the user this and confirm.
- **`image_gen.model`** — default `gemini-3-pro-image-preview`. Let the user override if they know a newer one.
- **`image_gen.api_key_env`** — default `GEMINI_API_KEY`.
- **`image_gen.output_dir`** — default `static/images`. Don't bother prompting unless the user is opinionated.
- **`image_gen.prompts_file`** — default `prompt_for_images.yaml`. Same.

#### Step 6: Optional toggles

- **`features.roadmap_shortcode`** — default `false`. "Include a roadmap shortcode skeleton?" Yes only if you have a temporally-evolving thing to visualize.
- **`features.series_overview_posts`** — default `true`. "Seed a `00-overview/index.md` per series?"
- **`git_init`** — default `true`. Initialize git in the target dir after rendering.
- **`gh_repo_create`** — default `ask`. Create a GitHub remote? If yes: `org/name`? Visibility?

### Step 7: Render

1. Write the answers YAML to `/tmp/wizard-answers-<timestamp>.yaml`.
2. Invoke the orchestrator:

   ```bash
   bash <plugin_root>/tools/bootstrap-render.sh /tmp/wizard-answers-<timestamp>.yaml <target_dir>
   ```

   This runs preflight + 3-pass render + a `hugo --buildDrafts --quiet` smoke check. Exit code 2 = preflight refusal (existing `.blog-craft.yaml`); other non-zero = render or Hugo error.

3. If a reference image source path was supplied in Step 2, copy it now:
   ```bash
   cp <source_path> <target_dir>/static/images/reference.png
   ```

### Step 8: Initial image (optional)

Skip silently if either of these is false: `features.series_overview_posts` is `true`, OR a reference image was supplied.

Otherwise, defer to the same prompt-composition logic the `blog-post` skill uses for per-post covers. Ask the user:

> "Want me to generate the cover image for the first series-overview post now? It costs one Gemini call (~30s). I'll need:
>   1. A one-paragraph scene description for the overview cover
>   2. Your `<api_key_env>` value if it's not already exported"

If yes:

1. Compose the full prompt by concatenating, in order: `metaphor.base_style`, `metaphor.persona`, the bullets in `metaphor.visual_constants` (one per line), the user's scene description, `metaphor.reference_guidance`. Show the composed prompt to the user for approval before proceeding.
2. Edit `<target_dir>/prompt_for_images.yaml` and replace the empty `prompt: ""` value on the `overview-<first-series-key>` entry with the approved composed prompt.
3. Confirm `<api_key_env>` is in the environment (read from `os.environ` if running interactively; if missing, ask the user to paste it and `export` it just for this step).
4. Run image generation:
   ```bash
   ( cd <target_dir> && python scripts/generate-images.py --reference static/images/reference.png --only overview-<first-series-key> )
   ```
5. Display the resulting PNG path. Offer to regen if the user is unhappy.

### Step 9: Verify

Pick a free TCP port:
```bash
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1])")
```

Start `bash scripts/hugo-serve.sh --port $PORT --buildDrafts` in the background (the wrapper handles the Go-on-PATH requirement — see `scripts/hugo-serve.sh` header), wait until `localhost:$PORT<base_path>` returns 200 (timeout 30s), then kill it. Print the URL the user can open.

### Step 10: Optional git steps

If `git_init` is true:
```bash
( cd <target_dir> && git init -b main && git add . && git commit -m "feat: initial scaffold via blog-craft" )
```

If `gh_repo_create` is true (and the user confirmed `org/name` + visibility):
```bash
( cd <target_dir> && gh repo create <org>/<name> --<visibility> --source=. --push )
```

Note: `gh repo create` against an org requires `read:org` scope on the active account. If the user is on a service token without it, instruct them to run `env -u GITHUB_TOKEN gh repo create ...` (or switch accounts).

## Done

End with a brief recap:
- Where the blog landed (`<target_dir>`)
- The local-dev URL (`http://localhost:1313<base_path>`)
- Three follow-ups: write your first post (`/blog-post`), customize the cover image prompts (`prompt_for_images.yaml`), and pick a deploy target (out of scope for blog-craft).
