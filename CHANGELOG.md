# Changelog

All notable changes to blog-craft are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and blog-craft adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The canonical version lives in `pyproject.toml`; `tools/bump_version.py` keeps
the plugin manifests in lockstep, and `.github/workflows/auto-tag.yml` cuts the
matching `vX.Y.Z` tag on merge (#18).

## [Unreleased]

## [0.14.0] - 2026-07-27

> **`site_dir` blogs: two files move on your next `/update`.** The CI workflow
> relocates from `<site_dir>/.github/workflows/blog-ci.yml` to
> `.github/workflows/blog-ci.yml`, and the hookify guard from
> `<site_dir>/.hookify.warn-hextra-weight-zero.md` to
> `.claude/hookify.warn-hextra-weight-zero.local.md`. Your edits move with them —
> the stale copy is the `local` side of the merge, so a `MERGE` line on a
> relocated path means your changes are being carried across. The dry-run names
> both sides; read it before applying. **Blogs whose site is the repo root** only
> see the hookify relocation. **After applying, expect gates that never ran to
> start running** — a workflow GitHub was never loading may have a backlog behind
> it.

### Fixed
- **`/update`'s documented invocation always failed (#59).** `python
  tools/update.py --config .blog-craft.yaml --blog .` — the form in the skill —
  raised a bare `CalledProcessError`. `bootstrap-render.sh` runs the Go renderer
  inside ten `( cd "$RENDERER_DIR" && … )` subshells, so a relative `--answers`
  or `--dst` was resolved against `tools/render-template/` rather than the
  caller's directory. Absolute paths worked, which is why it stayed latent: every
  successful run used one. Fixed where the `cd` is — the shell script absolutizes
  both arguments before anything cds, so every caller is fixed at once, including
  a human running the renderer by hand to diagnose it. The audit found four sites
  with this shape, not one: `reproduce.py`'s own `--config` and `--scratch` carry
  the identical break and were unreported. All are resolved at the library
  boundary as well as in argparse.
- **Renderer failures now say why (#59).** `reproduce.py` ran the renderer with
  `check=True, capture_output=True` and never surfaced the streams, so the
  operator got a stdlib traceback pointing at `subprocess.run` while the actual
  cause was one line the renderer had already printed. New `tools/proc.py` keeps
  the capture and attaches it to the exception; `CommandFailed` subclasses
  `CalledProcessError`, so existing handlers are unaffected. All four swallowing
  sites route through it — including `git archive <blog_craft_version>`, whose
  failure is precisely what the "keep `blog_craft_version` accurate" guardrail
  warns about.
- **`.github/**` was materialized under `site_dir`, where GitHub never reads it
  (#61).** For any blog whose Hugo site is not the repo root, the shipped CI file
  landed at `<site_dir>/.github/workflows/blog-ci.yml`. GitHub Actions loads
  workflows from `<repo>/.github/workflows/` and nowhere else, so that file was
  not a workflow — it was an inert YAML document that looked exactly like one.
  No error, no skipped run, no empty check, no entry in the Actions tab.
- **The hookify weight-zero guard had never loaded for *any* blog (#61).** It
  shipped as `.hookify.warn-hextra-weight-zero.md`; hookify globs
  `.claude/hookify.*.local.md` from the project root, so it matched neither the
  directory nor the filename — inert everywhere, not just on `site_dir` blogs.
  It now ships at `.claude/hookify.warn-hextra-weight-zero.local.md`, and its own
  `file_path` pattern carries the site prefix (hookify reports paths from the
  project root, so on a `site_dir` blog the pattern must be
  `<site_dir>/content/…`).
- **A relocated workflow could not have run even in the right place (#61).** The
  template invoked `--config .blog-craft.yaml` and `scripts/…` relative to the
  site root, while the config lives at the repo root. CI's working directory is
  the repository root, which is also the config root, so scripts and content
  globs now carry the site prefix; `--config` and `dossier_dir` do not (both are
  config-root-relative by contract), and the Hugo build gets a
  `working-directory`. A blog with no `site_dir` renders byte-identically —
  pinned by a test against the pre-#61 template across all three deploy kinds.

### Added
- **A declared path-ROOT model (#61).** `templates/manifest.yaml` gains a
  `roots:` section answering, per path, *who defines this path's location — the
  Hugo site, or a tool that reads it from the repository root?* The distinction
  is not "is it a dotfile": `.gitignore` is site-rooted (nested gitignores govern
  their own subtree), `.github/**` and `.claude/**` are not.
  `tests/unit/test_path_roots.py` requires exactly one root per materialized path
  across every `--src` root `bootstrap-render.sh` renders, so a new template file
  cannot merge without a reviewer answering the question. An undeclared path
  falls back to `site` at runtime — the pre-#61 behaviour — so a missed
  declaration is a failing test, never a broken blog.
- **`/update` relocates instead of re-adding dead files (#61).**
  `templates/manifest.yaml`'s `legacy_dests:` records where earlier releases put
  a path that has since moved; one table covers both migration axes (a root
  change *and* a rename). Without it, `plan_update` reads an absent managed path
  as `add` and re-creates the dead file on every run. New plan actions:
  `RELOCATE` (a move) and `PRUNE` (a stale duplicate under an already-correct
  destination). A conflict writes nothing and removes nothing — both copies stay
  and both are named, keeping the never-auto-resolve contract intact through a
  relocation.

## [0.13.1] - 2026-07-26

### Fixed
- **The glossary definition panel opens next to the term it defines (#49).** It
  was opening in the top-left corner of the viewport — 375px left and 299px above
  the abbreviation, on top of the page `<h1>`. The Popover API's top layer decides
  stacking, not coordinates, so a panel nobody positions takes the UA default and
  lands in the corner; `glossary.css` styled the panel but never placed it. The
  `{{< abbr >}}` shortcode now emits a unique `anchor-name` per trigger, derived
  from the panel id it already computes, with a matching `position-anchor` on the
  panel, and `glossary.css` anchors the panel below the term — flipping above it
  at the viewport foot and flipping its inline side at the edge. Browsers without
  CSS anchor positioning get a bottom-centred, viewport-clamped dock rather than
  the corner. Every unit test passed while the bug was live, because they assert
  structure and never position; `tests/unit/test_glossary_css.py` now pins the
  placement contract, and matrix row GL-9 books the part only a browser can check.

## [0.13.0] - 2026-07-26

### Added
- **Abbreviation glossary (`features.glossary`, opt-in).** A teaching blog leans
  on acronyms; the reader who does not know one has to leave the page. This
  feature lets them click instead. A blog-wide `data/glossary.yaml` registry
  holds `{name, description, url?}` per term; `{{< abbr "NUT" >}}` renders a
  click-to-open definition panel and `{{< glossary-index >}}` renders the whole
  registry alphabetically. **Zero JavaScript** — the trigger is a
  `<button popovertarget>` and the panel a `<span popover>`, so click/tap, Esc,
  click-away, keyboard focus and top-layer stacking are native browser
  behaviour. An optional second positional argument overrides the displayed text
  (`{{< abbr "SLO" "SLOs" >}}`) so plurals never fork a registry entry. No config
  schema bump — `features` passes through untouched, so an existing v5 blog opts
  in with two lines and an `/update`. See `docs/CONFIG.md` §9.
- **`/glossary` skill.** Scans one post, one series, or a whole blog, proposes a
  definition per abbreviation grounded in the sentence it was found in, shows the
  registry diff before writing, and marks the first occurrence of each term.
  Idempotent — a second sweep over an already-marked series changes nothing.
  Mirrored to OpenCode as `blog-craft-glossary`.
- **`tools/validate_glossary.py`** — the CI gate. Errors on a marker with no
  registry entry, an entry missing `name`/`description`, a relative `url`, or two
  keys differing only in case; warns on unused entries and an unsorted registry.
  Markers inside code fences are ignored, so a post documenting the shortcode is
  not gated on its own example. Ships at `scripts/` with its `glossary_scan.py`
  companion for plugin-free CI.

### Fixed
- **`test_explainers_hugo.py` was a time-of-day flake.** `scaffold-explainer.sh`
  stamps `date:` from the *local* date, but Hugo reads a bare date as midnight in
  the *site* timezone — so between local midnight and UTC midnight a freshly
  scaffolded post is future-dated and Hugo silently omits it while still exiting
  0. The test now stamps a post a day ahead (making the failure deterministic
  rather than clock-dependent) and passes `--buildFuture`.

## [0.10.0] - 2026-07-20

### Added
- **Config schema v5: composable composition (operator-directed refactor).**
  `image.composition_orders` is a NAMED map of orders (`hero`, `scenery`, ...);
  entries pick one via `composition.order` (a `composition_orders[name]`
  reference or an inline token list; absent -> `hero`). Order tokens gain the
  bracket form `layer[chunk]` (e.g. `reference_guidance[anchor]`), resolving a
  dict layer's named chunk directly. Entries move to a `composition:` block —
  `scene` (was `prompt`), `modifiers` (the selector fields; a value like
  `papers[white_lab_coat]` descends a nested table directly), and
  `reference_images` (`{primary, clothing: [...]}`), which is EXPLICIT: for v5
  entries the v4 precedence chain (config `reference_image` -> pool) never
  runs — what is declared is sent. Legacy v4 entries and configs keep working;
  one engine serves both. New `migrations/004_to_005.py` (config) and
  `tools/migrate_prompts.py` (entries, freezing the old precedence chain's
  pick into explicit `primary`). The scaffolder emits v5 entries.


## [0.9.0] - 2026-07-20

### Added
- **Generic `_select` layer walk (config schema v4).** The composition engine's
  last two hardcoded layer names — `torso` (series + variant index) and `mood`
  (named preset with free-form passthrough) — become config data: any map
  layer resolves through a declared `_select` walk (default: the layer's own
  name selects; free-form passthrough at the last step; intermediate misses
  skip). frank's rule ships as `_select: [[torso, series], torso_variant]`,
  written by `migrations/003_to_004.py`, and the parity fixtures' expected
  strings are untouched — byte-identical composed prompts, engine vocabulary
  zero (#39 / spec D1).
- **`site_dir` config key.** A blog may keep `.blog-craft.yaml` at the repo
  root with the Hugo site in a subdirectory (frank: `blog/`). `/blog-post`
  scaffolding and `/update` both honour it (#39 item 4).
- **`/update` path mapping + `--only` scoping.** Update destinations follow
  the blog's config (`site_dir`, `image.reference_pool`,
  `image.prompts_file`); `--only '<glob>'` scopes a run — migrating just the
  image machinery into an existing blog is now one command. Adoption of
  never-bootstrapped blogs documented in the update skill (spec D6).
- **Config-declared character sheets.** `gen-character-sheet.py` reads
  `image.character_sheet.layers` (default `[persona, visual_constants]`,
  byte-identical output; a frank-style blog sets `[base_character]`) instead
  of hardcoding layer names (spec D8).
- **`validate_images.py` image-entry gate.** Duplicate keys, missing fields,
  dead `references:` paths, escaping outputs, and selector walks that silently
  resolve to nothing now fail blog CI (unconditional step, mermaid-gate
  style). Replaces frank's orphaned image-pipeline suite (spec D8).
- **`extract-subject.swift`** (Apple Vision subject isolation, macOS-only)
  ships as a framework script for building `.reference-pool/*/subjects/`
  renders; workflow documented in the pool README.
- **`blog_config.py`** — dotted-path config reader for shell tooling, mirrored
  into blogs like the validators.

### Fixed
- **`blog-post-create.sh` ignored every documented `image.*` key (#39).** It
  now reads `site_dir`, `image.prompts_file`, `image.output_dir` from the
  config it already required; the appended entry is **scene-only** with
  selector fields (`--entry-field k=v`, ints stay ints) so the engine composes
  layers around it instead of double-composing; `--output` overrides the cover
  path; `--no-generate` creates bundle + entry without an API call so
  `--print-prompt` can preview first; and the hard requirement on
  `static/images/reference.png` (`exit 3`) is gone — the generator's own
  reference precedence decides.
- **An image entry's `references:` anchors never reached the model (#39
  item 5).** Absorbed from PR #40 (`entry_reference_paths()`, payload-order
  `--dry-run` listing, ordering + signature guards) — and fixed the second
  `_gen_bytes` caller PR #40 missed: `gen-character-sheet.py` now passes
  `root`, with an ast+inspect guard so the call sites can't drift again.
  Supersedes PR #40.
- **Skills spoke a dead vocabulary (#39 item 3).** `blog-post` Step 6
  hand-composed prompts from `metaphor.*` keys the shipped config never had
  (double-composing on layered blogs) and Step 7 read `image_gen.api_key_env`;
  `bootstrap-blog` collected `metaphor.*`/`image_gen.*` and wrote
  `metaphor.reference_image` while the generator reads
  `image.reference_image`. All skills now speak the shipped `image.*`
  contract, and `--print-prompt` is the single source of composed prompts.

## [0.8.0] - 2026-07-17

### Fixed
- **OpenCode mirror + uv.lock sync drift:** `scripts/install.sh` no longer
  leaves the working tree dirty on every run. The committed `.opencode/` skill
  mirrors were stale (broadsheet #22 and archetype-modes #35 never re-synced);
  they are now regenerated to match canonical `skills/`, and
  `tests/unit/test_opencode_sync.py` fails CI on any future mirror drift.
  `uv.lock` pinned the project at 0.4.0 while `pyproject.toml` had moved on
  (bumps never touched the lockfile); `tools/bump_version.py` now keeps
  `uv.lock`'s blog-craft `version` in lockstep (name-anchored — the line-1
  `version = 1` schema is never touched) and `--check` (the committed-repo
  self-consistency tripwire) now covers it.

## [0.7.0] - 2026-07-17

### Added
- **Explainer archetype modes:** `scaffold-explainer.sh --archetype <id>` now
  scaffolds all six explainer modes (`feature-deep-dive`, `skill-presentation`,
  `skill-comparison`, `testing-pyramid`, `deployment-strategy`,
  `security-posture`), each emitting that mode's section structure — previously
  five were guidance-only prose with no scaffold. `validate_explainers.py`
  gained a structural check: a post's `##` sections must match its declared
  archetype's recipe (every heading, in order; extra sections allowed), and an
  unknown archetype is rejected. Both scripts mirror into
  `templates/content-type-explainers/shared/scripts/`; docs updated in
  `skills/explainers/SKILL.md` and `references/archetypes.md`.

## [0.6.0] - 2026-07-16

### Added
- **Batch-rewrite changelog (#28):** `tools/assemble_changelog.py` assembles a
  per-post campaign changelog from per-post change entries — hoisting the items
  common to every post into a "Conventions Applied to Every Post" table
  (set-intersection, no manual dedup) and rendering the frank format. Documented
  in `skills/educational-writing/references/changelog.md` and wired as the
  end-of-campaign step in `post-rewrite`'s batch mode.

## [0.5.0] - 2026-07-16

The first release under controlled versioning — it also establishes the scheme
itself and folds in four features that had merged without a version bump.

### Added
- **Controlled versioning (#18):** `pyproject.toml` is the single canonical
  version; `tools/bump_version.py` syncs both `.claude-plugin` manifests;
  `tools/check_version_bump_needed.py` fails a PR that changes the shipped
  surface (`templates/`, `tools/`, `skills/`, `agents/`, `.claude-plugin/`)
  without a bump; `.github/workflows/auto-tag.yml` cuts `vX.Y.Z` + a Release on
  merge. Bootstrapped blogs now stamp a resolvable `blog_craft_version` tag.
- **Diagram quality gate (#25):** how-to / tutorial posts must carry a
  `mermaid` diagram (`gate.require_diagram`, on by default; `diagram_exempt`
  opt-out).
- **Batch / campaign post-rewrite mode (#26):** a documented small-batch,
  in-place, live-preview workflow plus the reproducible `scripts/batch-gate.sh`.
- **Broadsheet explainer style (#22):** a warm-dark editorial `--style`,
  `--embed-fonts` self-contained web-font embedding, per-style Mermaid theming,
  and `references/schematics.md`.
- **Build-time Mermaid syntax validator (#27):** `tools/validate_mermaid.py`
  lints `mermaid` fences (subgraph-targeting edges, bare `<br>`, unbalanced
  brackets) across all content types; on by default, opt out with
  `quality.mermaid_syntax: false`.

### Fixed
- Registered the `validate_educational.py` and (now) `validate_mermaid.py`
  tool↔template mirror pairs in the byte-identity guard (#25/#27).

[Unreleased]: https://github.com/derio-net/blog-craft/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/derio-net/blog-craft/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/derio-net/blog-craft/releases/tag/v0.5.0
