# `.blog-craft.yaml` — config contract (v2)

The single per-repo file that distinguishes one blog-craft blog from another.
Validated by `tools/validate_config.py --check <path>`.

```yaml
version: 2
blog_craft_version: "<release applied>"   # set by bootstrap/update

project: { name, tagline, base_url, base_path, module_path }

image:
  provider: gemini
  model: <gemini model>
  api_key_env: GEMINI_API_KEY
  output_dir: static/images
  prompts_file: prompt_for_images.yaml
  reference_pool: .reference-pool
  curation: { count_default: 1, archive_cap: 30, contact_sheet: true }
  composition_order: [ <layer names…>, scene ]
  layers:
    <name>: <scalar | list | indexed-table>
  optimize:               # optional; build-time WebP pipeline (see §6). Absent → raw images.
    enabled: true
    format: webp
    quality: 82
    max_width: 1600
    banner_max_width: 2560

series:
  - { key, title, description, content_type: posts | papers | explainers }

series_index:             # optional; controls the {{< series-index >}} layout
  style: cards            #   cards (default) | table | none
  layers:                 #   optional — opts into layer colour-coding
    - { code, name }      #   run tools/gen-layer-palette.py -> data/layer_palette.yaml

content_types:            # optional; opt-in modules (e.g. papers, explainers)
  papers: { enabled, dossier_dir, data_dir, gate, source_types,
            artefact_kinds, shortcodes, crosslink_fields, weight_offset }
  explainers: { enabled, weight_offset }

quality:                  # optional; educational-writing gate (see §7). Absent => no CI gate.
  enabled: true
  gate: { require_reader_goal, require_diataxis_mode,
          min_command_blocks, require_actionable_section }

features:                 # series_overview_posts, read_tracker, banners,
                          # roadmap{enabled,data}, analytics, css{mermaid_palette}
voice: |
  <tone>
ci:
  validators: [ frontmatter, dossier, mermaid, hugo_build ]
  deploy: { kind: container_pages | pages | none }
```

## §4.1 Layer-resolution rule

The image generator concatenates the layers named in `image.composition_order`,
in order. Each name resolves against `image.layers`:

| Layer value | Resolves to |
|---|---|
| **scalar** (string) | the string, verbatim |
| **list** | each element as a `- ` bulleted line |
| **indexed-table** (map: `torso`, `mood`) | the entry selected by the per-image field — `torso` by `entry.series` + `entry.torso_variant`, `mood` by `entry.mood` (name) |
| **`scene`** (reserved) | the per-image entry's `prompt` field |

A missing selector skips that layer. `scene` must appear in `composition_order`
and must **not** be a key in `layers`. The generator hardcodes no layer
vocabulary or order — frank and stoa ship different `composition_order` +
`layers`, and both are pure data. This is what lets one generator reproduce both
blogs' exact composed prompts.

## §5 Series index (`series_index`)

`{{< series-index >}}` renders a page-derived index of a series' posts on the
series overview. The optional `series_index` block picks its layout:

- **`style: cards`** (default) — a papers-roadmap-style vertical timeline: number
  badge, linked title, `summary` takeaway, and (when opted in) a layer tag.
- **`style: table`** — the compact `# / Post / Takeaway` table.
- **`style: none`** — no index rendered.

**Layer colour-coding (opt-in).** Declare `series_index.layers` as a registry of
`{code, name}` and give each post a `layer: <code>` in its frontmatter. Bootstrap
runs `tools/gen-layer-palette.py` to write `data/layer_palette.yaml` — 21-safe
unique OKLCH colours, one per layer, shared by the `series-index` cards **and**
the `roadmap` shortcode (a layer is the same colour in both). Regenerate the
palette (`python tools/gen-layer-palette.py --config .blog-craft.yaml > data/layer_palette.yaml`)
whenever the layer set changes. Without a palette, cards render neutral and the
roadmap is uncoloured — no layer system is required.

## §6 Image optimization (`image.optimize`)

Opt-in, build-time image optimization. When `image.optimize.enabled: true`, Hugo
processes bundle-resource images into **WebP** derivatives (width-capped, with a
responsive `srcset` + explicit `width`/`height`) at build — the committed PNG
**masters stay untouched**. Absent or `enabled: false` → raw images pass through.

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | `false` | Master switch (opt-in). |
| `format` | `webp` | Output format (only `webp` supported). |
| `quality` | `82` | Encode quality, 1–100. |
| `max_width` | `1600` | Width cap (px) for covers + inline images. |
| `banner_max_width` | `2560` | Separate cap for the wide site/track banners. |

**What is optimized:** post/section **covers** (`docs/list.html` + a blog's own
`single.html`), **inline** markdown images (`![](…)` via the render-image hook)
and the `{{< screenshot >}}` shortcode, and **banners**. Remote/absolute URLs and
`svg`/`gif` resources always pass through untouched. All routes go through the
single `partials/opt-image.html`.

**Banner convention (important):** Hugo can only process images that are page
resources or live under `assets/`. So to be **optimized**, banners must live in
**`assets/images/`** (e.g. `assets/images/banner-<track>.png`), **not**
`static/images/` — and `prompt_for_images.yaml` directs operator-generated
banners there. A banner still in `static/images/` renders **raw (unoptimized)**
as a fallback, so an un-migrated blog never silently loses its banner; move it to
`assets/images/` to opt into WebP. A track with no banner in either place renders
nothing (nil-safe).

**Composing the banner description:** the Gemini API doesn't support the 6:1
panoramic aspect ratio banners use, so `operator_generated: true` entries are
generated by hand in the Gemini web UI rather than through the API. That doesn't
mean writing the prompt by hand too — `generate-images.py --print-prompt <key>`
composes the full description (`base_style` + `persona` + `visual_constants` +
the entry's own `prompt` + `reference_guidance`) for *any* key, including
operator-generated ones; only the generation loop skips them, not `--print-prompt`.
Run it, paste the output into the Gemini web UI (attaching `image.reference_image`
if the blog uses one), and drop the resulting PNG into `assets/images/`.

**Requires Hugo Extended** for WebP encoding. The shipped CI template
(`.github/workflows/blog-ci.yml`) sets `extended: true`; a blog with its own CI
must ensure the same, or WebP silently won't be generated.

## §7 Post-quality gate (`quality`)

Optional. The structural floor under the **educational-writing** methodology (see
`skills/educational-writing/`). It exists because the easy failure mode of a
drafted post is *prose about the session that made it* — witty, in-character,
useless to a reader who needs to build/operate/fix the thing. The gate can't
judge prose, but it enforces the evidence a genuinely useful post carries.

Scope: only `content_type: posts` posts. Papers and explainers ship their own
validators and structure, so they're skipped. A single non-teaching post may opt
out with `quality_exempt: <reason>` in its frontmatter (use sparingly).

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | *(absent)* | When `true`, the shipped CI wires the gate step. Bootstrap sets it `true`; absent → no CI gate (skills still apply the methodology). |
| `gate.require_reader_goal` | `true` | Frontmatter `reader_goal:` present — one line on what the reader can *do* after reading. |
| `gate.require_diataxis_mode` | `true` | Frontmatter `diataxis:` present and valid — one or more of `tutorial`, `how-to`, `reference`, `explanation`. |
| `gate.min_command_blocks` | `1` | Minimum fenced command/output code blocks (mermaid fences don't count). |
| `gate.require_actionable_section` | `true` | At least one heading a reader under pressure can follow (Reproduce / Runbook / Steps / Verify / Recover / …). |

Run it directly:

```bash
python <blog-craft>/tools/validate_educational.py --config .blog-craft.yaml \
    content/docs/<series>/<NN>-<slug>/index.md
```

The validator ships into every blog at `scripts/validate_educational.py` (a
byte-identical copy of `tools/validate_educational.py`), so a plain-python CI runs
it without the plugin.

### Frontmatter added by the methodology

Every `content_type: posts` post carries two fields, set by `/blog-post` and
`/post-rewrite`:

```yaml
reader_goal: "Configure NUT so the homelab shuts down cleanly before the UPS battery dies."
diataxis: [how-to, reference]   # one or more of: tutorial, how-to, reference, explanation
```
