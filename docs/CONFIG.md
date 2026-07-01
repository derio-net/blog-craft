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
