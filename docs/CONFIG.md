# `.blog-craft.yaml` — config contract (v5)

The single per-repo file that distinguishes one blog-craft blog from another.
Validated by `tools/validate_config.py --check <path>` (accepts schema
versions 2–5; `tools/migrate_config.py` climbs the ladder; `tools/migrate_prompts.py` migrates the entries file).

```yaml
version: 5
blog_craft_version: "<release applied>"   # set by bootstrap/update; see §11

project: { name, tagline, base_url, base_path, module_path }

site_dir: .               # optional; where the Hugo site lives relative to this
                          # file (e.g. `blog` when the config sits at the repo
                          # root). Consumed by /blog-post scaffolding + /update
                          # path mapping. Default `.`.

image:
  provider: gemini
  model: <gemini model>
  api_key_env: GEMINI_API_KEY
  output_dir: static/images
  prompts_file: prompt_for_images.yaml
  reference_pool: .reference-pool
  reference_image: static/images/reference.png   # optional; the master
                          # character sheet — 2nd in the generator's reference
                          # precedence (CLI --reference beats it; pool follows)
  curation: { count_default: 1, archive_cap: 30, contact_sheet: true }
  composition_orders:     # v5: NAMED orders; entries pick one (default: hero).
    hero: [ <tokens…>, scene ]                   #   token = layer | layer[chunk]
    scenery: [ <tokens…>, scene ]                # (legacy v4: a single composition_order list)
  layers:
    <name>: <scalar | list | selector-table>     # see §4.1
  character_sheet:        # optional; which layers define the character for
    layers: [persona, visual_constants]          # scripts/gen-character-sheet.py
                          # (default shown; a frank-style blog sets [base_character])
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
  mermaid_csp_init: true  # optional; default false. Turn ON when the site serves
                          # `script-src 'self'` without 'unsafe-inline': that drops
                          # the theme's inline mermaid init, and diagrams then
                          # freeze in the light theme instead of following the
                          # dark/light toggle. Leave OFF otherwise — without a CSP
                          # the theme's block still runs and you would get two
                          # initialisers racing. See §10.
  glossary:               # optional; abbreviation glossary (see §9). Absent => off.
    enabled: true
    first_occurrence_only: true
voice: |
  <tone>
voice_level: balanced     # optional; dry | balanced | rich — how thick the persona
                          # frame is (see §8). Default balanced. Orthogonal to the gate.
ci:
  validators: [ frontmatter, dossier, mermaid, hugo_build ]
  deploy: { kind: container_pages | pages | none }
```

## §4.1 Layer-resolution rule

**v5 orders and entries.** `image.composition_orders` is a map of NAMED token
lists; an entry composes with `composition.order` — a
`composition_orders[name]` reference or an inline token list — defaulting to
`hero`. A token is a layer name or `layer[chunk]`, which resolves a dict
layer's named chunk directly (e.g. `reference_guidance[anchor]` — chunk
granularity is per-blog data: keep guidance as one chunk or split it). v5
entries carry a `composition:` block:

```yaml
- key: papers-07
  output: static/images/papers-07-cover.png
  aspect_ratio: "16:9"
  composition:
    reference_images:            # EXPLICIT (v5): what is declared is sent,
      primary: refs/sheet.png    # nothing else — the v4 precedence chain
      clothing: [refs/coat.png]  # (config reference_image / pool) never
    order: composition_orders[hero]   # optional; or an inline token list
    modifiers: { series: papers, clothing: papers[white_lab_coat], mood: worried }
    scene: >-                    # was `prompt` in v4
      ...
```

A dict-layer **modifier** value may be a bracket path (`papers[white_lab_coat]`
descends a nested table directly), a plain name (single-level lookup,
free-form passthrough on miss), or absent (layer skipped). A plain value that
lands on a container skips — bare group names never dump a table into the
prompt. Legacy v4 entries (top-level `prompt` + selector fields, single
`composition_order`, `_select` walks, the old reference precedence) keep
working — one engine serves both schemas.

The generator concatenates the resolved tokens in order, joining non-empty
sections with a blank line. Each plain layer name resolves against
`image.layers`:

| Layer value | Resolves to |
|---|---|
| **scalar** (string) | the string, verbatim |
| **list** | each element as a `- ` bulleted line |
| **selector-table** (map) | the **selector walk** below |
| **`scene`** (reserved) | the per-image entry's `prompt` field |

**The selector walk.** A map layer may declare `_select:` — a list of
selection steps; each step is an entry-field name, or a list of names (first
present wins). Absent → one step: the layer's own name (a same-named entry
field selects). Keys beginning `_` are directives, never prose. Walking:

- the entry field is **missing** → the layer resolves to nothing (skipped);
- the field's value is a **key** of the current map / a valid **int index** of
  the current list → descend;
- the value is a **string** that selects nothing and this is the **last** step
  → the string is used verbatim (**free-form passthrough** — write bespoke
  prose straight into the entry field; a non-string that selects nothing
  skips);
- it selects nothing at an **intermediate** step → skipped (a bad group never
  leaks into the prompt). `scripts/validate_images.py` flags entries whose
  walk silently resolves to nothing.

frank's torso table, as pure data:

```yaml
layers:
  torso:
    _select: [[torso, series], torso_variant]   # group by torso|series, then index
    building: ["work clothes", "overalls", …]
    papers:   ["white shirt + black tie", …]
  mood:                                         # default _select: [mood]
    focused: "focused, concentrating"
```

**Standard entry fields** — consumed by the generator itself, never selector
data: `key`, `series` (also drives pool reference selection), `output`,
`description`, `prompt` (the scene), `aspect_ratio`, `image_size`,
`references` (extra anchor images, appended after the master sheet),
`operator_generated`, `post_process`. Every **other** entry field exists to be
selected on by some layer's `_select`.

A missing selector skips that layer. `scene` must appear in `composition_order`
and must **not** be a key in `layers`. The generator hardcodes no layer
vocabulary, order, or selection rule — frank and gondor ship entirely
different `composition_order` + `layers`, and both are pure data. This is what
lets one generator reproduce both blogs' exact composed prompts.

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
composes the full description (every `composition_order` layer around the
entry's own `prompt`) for *any* key, including operator-generated ones; only
the generation loop skips them, not `--print-prompt`.
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
out with `quality_exempt: <reason>` in its frontmatter (use sparingly). A post
that legitimately needs no diagram waives *just* that one check with
`diagram_exempt: <reason>` while staying subject to the rest of the gate.

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | *(absent)* | When `true`, the shipped CI wires the gate step. Bootstrap sets it `true`; absent → no CI gate (skills still apply the methodology). |
| `gate.require_reader_goal` | `true` | Frontmatter `reader_goal:` present — one line on what the reader can *do* after reading. |
| `gate.require_diataxis_mode` | `true` | Frontmatter `diataxis:` present and valid — one or more of `tutorial`, `how-to`, `reference`, `explanation`. |
| `gate.min_command_blocks` | `1` | Minimum fenced command/output code blocks (mermaid fences don't count). |
| `gate.require_actionable_section` | `true` | At least one heading a reader under pressure can follow (Reproduce / Runbook / Steps / Verify / Recover / …). |
| `gate.require_diagram` | `true` | A post whose `diataxis` includes `how-to` or `tutorial` must carry ≥ 1 ` ```mermaid ` block — for visual learners a topology/flow diagram is the difference between understanding and guessing. Waive one post with `diagram_exempt: <reason>`. |

Run it directly:

```bash
python <blog-craft>/tools/validate_educational.py --config .blog-craft.yaml \
    content/docs/<series>/<NN>-<slug>/index.md
```

The validator ships into every blog at `scripts/validate_educational.py` (a
byte-identical copy of `tools/validate_educational.py`), so a plain-python CI runs
it without the plugin.

### Mermaid syntax gate (`quality.mermaid_syntax`)

Separate from the post-quality gate above, and content-type-agnostic: a
build-time linter that catches common ` ```mermaid ` syntax errors —
subgraph-targeting edges, bare `<br>` (use `<br/>`), unbalanced brackets — with
`file:line`, across posts, explainers, and papers, so a broken diagram fails CI
instead of shipping dead. **On by default.** Opt out per blog:

```yaml
quality:
  mermaid_syntax: false   # default true (absent → on)
```

Run it directly:

```bash
python <blog-craft>/tools/validate_mermaid.py --config .blog-craft.yaml \
    content/docs/*/*/index.md
```

Ships at `scripts/validate_mermaid.py` (byte-identical mirror) and runs as a CI
step before the Hugo build.

### Frontmatter added by the methodology

Every `content_type: posts` post carries two fields, set by `/blog-post` and
`/post-rewrite`:

```yaml
reader_goal: "Configure NUT so the homelab shuts down cleanly before the UPS battery dies."
diataxis: [how-to, reference]   # one or more of: tutorial, how-to, reference, explanation
```

Optionally, on a post that **mirrors code state** (no in-post "Update" logs — the
post is kept current instead), a last-updated stamp:

```yaml
last_updated: 2026-07-13
last_updated_commit: https://github.com/owner/repo/commit/<sha>
```

Render it with the `{{< last-updated >}}` shortcode (ships in the hugo-hextra
template) near the top of the post — it shows `Last updated <date> · <sha>` with
the sha linked to the commit, so a reader knows how current the post is and can
diff since. Emits nothing if `last_updated` is absent.

## §8 Voice level (`voice_level`)

Optional. `dry` | `balanced` | `rich` (default `balanced`). The dial for **how
much personality colors the teaching** — it works with the freeform `voice:`
string (`voice` = the character; `voice_level` = how loud). It moves orientation
warmth, aside frequency, transition prose, and how the *why* is voiced; it does
**not** move the evidence requirements, the Diátaxis mode discipline, or the gate.
Dryness is orthogonal to correctness.

| Level | Feels like | Body persona |
|-------|-----------|--------------|
| `dry` | clean technical docs | almost none (the cover image is the flavor) |
| `balanced` | a knowledgeable friend explaining | thin frame + warm orientation + memory-aiding asides |
| `rich` | the persona narrating the build | voiced throughout, but the how-to still leads and every section carries its evidence |

`/blog-post` and `/post-rewrite` read it from config and accept a per-run
`voice_level` override. Full guidance: `skills/educational-writing/references/voice.md`.

## §9 Abbreviation glossary (`features.glossary`)

Optional, off unless asked for. A teaching blog leans on abbreviations — NUT,
SLO, CDP, OKLCH — because spelling each one out every time would wreck the
prose. The cost lands on the reader who does not already know the term: they
leave the page to search, or they guess. This feature lets them click the term
instead.

```yaml
features:
  glossary:
    enabled: true
    first_occurrence_only: true   # optional, default true
```

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | *(absent → false)* | Master switch. When true, bootstrap/`/update` materialize the two shortcodes and `assets/css/glossary.css`, and the shipped CI wires the validator step. |
| `first_occurrence_only` | `true` | An **authoring** knob, not a rendering one: it governs where `/glossary` inserts markers. `false` marks every occurrence in a post rather than just the first. |

No schema version bump is involved — `features` passes through untouched, so
turning this on is a two-line edit to an existing v5 config followed by
`/update`.

### The registry — `data/glossary.yaml`

One blog-wide file. A term defined while writing post 3 is available to post 7,
so a series never redefines itself.

```yaml
NUT:
  name: Network UPS Tools
  description: >-
    Daemon suite that monitors a UPS over USB or the network and triggers a
    clean shutdown before the battery dies.
  url: https://networkupstools.org      # optional
SLO:
  name: Service Level Objective
  description: >-
    The numeric reliability target a service commits to — the line an error
    budget is measured against.
```

- Keyed by the literal token as it appears in prose. **Case-sensitive.**
- `name` and `description` are required. `url` is optional, must be absolute
  `http(s)`, and renders as a "Read more" link inside the panel.
- Classified `content` by `templates/manifest.yaml` (`data/**`), so **`/update`
  never touches your definitions.**
- Keep it alphabetically sorted; the validator warns (never fails) otherwise.

### Marking terms — the `/glossary` skill

```bash
/glossary                          # every post in the blog
/glossary tutorials                # one series
/glossary tutorials/07-monitoring  # one post
```

It scans for candidates, writes a definition for each from the sentence it was
found in, shows you the registry diff before writing, then inserts the markers.
It is **idempotent** — running it again on an already-marked post changes
nothing, which is what makes a repeated series-wide sweep safe.

Candidates are 2–10 character uppercase tokens found in genuine prose. Code
fences, inline code, frontmatter, headings, link text, URLs, existing shortcodes
and raw HTML are never touched. Lowercase tool names (`systemd`, `kubectl`) are
deliberately not proposed — too noisy — but you can hand-add any term to the
registry and it renders identically.

### The shortcodes

```
I wired {{< abbr "NUT" >}} into the rack.
The {{< abbr "SLO" "SLOs" >}} we agreed on were generous.
```

The optional second argument overrides the **displayed** text while the lookup
still uses the first — that is how plurals and possessives work without forking
a registry entry. It is positional rather than named because Hugo refuses to mix
positional and named parameters in one shortcode call.

The rendered markup is a `<button popovertarget>` wrapping an `<abbr title>`,
plus a `<span popover>` panel. **No JavaScript**: click/tap to open, Esc or
click-away to close, keyboard focusable, top-layer stacked — all native browser
behaviour. The inner `<abbr title>` carries the expansion for screen readers.

**Where the panel appears.** Directly below the term, flipping above it when
there is no room below and flipping its inline side near the viewport edge. That
placement is *not* free with the Popover API: the top layer decides stacking, not
coordinates, and an unpositioned panel takes the UA default and lands in the
viewport corner. It comes from CSS anchor positioning — the shortcode emits a
unique `anchor-name` per trigger and a matching `position-anchor` on its panel,
and the `@supports (anchor-name: --x)` block in `assets/css/glossary.css` carries
the geometry. Browsers without anchor positioning fall through to the base
`.abbr-panel` rule, which docks the panel bottom-centred and viewport-clamped.

If you override the panel's look in your own `custom.css`, leave those two rules
alone unless you mean to move it — and if you do move it, override *both* paths,
or a reader on a non-supporting browser gets whichever one you forgot.

A key with no registry entry **fails the Hugo build**. A marker with nothing
behind it is a broken promise to the reader.

```
{{< glossary-index >}}
```

renders the whole registry as an alphabetical definition list. Put it on a page
of your own choosing — blog-craft deliberately does not create a `/glossary/`
page, because that page would be operator-owned content `/update` could never
manage. It emits nothing (not an error) when the registry is absent.

### The CI gate

Run it directly:

```bash
python <blog-craft>/tools/validate_glossary.py --config .blog-craft.yaml \
    content/docs/*/*/index.md
```

| Check | Severity |
|---|---|
| a marker with no registry entry | **error** |
| an entry missing or blank `name` / `description` | **error** |
| `url` present but not an absolute http(s) URL | **error** |
| two keys differing only in case | **error** |
| an entry no post references | warning |
| the registry is not alphabetically sorted | warning |

Markers inside code fences are ignored, so a post that *documents* the shortcode
is not gated on its own example.

Ships at `scripts/validate_glossary.py` (with its `scripts/glossary_scan.py`
companion — the validator imports it) so a plain-python CI runs it without the
plugin, and runs as a CI step when `features.glossary.enabled` is true.

## §10 Mermaid under a strict CSP (`features.mermaid_csp_init`)

```yaml
features:
  mermaid_csp_init: true    # default false
```

Turn this on **when, and only when, the site serves `script-src 'self'` without
`'unsafe-inline'`.**

The Hextra theme initialises mermaid from an inline `<script>` at the end of
`_partials/scripts/mermaid.html`: it captures each diagram's source, calls
`mermaid.initialize()` with the current theme, and installs a MutationObserver
that re-renders on the dark/light toggle. A strict `script-src` drops that block.

The failure is quiet, which is the reason this knob exists at all. `mermaid.js`
self-starts, so **diagrams still appear** — there is no blank space, no build
error, and nothing in the console an author would think to look for. They simply
render in the light theme always, and stop following the toggle, on every page
that uses one. Enabling the feature materializes
`assets/js/mermaid-init.js`, which re-implements both behaviours from an
external asset; the theme's inline block stays in the markup, inert.

**Why it is opt-in rather than always on.** The two CSP fixes in 0.15.0 replaced
inline scripts *blog-craft itself emitted*, so there was nothing left behind to
collide with. This one supersedes a script inside the pinned theme, which
blog-craft cannot remove. On a site with no CSP that block still runs — shipping
ours unconditionally would mean two `mermaid.initialize()` calls and two
MutationObservers racing over the same nodes on every theme toggle. So the flag
tracks a fact about your deployment, not a preference.

If you enable a CSP later, flip this at the same time. If you are unsure whether
your site sends one, check the response headers:

```bash
curl -sI https://<your-blog>/ | grep -i content-security-policy
```

Guarded by `tests/unit/test_mermaid_csp_init.py`, which pins both directions
(flag on ⇒ an external, deferred, same-origin `mermaid-init` script in the built
output; flag off ⇒ the asset is never materialized) and additionally asserts the
theme *still* emits the inline init this feature supersedes — so a theme bump
that fixes it upstream fails loudly and tells you to retire the flag rather than
leaving you with a silent double-init.

## §11 Sync state — `.blog-craft.sync.yaml`

A generated sibling of `.blog-craft.yaml`, holding the config **as of the last
successful blog-craft sync**. Written by `bootstrap-render.sh` and by
`tools/update.py --apply` when the run is conflict-free and unscoped. Not
hand-edited. **Commit it** — see below for what its absence costs.

It exists because the two axes are not the same axis. `blog_craft_version`
records which *templates* the blog last received; the snapshot records which
*config* they were rendered with. `/update`'s 3-way base is
`render(config_at_last_sync, templates_at_recorded_version)`, and it needs both:

| | |
|---|---|
| `blog_craft_version` (in `.blog-craft.yaml`) | which templates — a git ref |
| `.blog-craft.sync.yaml` | which config those templates were fed |

Without the snapshot the updater has to fall back to your *current* config,
which makes any edit you have made since the last sync look like content
blog-craft already shipped. The merge then reads your on-disk file as a
deliberate deletion and keeps the deletion, so enabling a `features.*` flag is a
silent no-op for every `merged` path — `hugo.toml`, `assets/css/**`,
`.github/**`, `README.md` (derio-net/blog-craft#60). `/update` warns when it
takes that fallback, and records the snapshot so the next run is exact.

Blogs bootstrapped before the snapshot existed keep working: the first
conflict-free, unscoped `--apply` backfills it. A **scoped** `--only` apply
deliberately leaves it alone — a partial apply is not a sync, and recording one
would give every out-of-scope path a base built from a config it was never
rendered with.

```yaml
# .blog-craft.sync.yaml — GENERATED, DO NOT EDIT
#   <provenance header>
version: 5                    # ...then the config, verbatim, as it was at sync
blog_craft_version: "v0.16.1" #    time: comments, key order and all
...
```

Delete it only to deliberately forget what was last synced; `/update` will then
warn and rebuild it from whatever the config says today.
