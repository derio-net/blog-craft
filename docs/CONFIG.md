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

series:
  - { key, title, description, content_type: posts | papers }

series_index:             # optional; controls the {{< series-index >}} layout
  style: cards            #   cards (default) | table | none
  layers:                 #   optional — opts into layer colour-coding
    - { code, name }      #   run tools/gen-layer-palette.py -> data/layer_palette.yaml

content_types:            # optional; opt-in modules (e.g. papers)
  papers: { enabled, dossier_dir, data_dir, gate, source_types,
            artefact_kinds, shortcodes, crosslink_fields, weight_offset }

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
