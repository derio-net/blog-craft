# Changelog

All notable changes to blog-craft are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and blog-craft adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The canonical version lives in `pyproject.toml`; `tools/bump_version.py` keeps
the plugin manifests in lockstep, and `.github/workflows/auto-tag.yml` cuts the
matching `vX.Y.Z` tag on merge (#18).

## [Unreleased]

## [0.19.0] - 2026-07-29

> **The mermaid width gate lands BLOCKING, with no baseline and no allowlist.**
> This is a deliberate operator decision, not an oversight: a baseline would let
> the backlog sit forever, so the gate is set to *"force a focused effort to fix
> them."* **Expect red CI on your first build after adopting this release** —
> measured against frank's live site, **35 of 203 diagrams** exceed the default
> 1400px budget. Three ways forward, in order of preference: fix the diagram
> (split it, shorten labels, `LR` → `TD`), waive that one diagram in its own
> source with `%% blog-craft: wide-ok — <reason>`, or raise/disable the budget
> with `quality.mermaid_max_width` (`0` disables — and says so loudly in the log).

### Added
- **Mermaid diagrams render at their authored size, in a framed scroller
  (`features.mermaid_view`, default on).** Mermaid's `useMaxWidth` shrinks every
  SVG to fit Hextra's content column, which is capped at **672px on every
  viewport** — a 2139px diagram rendered at **31% scale**, painting 14px labels
  at 4.4px. It was not a wide-screen problem: a 4K panel got the same 31% as a
  laptop. Diagrams now render full size inside a horizontally scrollable, framed
  block — the way a wide table behaves — with two independent scroll affordances,
  because one is not enough: a persistent scrollbar (macOS overlay scrollbars
  paint *nothing* at rest — measured `offsetHeight - clientHeight` 0 → 9px once
  `-webkit-appearance: none` is set) and self-cancelling scroll shadows that
  invert with the theme. The container is keyboard-focusable (`tabindex="0"` via
  a `render-codeblock-mermaid.html` override), since a scroller only a trackpad
  can reach fails WCAG 2.1 SC 2.1.1. Pure CSS, so it survives the dark/light
  re-render that resets `innerHTML`. Config surface goes to **schema v6**;
  `migrations/005_to_006.py` adopts existing blogs through `/update`, and
  `features.mermaid_view: false` restores the previous rendering. See
  `docs/CONFIG.md` §12.
- **A blocking diagram-width gate (`quality.mermaid_max_width`, default
  1400px).** Rendering at authored size makes a wide diagram legible; it does not
  make it *followable*. `scripts/validate_mermaid_layout.mjs` runs after `hugo`,
  measures every diagram in the **built** site with the site's **own** mermaid
  bundle, and fails CI on anything over budget, naming page, block index,
  measured width and overage. 1400 is ~2× the 672px column: more than two
  column-widths of scrolling cannot be held in the reader's head. It measures
  rather than guesses — width is read from the rendered SVG's inline
  `max-width`, the same value the stylesheet keys off, so gate and renderer
  cannot disagree. Zero npm dependencies: Node 22's global `WebSocket` drives
  preinstalled headless Chrome over CDP, so no `package.json`, no `npm install`,
  and no supply-chain surface is added to any adopting blog. Because it reads
  built HTML rather than markdown, it also catches shortcode-emitted diagrams
  that no markdown scan sees — which is where the original breakage actually was.
- **Width-first diagram guidance.** `skills/educational-writing` now defaults to
  `flowchart TD` and reserves `LR` for short, genuinely left-to-right pipelines,
  grounded in a render of all 182 markdown-fenced diagrams in one blog (median
  873px, p90 1622px, max 2394px against a 672px column). Stated as a strong
  default rather than a rule, because the data says direction *predicts* width
  without determining it: every sampled `LR` diagram overflowed (4/4), but one
  `TD` diagram still measured 1895px. No mechanical rewrite of existing diagrams
  — the gate reports, authors fix.

### Changed
- **A disabled diagram gate now says how far behind it is.** Previously
  `quality.mermaid_syntax: false` printed a neutral line and exited 0 —
  indistinguishable from a pass in an Actions log, which is how a 50-finding
  backlog shipped unreported. `validate_mermaid.py` now **always scans**, and
  when disabled prints `GATE DISABLED (quality.mermaid_syntax: false) — would
  report N finding(s) across M file(s) checked` plus every finding, still exiting
  0. The new width gate behaves the same way at `mermaid_max_width: 0`: it lists
  the diagrams it did *not* measure, and invokes no browser. **This is a visible
  behaviour change for any blog that had these gates switched off and saw a quiet
  pass** — the build still goes green, the log no longer pretends there is
  nothing there.

## [0.18.1] - 2026-07-28

### Fixed
- **The actionable-section check rejected the headings it exists to find.**
  `_ACTIONABLE` anchored its verbs as `\bverify\b` / `\brecover\b`, which cannot
  match the inflected forms writers actually use — so `## Verifying the
  Bootstrap` and `## Recovery Path` both failed the gate, as did `## The Smoke
  Test`, `## Troubleshooting` and `## Diagnosis`. The unit test hid it by only
  ever passing the bare imperative ("Verify", "Recover"), the one form headings
  rarely take. Measured on a real 83-post blog: 34 posts failed the gate and
  **27 already carried such a heading** — so acting on the validator's output
  would have meant renaming good prose to satisfy a regex. Verb stems
  (`verif\w*`, `recover\w*`) now replace the anchors, and `troubleshoot\w*`,
  `diagnos\w*` and `smoke test` join the vocabulary. Deliberately not widened
  further: `\bsteps\b` stays anchored so "Missteps" is not a hit, and
  `test_narrative_headings_still_do_not_count_as_actionable` pins that
  Background / Architecture / Data Flow keep failing — a matcher that accepts
  everything is as useless as one that accepts nothing, and the repo-wide
  assertion looks identical either way.

## [0.18.0] - 2026-07-28

### Added
- **Reader-arc methodology — landscape beginning, what-transfers ending.**
  `skills/educational-writing` gains `references/reader-arc.md`: the post is
  organized around the reader's arc, not the work's chronology. Building and
  tutorial posts open with a conceptual lay-of-the-land sized to the material
  (a paragraph for a small tool, a section for a new domain) and close with a
  what-transfers section — what the reader takes to their *next* project, not a
  summary of this one. The drafting SKILL.md carve-out, session skeleton, and
  review checklist all wire it in, and the contract is CI-pinned
  (`tests/unit/test_reader_arc_contract.py`).
- **Vendored AI-tells catalog + warnings-first lint layer in the educational
  gate.** `references/ai-tells.md` catalogs the tells with machine-readable
  lint data, and `validate_educational.py` grows a lint layer on top of the
  structural gate: AI-vocabulary hits **fail** by default; em-dash density,
  parallelism runs, rule-of-three pileups, cliché conclusions, and a missing
  what-transfers section **warn**. Severities (`fail|warn|off`) and thresholds
  are configurable via the new `quality.lint` config block (`docs/CONFIG.md`).
  Code fences and frontmatter are excluded from scanning. The catalog ships
  into consumer blogs as a `scripts/` sibling mirror of the validator; a blog
  whose `scripts/` predates it prints a loud `LINT SKIPPED` and stays
  gate-only — never a crash, never a silent skip.
- **Blind cold-reader editor pass in `/blog-post` and `/post-rewrite`.**
  `agents/cold-reader.md` — a read-only agent (Read, Grep, Glob) dispatched
  with *no session context* — critiques every draft as a first-time reader
  across five sections (Takeaway mirror, Lost points, Session residue, Arc
  assessment, AI-tell instances), and
  the draft is revised against the critique before the operator ever sees it.
  Both drafting skills carry the dispatch sub-step ahead of the approval
  question (`tests/unit/test_cold_reader_contract.py`).
- **Dotted-key config seeding.** `seed_config.py` now seeds nested keys:
  `quality.lint.enabled` creates the real nested `quality:` block the validator
  reads (boolean value, comment attached, partially-existing blocks extended in
  place) instead of a dead flat string key. Existing values stay byte-for-byte
  untouched, and `/blog-post` Step 0 seeds the flag on first run in a consumer
  blog (`tests/unit/test_seed_config.py`).

## [0.17.0] - 2026-07-27

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
- **A renamed papers series validates.** `validate_paper` has taken a
  `papers_key` since it was written, but the CLI never passed it — so the series
  check always compared against the literal `"papers"`. On a blog with
  `series: [{key: essays, content_type: papers}]`, `scaffold-paper.sh` writes
  `series: [essays]` into every bundle it creates, and the validator then failed
  each paper on the one field the tool itself had written. The CLI now derives
  the key exactly as the scaffolder does. Caught in review: the first version of
  the papers-glob fix below asserted only the rendered glob *string*, so the test
  passed while the capability it named was false.
- **The CI papers step no longer fails on every non-papers post.** It globbed
  `content/docs/*/*/index.md` and handed the lot to `validate_papers`, which
  validates each file it is given and ERRORS on a post whose `series` lacks the
  papers key — it does not skip. So the step could only pass on a blog whose
  *only* series was papers. It now globs the papers SECTION,
  `content/docs/<key>/`, with the key read from `series[].content_type ==
  "papers"` (default `papers`) — the same derivation `scaffold-paper.sh` uses to
  place a bundle, so a blog that renamed the series is still gated. Selecting by
  path rather than skipping by frontmatter is deliberate: a paper carrying the
  WRONG series still sits in the papers directory, so it is still validated, and
  the series check is exactly what catches it. Latent until now — #61 is what
  makes this file execute for the first time on a `site_dir` blog.
- **The glossary no longer marks abbreviations inside diagram source.**
  `{{< papers/landscape >}}` wraps its `.Inner` in `<pre class="mermaid">` under
  a `quadrantChart` header, but the scanner's exclusions covered the shortcode
  TAG and not its BODY — so `x-axis OSS --> Commercial` read as prose. The
  marker expanded to a `<button popovertarget>` tree inside a chart axis and
  mermaid died with `Lexical error on line 4. Unrecognized text.`. On a real
  blog a full sweep put four of these across four papers, and the only thing
  that objected was a validator running over the RENDERED output, whose error
  names a lexer position and nothing that points back at a glossary sweep.

  The criterion is *the body is renderer source*, not *the shortcode has a
  body*: `papers/pullquote` and `papers/scar` also take `.Inner` and it is
  ordinary prose that must stay markable, so excluding every shortcode body
  would silently drop legitimate markers. Audited across every shipped
  shortcode — `landscape` is the only one that qualifies.

  Two halves, because the applier is idempotent and so never removes what it
  would no longer add: `excluded_spans` stops new markers, and a new
  **placement error** in `validate_glossary` reports the ones an earlier sweep
  already wrote. The key can be perfectly valid and the marker still fatal, so
  existence checks alone cannot catch it.

  Both body detection and the placement report subtract `code_spans`, so a post
  that *documents* the shortcode inside a fence is not failed by its own example
  — the invariant `markers_in` already honoured, and the one thing that must not
  drift between the two marker views. The opening tag and the body are each
  tempered against their own delimiters: without that, backtracking lets an
  opener quoted in inline code reach the NEXT block's `>}}` and report that
  block's body as its own, un-marking every paragraph in between — an
  over-broad exclusion is the failure this feature must not have. The `{{% %}}`
  form is covered too.

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
## [0.16.2] - 2026-07-27

### Documentation
- **The backfill warning is documented where operators meet it (#60).** 0.16.1
  shipped the check that names the `merged` paths a fallback base may have
  frozen, but only the CHANGELOG described it — an operator-facing warning with
  no entry in the skill or the config contract. `skills/update/SKILL.md` now
  explains what the backfilling run is telling you and how to act on it (diff
  each named path against a fresh render; a difference is shipped content an
  earlier run dropped), and `docs/CONFIG.md` §11 carries the short form. The
  archived spec gains a "Shipped beyond this spec" section recording the design
  it did not anticipate: the spec treats the fallback purely as a forward
  compatibility path, and misses that recording the first snapshot also freezes
  whatever the tree already holds.
- **Acceptance row UB-5** books the behaviour, which shipped with tests but no
  matrix row — the backfill the repo's acceptance rule owes on any PR that ships
  a capability.
- Plan and spec for #60 archived to `docs/superpowers/implemented/`; the UB-1…5
  origin refs follow them.

## [0.16.1] - 2026-07-27

### Fixed
- **Enabling a `features.*` flag no longer silently drops its contribution to
  merged files (#60).** `/update` recovered the 3-way base by re-rendering the
  templates at the recorded `blog_craft_version` — but fed them the config the
  operator had *just* edited. The base therefore already contained the new
  feature while the on-disk file did not, so `diff3` read the file as a
  deliberate deletion and kept the deletion. Enabling `features.glossary` on a
  synced blog added `abbr.html`, `glossary-index.html` and `glossary.css` but
  never the `Validate glossary` CI step, under a printed `MERGE` and an `update
  applied` — five of six planned paths landing is what made it read as success.
  Not glossary-specific: a changed `site_dir`, palette or series list had the
  identical shape, and every `merged` path was exposed — `hugo.toml`,
  `assets/css/**`, `.github/**`, `README.md`. The base is now
  `render(config_at_last_sync, templates_at_recorded_version)` in both halves,
  the first coming from a new sync snapshot. Documented as `docs/CONFIG.md` §11.

### Added
- **`.blog-craft.sync.yaml` — the sync snapshot.** The config, verbatim, as of
  the last successful sync; written by `bootstrap-render.sh` and by every
  conflict-free, unscoped `update.py --apply`, and classified `content` so the
  update flow never touches it. One small YAML file, not a rendered baseline tree
  (spec §8.2). Blogs synced before it existed keep working: `/update` warns that
  its base is approximate and backfills the snapshot, so the run after that is
  exact. **Commit the file** — an untracked snapshot is lost on the next clone.
- **`NOOP` as a distinct update outcome.** A 3-way merge that resolves entirely
  in the blog's favour writes nothing; reported as `MERGE` it was
  indistinguishable from one that shipped something, which is what kept #60
  invisible for a release. A `NOOP` on a path you expected to change is now the
  visible fingerprint of a wrong base. The dry-run also prints a per-action
  tally.
- **The backfilling run names what it may have frozen.** Recording the first
  snapshot fixes every future update, but it also baselines whatever the tree
  currently holds — including a change an earlier, pre-#60 run already dropped.
  From the run after that, such a path is an ordinary `NOOP` with no warning on
  it: the snapshot asserts "synced to this config" over a tree that does not
  match, and the tool stops disagreeing. So the one run that can still tell you
  now does, listing by mapped destination every `merged` path its fallback base
  resolved to `NOOP`, with how to diff them against a fresh render. Silent on a
  snapshot-backed run, and silent when the fallback decided nothing — a warning
  that fires on clean plans is one operators learn to skip.

## [0.16.0] - 2026-07-27

### Added
- **`features.mermaid_csp_init` — mermaid survives a strict CSP (#58).** The
  third instance of the failure class 0.15.0 fixed twice, and the one that got
  away: the Hextra theme initialises mermaid from an inline `<script>`, which
  `script-src 'self'` drops. `mermaid.js` self-starts, so diagrams still
  *appear* — always in the light theme, no longer following the dark/light
  toggle, with no build error and nothing in the console. Enabling the feature
  materializes `assets/js/mermaid-init.js`, which re-implements the theme's two
  behaviours (source capture + `MutationObserver` re-render) from an external
  asset; the theme's block stays in the markup, inert.

  **Opt-in, unlike the 0.15.0 fixes, and the asymmetry is the point.** Those
  replaced inline scripts blog-craft *itself* emitted, so nothing was left to
  collide with. This one supersedes a script inside the **pinned theme**, which
  blog-craft cannot remove — on a site with no CSP that block still runs, and
  shipping ours unconditionally would give every such site two
  `mermaid.initialize()` calls and two MutationObservers racing the same nodes.
  The flag therefore tracks a fact about the deployment, not a preference.
  Documented as `docs/CONFIG.md` §10.

- **`tests/unit/test_mermaid_csp_init.py`** — the guard, and the reason this bug
  outlived #56. `test_templates_csp_safe.py` asserts a *built* page carries no
  inline `<script>`, but its fixture post contains no diagram, so the theme never
  loads its mermaid partial and that assertion passed **vacuously** against this
  failure. The new guard builds a page that actually uses mermaid and pins both
  directions (flag on ⇒ external, deferred, same-origin `mermaid-init` in the
  output; flag off ⇒ asset never materialized, nothing referenced). It also
  asserts the theme *still* emits the inline init being superseded — keyed on
  `dataset.original`, a load-bearing substring rather than a cosmetic one — so a
  theme bump that fixes this upstream fails loudly and says to retire the flag,
  instead of silently leaving two initialisers behind. Deliberately does **not**
  assert "no inline script" on a mermaid page: there is one, blog-craft does not
  own it, and the guarantee that matters is that a working external superseder
  ships alongside it.

## [0.15.0] - 2026-07-26

### Fixed
- **Two templates emitted an inline `<script>`, which a CSP silently drops
  (#56).** `script-src 'self'` without `'unsafe-inline'` is the ordinary
  hardening posture for a public blog, and it drops inline blocks with no build
  error and nothing in the console an author would think to look for — the
  feature simply renders and does nothing. The read-tracker's "Clear read
  history" link cleared nothing, and `{{< asciinema >}}` never started a player.
  Both now behave through external assets, with per-instance configuration
  travelling as `data-*` attributes. The read-tracker feature already shipped its
  main logic as an external asset, so these were the two call sites that missed
  an established pattern — structurally the same as `resize` vs
  `crop_resize`/`ico` in #53.

### Added
- **`assets/js/asciinema-init.js`** — reads the shortcode's `data-*` attributes
  and bootstraps the player. Loaded (deferred, after the player library) only on
  pages that use the shortcode, matching how `read-tracker.js` is wired.
- **`.clear-read-history` in `custom.css`** — replaces the inline `style`
  attribute on the footer link, so that partial emits no inline markup at all.
- **`tests/unit/test_templates_csp_safe.py`** — the guard. Fails on any inline
  `<script>` in an HTML-emitting template, ignoring prose inside Go-template and
  HTML comments (a note explaining why a handler moved out of a `<script>` is not
  an offence — this fired on its own first draft) and skipping `.js.tmpl` /
  `.css.tmpl`, which are not markup. Carries a detector self-test pinning both
  match directions so the guard cannot go vacuous, plus a Hugo build asserting
  the wiring survives in the OUTPUT — external scripts loaded, `data-*` present,
  zero inline blocks. Inline `style=` is deliberately out of scope: `abbr.html`
  needs a unique `anchor-name` per trigger and `screenshot.html` a per-invocation
  `max-width`, and `style-src` is commonly left permissive where `script-src` is
  not.

- **asciinema-player is vendored and served same-origin (#56).** `head-end.html`
  loaded both the player script and its stylesheet from `unpkg.com`, which was
  wrong three ways at once: a `script-src 'self'` CSP blocks it outright (so
  fixing the inline `<script>` above would have left the feature broken anyway),
  the tags carried no Subresource Integrity so a substituted CDN response would
  have executed unchecked, and a CDN outage took the feature down with it.
  Serving from the blog's own origin resolves all three — which is why there is
  still no `integrity=` attribute: pinning a hash to a URL the CSP rejects would
  have been motion without progress. Apache-2.0, with `LICENSE` and a
  `PROVENANCE.md` recording version, sha256s and the update procedure. Hugo
  publishes an `assets/` resource only when a template retrieves it and both are
  gated behind `.HasShortcode "asciinema"`, so a blog that never uses the
  shortcode carries the files in its repo and ships **zero bytes** of them to
  readers. New `assets/vendor/**` manifest rule (framework) — deliberately not
  under `assets/css/**`, which is `merged`, because 3-way-merging a minified
  upstream bundle is meaningless.
- **`0.14.1` had no CHANGELOG entry** — added retroactively above, and
  `tests/unit/test_changelog.py` now makes the omission impossible: the version
  in `pyproject.toml` must have a matching section, released sections must be
  ordered newest-first, and `[Unreleased]` must survive. Two gates already gate
  the version (`bump_version.py --check`, `check_version_bump_needed.py`) and
  nothing gated the record of what changed.

## [0.14.1] - 2026-07-26

### Fixed
- **`srcset` could make the full-resolution image unreachable (#55).**
  `opt-image.html` built its candidate list from `slice 480 960 $maxW` and then
  clamped each candidate with `le $w $srcW` — comparing the cap against itself
  rather than against the primary actually emitted. Whenever the source was
  **narrower than the cap**, that top candidate failed the clamp and was dropped,
  leaving nothing in the srcset matching the primary. That is not a missing size:
  per the HTML spec, once a `srcset` carries `w` descriptors the `src` attribute
  stops being a selection candidate, so the full-resolution derivative
  `opt-image` had just generated became **unreachable** and the browser upscaled
  the largest survivor. With no `sizes` attribute it also assumes `100vw`, which
  makes the upscale deterministic rather than occasional, and every derivative
  still returns 200 so nothing fails server-side. Measured downstream on frank
  (derio-net/frank#710): banners at 2169w under a 2560 cap and covers at 1424w
  under a 1600 cap both emitted `480w, 960w` only — 179 affected images, a 2.0×
  upscale on a DPR-2 viewport. The top candidate now comes from `$primary.Width`
  and reuses the primary resource rather than re-`Resize`-ing to its own width
  (which would emit a byte-identical second file under a different hash). The
  existing tests all fed a source *larger* than the cap, where the cap and the
  primary width coincide and the defect cannot appear.

  *(Entry added retroactively in #57 — 0.14.1 shipped without one. Nothing
  enforced a CHANGELOG section at the time; `tests/unit/test_changelog.py` now
  does.)*

## [0.14.0] - 2026-07-26

### Fixed
- **Post covers went out unoptimized (#53).** `docs/single.html` rendered the
  cover as a raw `<img>` while every other image path — `list.html` (the cover
  *thumbnail*), `render-image.html`, `screenshot.html`, `site-banner.html` —
  went through `opt-image.html`. So the largest image on the page was the one
  image skipping WebP conversion, `maxWidth` capping and `srcset`: a retina
  display got no high-DPI variant and a phone downloaded the full-size asset.
  The partial and `[params.imageOptimize]` were both already shipped and
  enabled; only this call site was missed. `test_image_optimize.py` never caught
  it because its fixture leaves the papers content-type off, so the layout
  carrying the cover was never materialized in the test blog — the test now
  enables it, drops a `cover.png`, and asserts the cover is capped WebP with a
  srcset.
- **`.reference-pool/README.md` documented the v4 chain v5 removed (#53).** It
  described reference selection as a three-tier precedence chain that "stacks",
  which `docs/CONFIG.md` has said does not run for a v5 entry since 0.10.0. A
  blog bootstrapped today got a README contradicting its own engine. Rewritten
  to the v5 contract (exactly one `primary`, `clothing:` anchors, order is
  load-bearing), with the v4 chain kept as an explicit legacy note.

### Added
- **`resize` accepts `target` and `size` (#53).** Of `post_process()`'s three
  steps, `crop_resize` and `ico` already wrote to a `target` and `ico` already
  took `size` as a square shorthand — `resize` alone always clobbered the source
  image. That made a one-master-to-many-derivatives pass inexpressible, because
  each `resize` destroyed the source the next step had to read; the canonical
  favicon set (crop square, then fan out to apple-touch/32/16/ico) could not be
  written. `resize` now honours both, strictly backwards compatibly: with
  `width`/`height` and no `target`, behaviour is unchanged. `post_process()` had
  no test coverage at all, which is how the three steps drifted apart —
  `tests/unit/test_post_process_steps.py` now pins the shared contract.

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
