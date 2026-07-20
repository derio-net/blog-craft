# Image composition as a first-class, generic, optional system

**Date:** 2026-07-20 · **Branch:** `feat/image-composition-system` · **Closes:** #39 · **Supersedes:** PR #40 (absorbed)

## Context

blog-craft already ships the v2 layered composition *engine*
(`templates/hugo-hextra/scripts/generate-images.py` + `compose.py`, spec'd in
`docs/CONFIG.md` §4.1): a dumb concatenator that walks `image.composition_order`
and resolves each named layer from `image.layers` + the per-image entry. frank
and gondor-blog both run it today with completely different layer vocabularies.

What never migrated is everything *around* the engine:

- `skills/blog-post/SKILL.md` Step 6 hand-composes prompts from a dead
  `metaphor.*` vocabulary; Step 7 reads `image_gen.api_key_env`. Neither key
  exists in the shipped config contract (#39 item 3).
- `skills/bootstrap-blog/SKILL.md` Steps 2/5/7/8 collect `metaphor.*` +
  `image_gen.*` and write `metaphor.reference_image` — the generator reads
  `image.reference_image` (#39 drift).
- `tools/blog-post-create.sh` validates `.blog-craft.yaml` exists then never
  reads it: hardcodes `prompts_file`/`output_dir`/bundle dir, forces
  `static/images/reference.png` (hard `exit 3`), and appends a *fully composed*
  prompt as the entry `prompt:` — which the engine treats as the `scene` layer
  only, so a layered blog would double-compose (#39 items 1–2).
- No config key places a Hugo site in a subdirectory. frank keeps
  `.blog-craft.yaml` at the repo root with the site under `blog/` — neither
  `BLOG_ROOT` choice works (#39 item 4).
- An entry's `references:` anchors never reached the model (#39 item 5) — fixed
  by PR #40, which this branch absorbs; #40's `test` check fails because the
  other `_gen_bytes` caller, `scripts/gen-character-sheet.py`, wasn't updated
  for the new `root` parameter.
- The engine still hardcodes two layer names: `torso` (selected by
  `entry.torso or entry.series`, indexed by `entry.torso_variant`) and `mood`
  (named preset with free-form passthrough) — `compose.py:29-43`.
- `gen-character-sheet.py` hardcodes `layers.persona` + `layers.visual_constants`
  — frank's character prose lives in `base_character`, so the sheet tool cannot
  serve frank.

**Operator decisions (batched Q&A, 2026-07-20):**

1. Absorb PR #40 into this branch; the PR notes it supersedes #40.
2. The engine becomes **fully generic**: it parses *any* map of category-key →
   prose. Standard per-entry fields (`key`, `output`, `prompt`, `aspect_ratio`,
   …) stay fixed; everything else is selector data for config-declared
   dictionaries. One blog controls the hero, another the scenery, another both
   or multiple heroes — all pure data. Config *organization* (grouping shared
   prose under `reference_guidance`, selectors under `mood`/`style` dicts) is a
   per-blog convention the engine does not impose.
3. Migration is delivered post-merge via **two Test Plans**: frank
   (`derio-net/frank`) and gondor-blog (`derio-homelab/gondor-blog`). "Correct
   configuration ⇒ no visible change": composed prompts stay byte-identical and
   the dry-run image payload stays identical.
4. Extras in scope: the image-pipeline **validation suite** (replacing frank's
   orphaned `tests/image-pipeline/test_pipeline.py`), the **extract-subject**
   tool, and a **generic character-sheet function**. Pool random-sampling
   (`--pool-generic`/`--pool-series`) is declined — explicit `references:` only.

## Goals

1. **Generic engine** — remove the `torso`/`mood` hardcoding; any dict layer
   resolves through a config-declared selector path.
2. **Close #39 end-to-end** — config-driven scaffolder, scene-only entries with
   selector fields, `site_dir` support, references in the payload (PR #40 +
   the `gen-character-sheet.py` caller fix).
3. **Skills speak the shipped contract** — `--print-prompt` becomes the single
   source of composed prompts; no skill hand-concatenates layers.
4. **`/update` migrates existing blogs** — site-dir path mapping, path-scoped
   application (`--only`), and a config schema migration (v3 → v4) that
   rewrites `metaphor.*`/`image_gen.*` vocabulary and encodes the previously
   hardcoded engine rules as explicit config data.
5. **Byte-parity guarantee** — frank's and gondor's composed prompts are
   unchanged through migration, proven by CI fixtures and the post-merge Test
   Plans.

## Non-goals

- Pool random-sampling (declined in Q&A).
- Replacing a migrated blog's theme/layouts wholesale. `/update --only` lets
  the operator scope migration to the image machinery; whole-site adoption is a
  separate decision per blog.
- Multi-provider image APIs (gemini-only, as today).
- Changing the composed-prompt format (`"\n\n".join(non-empty sections)` stays
  byte-compatible).

## Design

### D1 — Generic layer resolution (schema v4)

`compose.py` keeps its shape (stdlib-only, dumb concatenator). Resolution rules:

| Layer value | Resolves to |
|---|---|
| scalar | the string, verbatim |
| list | `- ` bulleted lines |
| dict | **selector walk** (below) |
| `scene` (reserved) | the entry's `prompt` field |

**Selector walk.** A dict layer may declare `_select:` — a list of selection
steps. Each step is an entry-field name, or a list of field names (first
present wins). Default when `_select` is absent: `[<layer-name>]` (the
same-named entry field selects), preserving today's generic-table behaviour.

Walking: start at the table (minus `_`-prefixed keys, which are reserved for
directives and never prose). For each step, read the entry field:

- field **missing** → the layer resolves to `""` (skipped), as today;
- value is a **key** of the current dict / a valid **int index** of the current
  list → descend;
- value doesn't select, and this is the **last** step → return the entry value
  verbatim (**free-form passthrough** — today's `mood` and string
  `torso_variant` behaviour, now universal);
- value doesn't select at an **intermediate** step → `""` (a bad group never
  passes through as prose).

If the walk ends on a non-scalar (steps exhausted before reaching prose), the
layer resolves to `""` — `validate_images.py` (D8) flags it.

**Deliberate v4 semantic change:** today only `mood` passes an unknown selector
value through as prose; a *generic* dict layer returns `""`. In v4 the
passthrough-at-last-step rule is universal. No shipped fixture or known blog
uses a generic dict layer (only `torso`/`mood` exist in the wild, and both are
passthrough-compatible), the parity fixtures prove non-divergence, and
`validate_images.py` flags selector values that silently miss their table —
which is what makes universal passthrough safe to adopt.

frank's `torso` becomes pure data:

```yaml
layers:
  torso:
    _select: [[torso, series], torso_variant]
    building: ["…variant 0…", "…variant 1…"]
    operating: ["…"]
  mood:               # default _select: [mood]; passthrough is now the generic rule
    cautious: "Frank's expression is cautious — alert but not anxious; …"
```

The engine's special-cased `torso`/`mood` branches are **deleted**. The 003→004
migration writes the explicit `_select` for any dict layer named `torso`
(the only case whose default selector changes meaning); `mood` needs nothing.

**Standard entry fields** (consumed by the generator, never selector data):
`key`, `series`, `output`, `description`, `prompt`, `aspect_ratio`,
`image_size`, `references`, `count`, `operator_generated`, `post_process`.
Every other entry field exists to be selected on by some layer's `_select`.
CONFIG.md §4.1 is rewritten to state both tables.

### D2 — PR #40 absorbed

Cherry-pick `fix/generate-images-entry-references` (`entry_reference_paths()`,
`_gen_bytes(..., root)`, dry-run payload listing, its 6 unit tests, CHANGELOG
entry), then fix the caller the PR missed:
`gen-character-sheet.py:83` passes `ROOT` as the new `root` argument. The
bootstrap smoke (`smoke-character-sheet.sh`) that failed #40's `test` check
goes green. Version numbers are re-resolved on this branch (single minor bump,
D9) rather than #40's 0.8.1.

### D3 — `site_dir`

New optional top-level config key `site_dir: <rel-path>` (default `.`): where
the Hugo site lives relative to `.blog-craft.yaml`. frank sets `blog`.

Consumers:
- `tools/blog-post-create.sh` — bundle dir becomes
  `<blog_root>/<site_dir>/content/docs/<series>/<NN>-<slug>`.
- `tools/update.py` — path mapping (D6).
- `docs/CONFIG.md` + `validate_config.py` — documented, validated as a
  relative path that exists.

The generator needs no change: it already resolves everything relative to the
config's directory, and frank's entry `output:`/`prompts_file` paths carry the
`blog/` prefix by that convention.

### D4 — Scaffolder rewrite (`tools/blog-post-create.sh`)

- **Reads the config it requires.** A new `tools/blog_config.py` helper
  (python3 + pyyaml, mirrored into blogs as `scripts/blog_config.py`) prints
  resolved keys: `blog_config.py --config <path> get image.prompts_file
  [--default …]`. The shell script uses it for `prompts_file`, `output_dir`,
  `reference_pool`, `site_dir`. (Why not `render-template --get-bool`: we need
  strings, and a Python reader is testable and reusable by `validate_images.py`.)
- **Scene-only entries with selector fields.** The prompt-file argument now
  carries the *scene* only. New repeated flag `--entry-field k=v` (and always
  `series: <series>`) emits selector fields into the appended entry. The entry
  the helper writes is exactly what the engine wants — no double composition.
- **Optional `--output <path>`** overrides the default
  `<output_dir>/<key>-cover.png` (frank's convention puts covers inside page
  bundles; the skill passes the blog's convention through).
- **No forced reference.** The `exit 3` block and forced
  `--reference static/images/reference.png` are deleted; the generator's own
  precedence (CLI override → `image.reference_image` → pool by series →
  generic pool → none) decides.

### D5 — Skills rewritten to the shipped contract

- **`skills/blog-post` Steps 5–8:** Step 5 collects the scene brief; a new
  sub-step reads `image.composition_order` + `image.layers` and, for each dict
  layer, proposes a selector value (listing the table's keys; free-form
  allowed — passthrough is now a documented engine rule). Step 6 no longer
  hand-composes: the helper appends the entry first, then previews via
  `python <site_dir>/scripts/generate-images.py --print-prompt <key>` — the
  engine is the single composition source. Step 7 reads `image.api_key_env`.
- **`skills/bootstrap-blog` Steps 2/5/7/8:** the metaphor interview now writes
  `image.layers` + `image.composition_order` directly (default vocabulary for
  new blogs: `base_style`, `persona`, `visual_constants`, `scene`,
  `reference_guidance` — gondor's shape), `image.*` settings replace
  `image_gen.*`, the reference destination is written to
  `image.reference_image`, and Step 8 previews via `--print-prompt` instead of
  hand-concatenation.
- Docs that repeat the old vocabulary (`docs/USING-ON-A-HOST.md`, template
  comments) are swept in the same pass.

### D6 — `/update` generalization

`tools/update.py`:

- **Path mapping.** A pure function `map_dest(path, cfg) -> str` maps each
  staging-relative path to its blog-relative destination:
  `.reference-pool/**` → `<image.reference_pool>/**`;
  `prompt_for_images.yaml` → `<image.prompts_file>`; everything else →
  `<site_dir>/<path>`. Identity when `site_dir: .` and the defaults hold — so
  every existing blog's plan is unchanged (regression-guarded). Classification
  still runs on the *staging-relative* path (the manifest stays site-shaped);
  the plan records and applies to the mapped destination. `--blog` points at
  the **config root** (frank's repo root), not the site dir.
- **`--only <glob>`** (repeatable) filters the plan to matching
  staging-relative paths — this is what makes "migrate the image machinery
  only" expressible: `tools/update.py --config .blog-craft.yaml --blog .
  --only 'scripts/**' --apply`.
- **Adoption without a rendered baseline** needs no new mode: framework paths
  replace/add regardless of base; merged paths without a usable base already
  surface as `conflict (no base to merge from)` and are never auto-resolved.
  The `/update` skill documents the adoption flow (first `--only`-scoped
  apply, then record `blog_craft_version`). frank's pinned SHA works with
  `git archive`.

`skills/update/SKILL.md` gains the migration runbook: config ladder first
(`migrate_config.py`), then plan, then scoped or full apply, then parity check
(`--print-prompt` diff against a pre-migration snapshot).

### D7 — Config schema migration 003 → 004 (`migrations/003_to_004.py`)

Pure + idempotent (runs only on `version == 3`; gondor at v2 rides the ladder
002→003→004). In one pass:

1. **`metaphor.*` → `image.layers`.** If a `metaphor` block exists:
   `base_style`/`persona`/`visual_constants`/`reference_guidance` become
   same-named layers; `metaphor.reference_image` → `image.reference_image`;
   `image.composition_order` (when absent) is set to
   `[base_style, persona, visual_constants, scene, reference_guidance]` —
   exactly the order the old skill hand-composed, so composed output is
   unchanged. The `metaphor` block is removed.
2. **`image_gen.*` → `image.*`** (merge; existing `image.*` keys win), block
   removed.
3. **Encode the engine's old hardcoding as data:** a dict layer named `torso`
   gains `_select: [[torso, series], torso_variant]` if it has no `_select`.
4. `version: 4`.

`validate_config.py` learns v4: `site_dir` (optional, relative),
`_select` shape (list of str-or-list-of-str), `image.character_sheet.layers`
(optional list). CONFIG.md header moves to v4.

### D8 — Character sheet, validation suite, extract-subject

- **`gen-character-sheet.py`:** character prose comes from config —
  `image.character_sheet.layers` (default `[persona, visual_constants]`, so
  existing blogs need no edit; frank's migration sets `[base_character]`).
  Each named layer resolves through the same `resolve_layer` rules; the sheet
  prompt keeps its fixed frame (`SHEET_STYLE` … `SHEET_LAYOUT`) with the first
  configured layer rendered under the "CHARACTER — draw THIS character:" label
  and list layers under "HOLD ALL OF THESE CONSTANT" — so today's
  persona+visual_constants output is reproduced exactly by the default config.
  The `_gen_bytes` call passes `root` (D2).
- **`tools/validate_images.py`** (mirrored to `scripts/validate_images.py`):
  validates `prompt_for_images.yaml` against the config — unique keys;
  required fields (`key`, `output`, `prompt` unless `operator_generated`);
  every `references:` path exists; every dict layer's selector walk for every
  entry lands on prose or a declared skip (flags walks that dead-end on a
  non-scalar and int indexes out of range); `output` paths land under
  `site_dir` or `assets/`/`static/` trees. Wired as an opt-in `images` entry in
  `ci.validators` and run in the shipped blog CI when present. This replaces
  frank's orphaned `tests/image-pipeline/test_pipeline.py` (frank-side
  deletion happens in frank's migration, Test Plan A).
- **`extract-subject.swift`** ports from frank to
  `templates/hugo-hextra/scripts/extract-subject.swift` (framework class):
  Apple Vision subject isolation for building pool `subjects/*.png`. Guarded
  usage note (macOS-only; degrades with a clear error elsewhere), referenced
  from the pool README's curation workflow.

### D9 — Docs, versioning, CI

- CONFIG.md: v4 header, rewritten §4.1 (resolution table + standard entry
  fields + `_select`), `site_dir`, `image.character_sheet`, `validate_images`.
- `templates/manifest.yaml`: new framework paths (`scripts/blog_config.py`,
  `scripts/validate_images.py`, `scripts/extract-subject.swift`).
- CHANGELOG under one release; **single minor bump 0.8.0 → 0.9.0**
  (shipped-surface change; `tools/bump_version.py` lockstep; supersedes #40's
  0.8.1).
- Tests: unit coverage per phase (engine walk, migration, mapping, scaffolder,
  character sheet, validator) + updated `tests/unit/test_image_compose.py`
  fixtures proving frank/gondor byte-parity + smoke updates
  (`smoke-blog-post.sh` drops the stub-reference requirement; a new
  frank-shaped `site_dir` fixture exercises scaffold + update mapping).

## Test Plan

*Post-merge — operator-driven. Both plans follow snapshot → migrate → diff.*

### Plan A — frank (`derio-net/frank`, site_dir=blog, pool + dict layers)

1. **Snapshot (pre-migration):** from frank's root, for every key:
   `python blog/scripts/generate-images.py --print-prompt <key>` →
   `/tmp/frank-prompts-before/`; `--dry-run` output (payload listing) →
   `/tmp/frank-dryrun-before.txt`.
2. **Config ladder:** `python <blog-craft>/tools/migrate_config.py --config
   .blog-craft.yaml` (…→v4). Inspect: `torso` gained `_select`;
   `site_dir: blog` added by hand (adoption choice, not auto-derivable);
   `image.character_sheet.layers: [base_character]` set by hand.
3. **Machinery update (scoped):** `python <blog-craft>/tools/update.py
   --config .blog-craft.yaml --blog . --only 'scripts/**' --apply` — replaces
   the vendored `blog/scripts/{generate-images,compose}.py` and adds
   `blog_config.py`/`validate_images.py`/`extract-subject.swift`.
4. **Parity:** re-run step 1 → diff both snapshots. **Empty diff required**
   (byte-identical prompts, identical payload listings, including the
   multi-anchor `paper-04-cover`-style entries).
5. **Validator:** `python blog/scripts/validate_images.py --config
   .blog-craft.yaml` passes; delete the orphaned
   `tests/image-pipeline/test_pipeline.py` and the duplicated legacy
   `base_*`/`torso_variants:`/`moods:` prose in `blog/prompt_for_images.yaml`
   (now config-owned); re-run parity (step 4) once more.
6. **Live check (optional, one API call):** regenerate one cover with
   `--only`; visually compare.
7. Commit as frank PR; record `blog_craft_version: v0.9.0`.

### Plan B — gondor-blog (`derio-homelab/gondor-blog`, site_dir=., scalar/list layers)

1. **Snapshot:** `--print-prompt` for all keys → `/tmp/gondor-prompts-before/`.
2. **Config ladder:** v2 → v4 (002→003→004). Inspect: no `metaphor`/`image_gen`
   blocks exist, layers untouched, `version: 4`.
3. **Update:** `tools/update.py --config .blog-craft.yaml --blog . --apply`
   (identity path mapping). gondor has **no `blog_craft_version` pin**, so
   merged-class files (`hugo.toml`, `README.md`, …) that differ locally will
   surface as `conflict (no base to merge from)` — expected; resolve by
   inspection, or scope the run with `--only 'scripts/**'` (like frank) if only
   the image machinery should move. Framework replacements apply either way.
4. **Parity:** re-run snapshots → **empty diff**.
5. **Scaffold check:** run `/blog-post` end-to-end (test mode) — bundle lands
   in `content/docs/…`, entry is scene-only + selector-free (no dict layers),
   cover generates without a forced reference path.
6. Commit; record `blog_craft_version: v0.9.0`.

## Acceptance rows

Capability `image-composition` (origin: this spec):

| ID | Acceptance (business claim) | Level |
|---|---|---|
| IMG-COMP-1 | The engine composes any config-declared layer map — no hardcoded layer vocabulary; frank's and gondor's composed prompts reproduce byte-identically | unit (ci) |
| IMG-COMP-2 | `/blog-post` scaffolding honours the documented `image.*` config keys and `site_dir` — a frank-shaped blog can use it | unit+smoke (ci) |
| IMG-COMP-3 | A scaffolded prompt entry is scene-only with selector fields — the generator composes it without double-composition | unit (ci) |
| IMG-COMP-4 | An entry's `references:` anchors reach the model payload after the master sheet, verifiable via `--dry-run` | unit (ci) |
| IMG-COMP-5 | `/update` migrates an existing blog's image machinery in place, honouring `site_dir` and `--only` scoping | unit+smoke (ci) |
| IMG-COMP-6 | Config migration to v4 rewrites `metaphor.*`/`image_gen.*` and encodes `torso` selection as data, preserving composed output | unit (ci) |
| IMG-COMP-7 | Character-sheet generation draws its prose from config-declared layers — any persona vocabulary works | unit (ci) |
| IMG-COMP-8 | frank migrated via `/update` generates unchanged (Test Plan A parity) | manual (not-implemented until run) |
| IMG-COMP-9 | gondor-blog migrated via `/update` generates unchanged (Test Plan B parity) | manual (not-implemented until run) |
