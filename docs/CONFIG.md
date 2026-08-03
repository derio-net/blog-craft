# `.blog-craft.yaml` — config contract (v7)

The single per-repo file that distinguishes one blog-craft blog from another.
Validated by `tools/validate_config.py --check <path>` (accepts schema
versions 2–7; `tools/migrate_config.py` climbs the ladder; `tools/migrate_prompts.py` migrates the entries file).

```yaml
version: 7
blog_craft_version: "<release applied>"   # set by bootstrap/update; see §11

project: { name, tagline, base_url, base_path, module_path }

site_dir: .               # optional; where the Hugo site lives relative to this
                          # file (e.g. `blog` when the config sits at the repo
                          # root). Consumed by /blog-post scaffolding + /update
                          # path mapping. Default `.`.
                          # NOT everything moves with it: paths whose location is
                          # defined by a tool outside Hugo — `.github/**` (GitHub
                          # Actions) and `.claude/**` (hookify) — stay at the repo
                          # root. templates/manifest.yaml's `roots:` section is the
                          # registry of which is which; see skills/update/SKILL.md.

image:
  provider: gemini
  model: <gemini model>
  fallback_model: <gemini model>   # v7, optional; retried when `model` raises OR
                          # returns a response with no image part. Absent => one
                          # attempt, exactly as before. See §13.
  timeout_ms: 120000      # v7, optional; HTTP cap in MILLISECONDS, straight into
                          # the SDK's HttpOptions(timeout=…). Absent => the SDK
                          # default. See §13.
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
  mermaid_view: true      # v6; DEFAULT TRUE (absent => on, unlike every other
                          # features.* flag). Diagrams render at their authored
                          # size in a framed horizontal scroller instead of being
                          # shrunk to the 672px column. `false` restores the
                          # pre-v6 rendering. See §12.
  stickers:               # v7; die-cut sticker sheets (see §13). DEFAULT OFF —
    enabled: false        # absent or false ships no sticker scripts at all.
    prompts_file: blog/_private/stickers/stickers-prompts.yaml
    images_dir:   blog/_private/stickers/images
    sheets_dir:   blog/_private/stickers/sheets
    sheets_prefix: my-stickers          # optional; default <slug(project.name)>-stickers
    sheet: { size: a4, dpi: 300, grid: [3, 3], gutter: 60 }   # optional; these ARE the defaults
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

**Keep `images:` last, and keep it a block sequence.** `images:` is the only
top-level key the entries file needs, and `/blog-post` appends new entries at end of
file (it never re-dumps the document, so hand-written formatting survives). Three
layouts are therefore refused up front, each naming what it found: a hand-added
top-level key *after* the sequence (move it above `images:`), a second YAML document
or a `...` document-end marker (an appended entry would land outside the sequence),
and a **flow-style** value — `images: []` or `images: [{key: a}]` — which cannot be
extended by appending a line (rewrite it as one `- key:` item per line). The
sequence's own indentation is read from the file, so column 0 and two spaces are
equally fine, and a quoted `"images":` key is the same key. Anything the entries
themselves do is *not* a layout problem: a `description:` or a `tags: [...]` list an
operator wrapped by hand may continue at column 0 — that is ordinary content, and the
check is PyYAML's own parse rather than a scan of the columns.

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

**`output` is config-root-relative, and `/blog-post`'s default for it is
blog-dependent.** Both conventions are legitimate — a cover inside the post's
page bundle, or one collected in `image.output_dir` — so the scaffolder follows
the convention **your entries file already shows** rather than a fixed rule: if
existing entries carrying `output` are mostly under `<site_dir>/content/`, a new
entry gets `<site_dir>/content/docs/<series>/<NN>-<slug>/cover.png` (the bundle
that run just created); otherwise, and when the file has no entries yet, it gets
`<image.output_dir>/<key>-cover.png`. `blog-post-create.sh --output <path>`
overrides the detection. Every blog in the field keeps the default it already had.

**`key` is never detected.** It defaults to `<series>-<number>`. A blog keyed
`ops-30-silent-failure` off a series named `operating` needs an abbreviation that
lives in no config field, so `--key <key>` is an explicit override — read an
existing entry and match it rather than hoping.

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

`series_index.layers` is also the registry `/blog-post` validates `--layer`
against: an unregistered code is an error naming the valid ones, and a post
scaffolded **without** `--layer` on a blog that declares layers gets a greppable
`layer: TODO` plus a warning (an unmatched code renders exactly like no layer, so
the placeholder is inert). Declare no layers and the scaffolder emits no `layer`
key at all.

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
| `mermaid_max_width` | `1400` (px) | **Blocks.** Maximum rendered width of any mermaid diagram in the built site. Not a per-post gate: it runs after `hugo` against `public/**/*.html` and **fails CI** for every diagram over budget, naming page, block index, measured width and overage. `1400` is ~2× the 672px content column — a diagram needing more than two column-widths of scrolling can't be held in the reader's head. Waive one diagram with a `%% blog-craft: wide-ok — <reason>` comment in its own source; set `0` to disable the gate (still loud: it lists what it did not measure). See §12. |

Run it directly:

```bash
python <blog-craft>/tools/validate_educational.py --config .blog-craft.yaml \
    content/docs/<series>/<NN>-<slug>/index.md
```

The validator ships into every blog at `scripts/validate_educational.py` (a
byte-identical copy of `tools/validate_educational.py`), so a plain-python CI runs
it without the plugin.

### AI-tells lint (`quality.lint`)

Runs with the gate above, **warnings-first**: it flags the surface patterns that
make prose read machine-written without pushing the drafting toward
regex-gaming. Only the conservative AI-vocabulary list *fails* by default; the
density metrics (em-dash, negative parallelism, rule-of-three triads), cliché
conclusion openers, and the missing what-transfers section on
tutorial/explanation posts *warn*. Warnings print as `LINT WARN:` lines and
never affect the exit code; `LINT FAIL:` lines exit nonzero alongside gate
failures.

```yaml
quality:
  lint:
    enabled: true          # false => skip the lint entirely (gate-only run)
    severities:            # per-check: fail | warn | off
      vocabulary: fail     # default fail — the only failing check
      em_dash: warn
      negative_parallelism: warn
      triad: warn
      conclusion: warn
      what_transfers: warn
    thresholds:            # per-1000-words densities (numbers)
      em_dash_per_1000: 8
      negative_parallelisms_per_1000: 2
      triads_per_1000: 3
```

Every key is optional — an **absent `quality.lint` block means defaults**
(vocabulary fails, everything else warns). The word lists, regex patterns, and
default thresholds live in **one source**:
`skills/educational-writing/references/ai-tells.md` (its fenced yaml block) —
the drafting skills apply the same catalog as prose guidance, so instruction
and mechanics cannot drift apart. The file ships into every blog at
`scripts/ai-tells.md` next to the validator; if it is missing (a blog whose
`scripts/` predates it), the run prints `LINT SKIPPED:` and stays gate-only.
The drafting skills seed `quality.lint.enabled` on their first run; until then
the absent block simply means defaults.

Mode-conditional checks (what-transfers) key off the `diataxis` frontmatter
(tutorial/explanation), never series names. All matching runs on prose only —
fenced code blocks, inline code spans, and frontmatter never trip the lint.

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
GC_GOATCOUNTER:
  rendered_text: GC                     # optional; defaults to the key
  name: GoatCounter
  description: >-
    The analytics tool behind the visitor numbers — the second sense of `GC` in
    this blog.
```

- Keyed by the literal token as it appears in prose. **Case-sensitive.**
- `name` and `description` are required. `url` is optional, must be absolute
  `http(s)`, and renders as a "Read more" link inside the panel.
- `rendered_text` is optional: a non-empty string containing no double quote
  (it is copied into a shortcode argument, and a quote there emits an unparseable
  shortcode). A wrong type, an empty or whitespace-only value, or an embedded
  quote is an **error**; absent, it **defaults to the key**.
- Two entries **may** share a `rendered_text` — that is the whole point of the
  field, and the validator never reports it. It is how one abbreviation carries
  two expansions: `GC` (Garbage Collection) and `GC_GOATCOUNTER`
  (`rendered_text: GC`) both read `GC` on the page.
- The **key stays the identifier.** The shortcode lookup, the panel `id` and the
  CSS anchor name are all key-derived, so two senses on one page get two anchors
  and no collision. `rendered_text` moves only what the reader sees — the
  `<abbr>` body, the `aria-label`, and the index row.
- Display text resolves by one precedence chain in both surfaces:
  **call-site argument 1 › `rendered_text` › the key.**
- `{{< glossary-index >}}` sorts on the **resolved display text**, with the key as
  tiebreaker. A no-op for a registry with no `rendered_text`; with one, it keeps
  the two senses of an abbreviation adjacent instead of ordering them by an
  identifier the reader never sees.
- **A second sense is marked by hand.** `/glossary` matches literal prose tokens
  against keys, so it can only auto-mark the default sense — a bare `GC` in a post
  becomes `{{< abbr "GC" >}}`. Write `{{< abbr "GC_GOATCOUNTER" >}}` yourself
  where the other sense is meant.
- Classified `content` by `templates/manifest.yaml` (`data/**`), so **`/update`
  never touches your definitions.**
- Keep it alphabetically sorted **by key**; the validator warns (never fails)
  otherwise. Key order, not display order — the file is read as a keyed mapping.

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
positional and named parameters in one shortcode call. It also wins over the
entry's own `rendered_text`, so a second-sense entry still pluralizes:
`{{< abbr "GC_GOATCOUNTER" "GCs" >}}`.

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
| `rendered_text` that is not a string, or is blank, or contains a `"` | **error** |
| two keys differing only in case | **error** |
| two entries sharing a `rendered_text` | *never reported — that is the feature* |
| an entry no post references | warning |
| the registry is not alphabetically sorted by key | warning |

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

**Read the backfilling run's output.** Recording the first snapshot fixes every
future update, but it also freezes whatever the tree currently holds — including
a change an earlier, pre-#60 run already dropped. After that the path is an
ordinary `NOOP` with nothing flagged on it. So that one run lists every `merged`
path its fallback base resolved to `NOOP`, with how to diff each against a fresh
render; anything that differs is shipped content you are missing.

```yaml
# .blog-craft.sync.yaml — GENERATED, DO NOT EDIT
#   <provenance header>
version: 5                    # ...then the config, verbatim, as it was at sync
blog_craft_version: "v0.16.1" #    time: comments, key order and all
...
```

Delete it only to deliberately forget what was last synced; `/update` will then
warn and rebuild it from whatever the config says today.

## §12 Mermaid rendering (`features.mermaid_view`)

```yaml
features:
  mermaid_view: true    # v6; default TRUE — absent means on
```

Mermaid renders with `useMaxWidth: true`, which scales every SVG down to fit its
container. Hextra caps the content column at 672px on every viewport (the shell
is `80rem`, so a 3840px 4K panel gets the same column a 1440px laptop does), so a
diagram whose natural width is 2139px renders at **31% scale** — label text
authored at 14px paints at 4.4px. This is not a wide-screen problem; every reader
gets the same 31%.

With this feature on, each diagram renders at its **authored size** inside a
framed, horizontally scrollable block — the way a wide table behaves. Nothing is
scaled down, so nothing becomes illegible; a diagram that fits is untouched.

### The mechanism — and the one edit that would destroy it

Mermaid writes `style="max-width: <natural>px"` **inline** on each rendered SVG.
Inline author declarations beat stylesheet ones, and `max-width` beats `width`
regardless of origin. So one rule does the whole job:

```css
.content .mermaid svg { width: 200rem; }
```

which resolves to `min(200rem, natural)`. A 428px diagram stays 428px and never
scrolls; a 2139px one renders full size in the scroller; nothing is ever enlarged
past its authored size. No per-diagram tuning, and because it is pure CSS it
survives the dark/light re-render that `mermaid-init.js` performs by resetting
`innerHTML` (see §10) — a JS-attached wrapper would not.

**Do not add a `max-width` to the SVG in your own stylesheet.** It competes with
the inline value the whole feature keys off. (`.content .mermaid svg { max-width:
100% }` shipped in `custom.css.tmpl` long before this feature and is *inert* once
mermaid has rendered, for exactly the same reason — the inline declaration wins.
Removing it is neither necessary nor sufficient.) `mermaid-view.css` is loaded
**before** `custom.css`, so everything the frame sets is a default you can
override in your own sheet; the width line is the one to leave alone.

### The two scroll affordances, and why one is not enough

A scroller nobody can see they can scroll is a diagram that is silently truncated
— it *looks* complete, and the reader never learns the right-hand third exists.
Two independent cues ship, because each fails in a case the other covers:

1. **A scrollbar that is actually painted.** macOS (and iPadOS, and Chrome with
   overlay scrollbars) defaults to an overlay bar that paints nothing at rest.
   Measured on the prototype: `offsetHeight - clientHeight == 0` without the fix,
   `9px` with it. Only `-webkit-appearance: none` on `::-webkit-scrollbar` opts
   out of the overlay — *sizing the pseudo-element alone does not.*
2. **Scroll shadows.** `background-attachment: local, local, scroll, scroll`:
   cover gradients in the frame colour travel with the content, sitting on top of
   edge shadows pinned to the scroller. Scroll right and the left cover slides
   away, uncovering the shadow. Self-cancelling at both ends, no JS. The colours
   are custom properties that **invert** with the theme, since a black shadow is
   invisible against a `#111` frame.

The standard `scrollbar-width` / `scrollbar-color` properties are gated behind
`@supports not selector(::-webkit-scrollbar)`, and that gate is load-bearing, not
tidiness: in Chrome and Safari those two properties **win over the WebKit
pseudo-elements and disable them**, silently restoring the invisible overlay bar.
Hoisting them out of the feature query to "support both engines" turns affordance
1 back off, with no error and nothing in devtools to see. Firefox, which has no
`::-webkit-scrollbar`, is the only engine that reads them.

### Keyboard reachability

A scroll container that only a trackpad can reach fails WCAG 2.1 SC 2.1.1. The
feature therefore overrides Hextra's `_markup/render-codeblock-mermaid.html` to
add `tabindex="0"` to the `<pre>`, so the diagram takes focus and the arrow keys
scroll it. The override otherwise reproduces the theme hook exactly — including
`role="img"`, its i18n `aria-label`, and `.Page.Store.Set "hasMermaid" true`,
which the theme's own scripts partial depends on to load mermaid at all. That
pins the feature to the theme hook's shape: re-check it on a Hextra bump.

### Turning it off

```yaml
features:
  mermaid_view: false
```

`false` is the only way to opt out — **absent means on**, unlike every other
`features.*` flag, so a blog that has never heard of this key still gets the fix.
With `false` the module is not materialized at all (no stylesheet, no render-hook
override) and diagrams render exactly as they did before v6. `/update` runs
`migrations/005_to_006.py`, which writes `mermaid_view: true` for existing blogs
but leaves an explicit `false` alone.

### Related: the width gate

Rendering at authored size makes wide diagrams legible; it does not make them
*followable*. `quality.mermaid_max_width` (§7, default `1400`px) fails the build
for any diagram that would need more than ~2 column-widths of scrolling. The two
are deliberately separate knobs: turning the scroller off does not turn the gate
off, and vice versa. The gate measures a real render of the **built** site with
the site's **own** mermaid bundle — reading width from the same inline
`max-width` the CSS keys off, so gate and renderer cannot disagree.

## §13 Die-cut sticker sheets (`features.stickers`)

**v7, default OFF.** An opt-in capability that composes sticker prompts through
the *same* engine as covers and lays the chosen images onto print-ready sheets at
a real DPI. It ships **no Hugo assets** — no page, shortcode, gallery or CSS —
because a sticker set is a private **print** asset. Two scripts land at
`<site_dir>/scripts/` when it is on, and nothing at all when it is off:

| script | does |
|---|---|
| `scripts/generate-stickers.py` | generates candidates through `generate-images.py`, never over the masters |
| `scripts/build-sheets.py` | composes the print sheets from the chosen masters |

**Why default OFF, and how the gate reads.** `tools/bootstrap-render.sh` follows
the `features.glossary` shape, not the `features.mermaid_view` one: `--get-bool`
reports `false` for a key that is simply **absent**, so a blog that never asked
for stickers gets neither script. (`mermaid_view` checks `--has` first because
absence there means *true*; copying that shape here would have shipped sticker
scripts to every existing blog.) `migrations/006_to_007.py` seeds
`features.stickers: {enabled: false}` for existing blogs and leaves an explicit
`true` alone — so after an update the normal shape is **present and disabled**,
and `absent` is the legacy one.

### The keys

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | `false` | Materializes the two scripts. `generate-stickers.py` also refuses to run when it is not `true`. |
| `prompts_file` | — | The sticker entries file, config-root-relative. **Separate from `image.prompts_file`**, so `sheet`/`pos` stay out of cover entries and the sticker keys out of the cover key namespace. |
| `images_dir` | — | Where the curated masters live. `build-sheets.py` falls back to `<images_dir>/sticker-<key>.png` for an entry with no `output:`. |
| `sheets_dir` | — | Where the built sheets are written. |
| `sheets_prefix` | `<slug(project.name)>-stickers` | Filename prefix, so the port is not frank-shaped: output is `<sheets_dir>/<prefix>-<SIZE>-sheet<N>.png`. |
| `sheet.size` | `a4` | Paper name from `build-sheets.py`'s millimetre table (`a4`, `letter`). |
| `sheet.dpi` | `300` | Written **into** the PNG, which is what makes "print at 100%" work. |
| `sheet.grid` | `[3, 3]` | `[cols, rows]`. Genuinely honoured — it also sets `pos`'s valid range (`1..cols*rows`). |
| `sheet.gutter` | `60` | Pixels between cells and around the grid. |

`tools/validate_config.py` requires the three path keys **exactly when `enabled`
is `true`** (a disabled block is allowed to be the stub the migration seeds), and
checks `sheet` geometry whenever the block is present, enabled or not — bad print
numbers are nonsense either way, and `build-sheets.py` would otherwise discover
them at print time. Checks fire on a key being **present**, so a half-written
`enabled:` (YAML `None`) is an error rather than a silent no-op.

**`sheet.size` is deliberately not validated there.** The paper vocabulary
belongs to `build-sheets.py` so the table can grow without a schema change, which
makes that script the only guard: an unknown size is a hard error naming the
known ones, never a silent fallback to A4.

### The page is derived, not configured

There is no key for page pixels. They come from `size` + `dpi`:

```
round(210 / 25.4 * 300) == 2480      # A4 width  @ 300 dpi
round(297 / 25.4 * 300) == 3508      # A4 height @ 300 dpi
```

Adding explicit pixel keys would let `size: a4` and an inconsistent pixel size
disagree — a wrong-sized page that prints wrong. **The derivation is per axis and
is not a linear scale**: at 600 dpi the A4 *height* doubles (`7016 == 2 × 3508`)
but the *width* is `4961`, not `2 × 2480 = 4960`, because `round()` is not
linear. Read it as `round(mm / 25.4 * dpi)` per axis, never as "twice the dpi,
twice the sheet".

The DPI is written into the file (`page.save(dest, dpi=(dpi, dpi))`), which PNG
stores as integer pixels **per metre** — 300 dpi is `pHYs 11811`. That is why
Pillow reads it back as `299.9994`: the integer chunk is the contract, the float
is a derived convenience.

### Placement, and two silent failures made loud

Each sticker entry carries `sheet` (1-based) and `pos` (1-based cell,
left→right then top→bottom); an entry with neither is simply not on a sheet.
Three ways to get it wrong are all errors that refuse the run before any page is
composed, because the failure mode they share is a **printed** sheet with a hole
in it — paper, ink and manual cutting spent before anyone notices:

- a `pos` outside `1..cols*rows` for the configured grid;
- a **duplicate `(sheet, pos)`** — the same cell claimed twice. The message names
  both stickers and the cell. The same `pos` on a *different* sheet is legal and
  normal;
- a missing image file for a placed sticker.

The engine has the matching guard on the prompt side: an entry whose composed
prompt is **empty** is still skipped, but now with a `WARN` naming the key
instead of in silence. That is a warning and not an error on purpose — an
operator may have a legitimately empty entry, and a non-zero exit there would be
a behaviour change on the cover path every blog takes.

### The sticker composition order, and the `_template` directive

Sticker layers are namespaced `sticker_*` because the prose **contradicts** the
cover prose — a cover `base_character` says "flat-top hair" while a sticker one
says "NOT a hard blocky / square flat-top". They cannot share a layer name.

```yaml
image:
  composition_orders:
    sticker:
      - sticker_base_character
      - sticker_atmosphere
      - sticker_reference_guidance
      - sticker_face_pins
      - clothing
      - sticker_mood
      - scene
      - sticker_border_spec      # AFTER scene, not before
  layers:
    sticker_mood:
      _template: "Frank's expression: {}."
    clothing: {}                 # only when the blog has no `clothing` layer
    sticker_base_character: |- …
```

`sticker_border_spec` **follows** `scene`: the sticker finish is described after
the scene it frames. Swapping those two produces a prompt that reads perfectly
well and is not the one that made the artwork.

An entry composes with the **bracketed** reference:

```yaml
composition:
  order: composition_orders[sticker]      # a bare `sticker` is NOT a synonym
  modifiers: { sticker_mood: <free-form text>, clothing: <free-form text> }
```

A bare `sticker` matches no order reference, resolves to an empty token list and
composes an empty prompt — which is precisely the case the new WARN above exists
to shout about.

**`_template` (v7, `compose.py`).** A dict layer may declare
`_template: "… {} …"`, which frames the value the layer resolved to — a table
hit or a free-form passthrough alike. A layer that resolves to `""` stays `""`
(an empty section is dropped, and `"Frank's expression: ."` would be a bug).
`{}` is a positional `str.format` field, so prose containing braces passes
through unharmed — only the *template* is parsed. The validator requires exactly
one `{}` and **no other brace anywhere**, which is stricter than "one
placeholder" by policy: a frame then has one obvious spelling, stays diffable,
and can be emitted mechanically.

> **Never put `_template` on a shared layer whose values are already complete
> sentences.** `_template` attaches to a **layer**, so it applies to every order
> naming that layer. A cover `mood` table like
> `curious: Frank's expression is curious — head tilted…` framed with
> `"Frank's expression: {}."` composes
> `Frank's expression: Frank's expression is curious — …` on **every cover** —
> silently, because sticker goldens only cover sticker prompts. That is why the
> frame lives on its own `sticker_mood` layer and sticker entries carry
> `modifiers.sticker_mood`, never `modifiers.mood`.
>
> Relatedly, `validate_config.py` **rejects** an order token `X[y]` whose layer
> `X` declares `_template`: the bracket-token path resolves a named chunk without
> a modifier and is deliberately not framed, so `X` and `X[y]` look identical in
> config and differ only by silently losing the frame.

Also load-bearing, and the easiest way to break every sticker prompt at once: a
layer **absent** from `image.layers` resolves to the empty string and `compose()`
drops the section. So a blog with no `clothing` layer needs `clothing: {}` for
the sticker `clothing` prose to survive — the empty table is not decorative.

### Non-destructive generation — the `--out` contract

The sticker workflow is *pick a winner, then copy it over*, and the engine's
default is to write the last variant straight to the entry's `output:`. So
`generate-stickers.py` **always** passes `--out`, defaulting to `regen`:

```bash
scripts/generate-stickers.py --list                 # keys, sheet/pos, description
scripts/generate-stickers.py --dry-run              # the FULL prompt + resolved refs, no API call
scripts/generate-stickers.py --only 01-wave,05-key  # regenerate two
scripts/generate-stickers.py                        # regenerate all into <config root>/regen/
# eyeball regen/, then copy the winner over the master, then:
scripts/build-sheets.py
```

Under `--out DIR` (`generate-images.py`, available for covers too):

- the entry's `output:` is **never** written, and its parent directories are not
  even created;
- the filename is the **basename of the entry's `output:`**; when two or more
  *selected* entries collide on that basename, every member of the colliding
  group becomes `<key>-<basename>`. Deterministic — a function of the selected
  set, not of iteration order — and extension-correct. For stickers it yields
  exactly `sticker-<key>.png`, the name of the master to copy over;
- a `DIR` that would alias any selected entry's `output:` (including through a
  symlink or a hard link) **refuses the whole run** before the first API call. A
  path-shaped promise is not a guarantee;
- `post_process` is skipped entirely: those steps write over or next to the
  *published* asset;
- `.regen-archive/<key>/` snapshots and `.txt` sidecars are written as usual. The
  sidecar records `output: <entry path>` as provenance — it is where a chosen
  winner *belongs*, not a file that was written;
- `--dry-run` names the `--out` destination, not the `output:` path it will never
  touch;
- a relative `--out` is resolved by the **shim** against the config root and
  handed to the engine absolute; the engine's own `--out` is CWD-relative, like
  `--reference`.

`--count` is deliberately not exposed on the shim. A `--count N` run needs
`image.curation.archive_cap >= N`, or the archive FIFO prunes that run's own
earlier variants mid-run (it now warns and proceeds with the survivors instead of
crashing); use `generate-images.py --count` directly, with the cap raised.

**Two contact sheets, and the one that is an accepted divergence.** The engine
writes a per-**key** sheet across that key's variants to
`.regen-archive/<key>/contact-sheet.png`, only when `--count > 1` — so a sticker
run, which makes one image per key, never produces one. The run-level sheet the
sticker runbook points at is therefore built by the **shim**, at
`<out>/contact-sheet.png`, whenever at least two keys succeeded, with `cols=5,
tile_width=420`. Its **layout** is blog-craft's `_contact_sheet` (label at the
top of a fixed tile), which differs from the pre-port private helper
(aspect-preserving thumbnails, label in a strip along the bottom). The artifact
is review-only and the old helper no longer exists, so this is declared, not
reproduced.

### The two reliability knobs (`image.fallback_model`, `image.timeout_ms`)

Both are engine-wide, not sticker-specific, and both are absent by default —
with neither set, cover generation is byte-for-byte what it was.

- `image.fallback_model` is attempted when the primary **raises** or returns a
  response with **no image part**, with each attempt logged to stderr with its
  model name and the exception *type*. It adds a retry; it never softens a hard
  failure: if every configured model raises, the last exception **propagates**
  (and with no fallback configured, the single attempt propagates unchanged, as
  before). An image-*less* response stays a soft failure — `rc=1` for that key,
  nothing written. Mixed case — primary raises, fallback answers without an image
  — propagates the primary's exception, because reporting "the model declined"
  for a transport or auth error would mislead.
- `image.timeout_ms` is **milliseconds**, passed to the SDK's
  `HttpOptions(timeout=…)`.

### Adopting an existing private sticker set

`tools/migrate_stickers.py` is a one-time, blog-craft-side transform (it is never
shipped into a blog):

```bash
tools/migrate_stickers.py --config <blog>/.blog-craft.yaml \
    --legacy <blog>/blog/_private/<dir>/stickers.yaml [--move-assets] [--dry-run]
```

Both paths are required and nothing is guessed; everything resolves against the
config's own directory, never the process CWD. It writes the new
`features.stickers.prompts_file`, **prints** the `image.layers` +
`composition_orders.sticker` block for the operator to paste, and — only under
`--move-assets` — `git mv`s `images/` and `sheets/` into the configured
directories, refusing rather than clobbering when a destination already exists.
It never edits `.blog-craft.yaml`: that file is the operator's content.

Three things about the printed block that are easy to get wrong:

- **`clothing: {}` is emitted only when the target config has no `clothing`
  layer.** Emitting it unconditionally would *destroy* a populated one:
  PyYAML resolves duplicate mapping keys by silently taking the last, and a cover
  entry that selects with the bracket form (`building[dirty]`) then resolves
  nothing and loses its clothing sentence **entirely**. When the layer exists the
  key is omitted with a note, and the tool *checks* rather than assumes that the
  existing layer still returns every sticker's prose unchanged.
- **it never emits a bare `mood:` key**, for the double-framing reason above.
- it **warns** about any emitted key the target config already defines, and
  **refuses** an empty `clothing`/`mood`/`scene`, a duplicate sticker key, a
  configured path escaping the blog root, and a `prompts_file` that resolves to
  the legacy source itself (writing there would destroy the only copy of the
  prose being migrated — name the new file `stickers-prompts.yaml`, not
  `stickers.yaml`).

**What `/update` does and does not do.** `templates/manifest.yaml`'s
`legacy_dests` retires the two *scripts*: `scripts/build-sheets.py` and
`scripts/generate-stickers.py` are `framework`, so the planned action is
`replace` — blog-craft's copy wins and the private one is unlinked. Local edits
to those two scripts are **discarded**, deliberately; only `merged`-class files
preserve operator edits. Everything else in that private directory is `content`
— the legacy `stickers.yaml`, the curated masters, the built sheets, the README —
and `/update` never touches content, so **the directory itself survives** while
it still holds any of it. Emptying it is the operator's last step, not
blog-craft's. For a blog that never had those paths there is no legacy side to
find, so nothing is relocated and nothing is deleted; with the feature disabled
the scripts are not even staged.

The order matters, because the transform refuses when `features.stickers` is
missing or its paths are empty:

1. `/update` — climbs the schema ladder to v7 (seeding the disabled block) and
   retires the two private scripts;
2. paste the printed block; set `features.stickers.enabled: true` plus the three
   paths;
3. `tools/migrate_stickers.py … --move-assets`;
4. `git rm` what is left of the private directory, then delete the directory by
   hand;
5. rebuild the sheets and confirm they are unchanged.
