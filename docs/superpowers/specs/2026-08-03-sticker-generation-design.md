# Sticker generation — port frank's private sticker set into blog-craft

- **Date:** 2026-08-03
- **Status:** design (brainstormed, not yet planned)
- **Repo:** blog-craft (consumer migration: frank)
- **Branch:** `feat/stickers`

## Problem

frank carries a die-cut sticker generator that blog-craft does not have. It
lives at `frank/blog/_private/frank-stickers/` and is four files:

| file | lines | role |
|---|---|---|
| `stickers.yaml` | 217 | shared style prose + 18 stickers, each with `sheet`/`pos` |
| `generate-stickers.py` | 151 | Gemini image generation, one sticker at a time |
| `build-sheets.py` | 59 | composes two print-ready 300-DPI A4 sheets (3×3 each) |
| `README.md` | 47 | the operator runbook |

`generate-stickers.py:5` describes itself as mirroring "the blog's
generate-all-images.py" — the very script blog-craft already absorbed and
generalized. So frank now runs two prompt-composition engines: the shared one
for covers, and a private fork for stickers. The fork has already drifted (see
§2), and every future engine improvement lands on one side only.

The operator's ask: port it into blog-craft as a first-class capability, and on
frank's next `/update` have frank **delete its own implementation and adopt
blog-craft's, with no behavioral changes**.

## Findings (evidence, 2026-08-03)

### What ports for free

- **The concatenation rule is already identical.** `compose()` joins non-empty
  sections with a blank line and its docstring states it is "byte-compatible
  with frank's generate-all-images.py" (`tools/compose.py:7,123`). frank's
  sticker script uses the same `"\n\n".join` (`generate-stickers.py:49-54`).
  The only difference is that frank's sticker join does not filter empties —
  immaterial, because all eight sticker sections are non-empty for all 18
  stickers.
- **Reference ordering maps exactly.** `primary_reference()` is documented as
  "the FIRST payload image" and `entry_reference_paths()` appends the rest "in
  declared order" (`templates/hugo-hextra/scripts/generate-images.py:196-254`).
  frank's sticker order — `canon_face`, then two `style_anchors`, then the
  clothing subject — is expressible as v5
  `reference_images: {primary, clothing: [...]}` with no engine change.
- **Per-entry `aspect_ratio` already exists** (`generate-images.py:260-266`),
  covering frank's `defaults.aspect_ratio: '1:1'`.
- **Shipped scripts already classify correctly.** `manifest.yaml`'s
  `framework: scripts/**` row says it "covers every shipped script … no
  per-file rows needed", and `roots.site: scripts/**` lands them at
  `<site_dir>/scripts/`. New sticker scripts inherit both.
- **`/update` can already delete frank's files.** `manifest.legacy_dests` maps
  a currently-shipped path to the destinations earlier releases used;
  `plan_update` emits `relocate`/`prune`, and `apply_plan` does
  `legacy.unlink()` + `_prune_empty_parents()` (`tools/update.py:105-119,
  186, 325-338`). Paths absent from the table are inert, so gondor and stoa
  are unaffected.

### What does not port — five real divergences

1. **The mood frame has no expression in config.** frank's stickers wrap a
   per-entry free-form mood in a code template,
   `f"Frank's expression: {s['mood']}."` (`generate-stickers.py:53`).
   blog-craft's `_resolve_modifier` passthrough returns the raw value with no
   wrapper (`compose.py:87`), so the prefix and trailing period are lost.
   Note the sticker frame is `expression:` while frank's *cover* mood table
   bakes `expression is` (`frank/.blog-craft.yaml:154-167`) — they are
   different strings, and two stickers keyed "satisfied" carry different mood
   text, so a shared table cannot serve stickers.

2. **Sticker and cover `base_character` directly contradict each other.**
   Covers say "Messy black flat-top hair with jagged spiky peaks"
   (`frank/.blog-craft.yaml:91`). Stickers say the head is "slightly ROUNDED
   and softened — NOT a hard blocky / square flat-top Frankenstein head" and
   the hair is "DARK (dark charcoal, near-black) … NOT green or olive"
   (`stickers.yaml:16`). These cannot share the layer name `base_character`.
   Sticker layers must be separately named. This is a hard constraint, not a
   preference.

3. **The engine is destructive; frank's sticker workflow is not.** frank's
   generator writes only to `regen/` and never touches
   `images/sticker-<key>.png`; the README's workflow is "pick a winner from
   `regen/` … copy it over" (`README.md:28-29`). blog-craft's generator writes
   the last variant straight to the entry's `output:` path
   (`generate-images.py:351`). Porting stickers as ordinary entries would
   **overwrite the curated sticker master on every regeneration** — silent
   loss of the hand-picked artwork the print workflow exists to protect. This
   is the highest-severity finding in this design.

4. **No model fallback, no HTTP timeout.** frank's sticker script retries
   `gemini-3-pro-image-preview` → `gemini-2.5-flash-image` on any exception
   and caps HTTP at 120 s (`generate-stickers.py:37-39,123`). `_gen_bytes`
   does neither. Dropping them changes behavior on the failure path — and the
   fallback exists precisely because the primary is a *preview* model.

5. **No print/DPI-aware layout code anywhere in blog-craft.** `_contact_sheet`
   is a screen-resolution review grid with hardcoded `cols = min(len, 3)` and
   `400×260` tiles (`generate-images.py:146-159`). frank's `build-sheets.py`
   is a different thing: 2480×3508 at exactly 300 DPI, a centered 3×3 grid,
   `dpi=(300,300)` written into the PNG so printing at 100% maps A4 1:1 and
   the `#1b4332` keyline stays a literal cut path. This is the only genuinely
   new code in the port. frank's *regen* contact sheet also uses different
   geometry (`cols=5, tile_width=420`) via frank's own `scripts/lib/`.

## Goal

One prompt-composition engine. frank's sticker set generates byte-identical
prompts and pixel-identical sheets through blog-craft's shipped code, with the
capability available (off by default) to any blog-craft blog. frank's four
private files are gone after its next `/update`.

## Non-goals

- No published sticker surface — no Hugo page, shortcode, gallery, or CSS.
  frank's set is a private print asset and stays one (operator decision, §
  Decisions). This keeps CSP review, image optimization, and layout entirely
  out of scope.
- No new sticker *content*. The 18 stickers, their prose, and the two sheets
  are frank's content and move verbatim.
- No change to cover generation for any blog. Every change is additive and
  gated; existing composed prompts must not shift by one byte.

## Decisions (operator, 2026-08-03)

1. **Mood frame → add `_template` to `compose.py`.** A dict layer may declare
   `_template: "Frank's expression: {}."`, applied to the resolved or
   passed-through value. Underscore keys are already reserved as directives
   never rendered as prose (`compose.py:24,85`), so this is backward
   compatible. Chosen over baking the prefix into all 18 entries because it
   keeps the frame structural: a 19th sticker cannot silently omit it.
2. **Port both reliability knobs** as `image.fallback_model` and
   `image.timeout_ms`, honored by every `generate-images.py` run.
3. **Private print asset, config-gated** — `features.stickers.enabled`,
   default `false`; output stays in an unpublished path.
4. **Dedicated prompts file** — `features.stickers.prompts_file`, separate
   from `image.prompts_file`, keeping `sheet`/`pos` out of cover entries and
   the 18 sticker keys out of the 88-key cover namespace.

Two further decisions taken during design, flagged for review:

5. **Add `--out <dir>` to `generate-images.py`** (non-destructive mode): when
   given, images land at `<dir>/<key>.png` and the entry's `output:` is never
   written. This is what makes finding 3 safe, and it generalizes usefully to
   covers ("preview without clobbering the shipped one").
6. **Parameterize `_contact_sheet(images, out, cols=None, tile_width=400)`**
   so frank's regen contact sheet keeps its `cols=5, tile_width=420`
   geometry instead of silently reflowing to 3 columns.

> **Decision 6 is necessary but not sufficient** (found during phase 2
> implementation, 2026-08-03). The two contact sheets are different artifacts,
> not the same artifact at different sizes:
>
> | | blog-craft engine | frank's sticker script |
> |---|---|---|
> | scope | one sheet per **key**, across that key's variants | one sheet per **run**, across the keys generated |
> | path | `.regen-archive/<key>/contact-sheet.png` | `<out>/contact-sheet.png` |
> | trigger | only when `--count > 1` | whenever ≥2 keys succeeded (`generate-stickers.py:141-144`) |
>
> frank generates **one image per key**, so `count == 1` and the engine's sheet
> is never produced at all — geometry parameters alone cannot bridge that.
> Phase 4's `generate-stickers.py` shim therefore builds the run-level sheet
> itself, calling `_contact_sheet(..., cols=5, tile_width=420)` over the keys it
> generated. The engine keeps its per-key sheet unchanged; the shim owns
> frank's workflow semantics, which is the right split.

## Architecture

### 1. Config surface

```yaml
image:
  model: gemini-3-pro-image-preview
  fallback_model: gemini-2.5-flash-image   # NEW — retry target on any exception
  timeout_ms: 120000                       # NEW — HttpOptions timeout
  composition_orders:
    sticker:                               # NEW — frank's fixed 8-token order,
      - sticker_base_character             # transcribed from
      - sticker_atmosphere                 # generate-stickers.py:49-54
      - sticker_reference_guidance
      - sticker_face_pins
      - clothing
      - sticker_mood
      - scene
      - sticker_border_spec                # NOTE: after scene, not before
  layers:
    sticker_mood:                          # NEW — sticker-only, NOT frank's `mood`
      _template: "Frank's expression: {}."   # (see the warning below)
    sticker_base_character: |- ...
    sticker_atmosphere: |- ...
    sticker_reference_guidance: |- ...
    sticker_face_pins: |- ...
    sticker_border_spec: |- ...

features:
  stickers:
    enabled: false                                    # default OFF
    prompts_file: blog/_private/stickers/stickers.yaml
    images_dir: blog/_private/stickers/images
    sheets_dir: blog/_private/stickers/sheets
    sheet: { size: a4, dpi: 300, grid: [3, 3], gutter: 60 }
```

Two notes on this shape.

`clothing` and `scene` are **reused** from frank's existing cover layers —
frank's sticker `clothing` is per-entry free-form prose, which passthrough
already handles, and `scene` is the reserved token. **`mood` is not reusable**,
and an earlier draft of this spec got that wrong. Six layers are namespaced,
not five.

> **Why `sticker_mood` and not `mood`** (found during phase 1 implementation,
> 2026-08-03). `_template` attaches to a *layer*, so it applies to every order
> naming that layer. frank's `mood` table is already a flat map of **complete
> sentences** — `curious: Frank's expression is curious — head tilted…`
> (`frank/.blog-craft.yaml:154-167`) — and frank's `hero` (line 57) and
> `banner` (line 77) orders both name plain `mood`. Putting `_template` on
> `mood` would therefore compose
> `Frank's expression: Frank's expression is curious — …` on **every frank
> cover**. Nothing in blog-craft would catch it: the sticker goldens only cover
> sticker prompts, and `test_image_compose.py` uses its own `_template`-free
> fixture. A separate `sticker_mood` layer keeps the frame where it belongs.
>
> Consequence for entries: `_resolve_modifier` looks up `entry.get(<layer
> name>)`, so sticker entries carry `modifiers: {sticker_mood: <free-form
> text>}` — not `mood`.

The order above is authoritative, transcribed from
`generate-stickers.py:49-54`:

```python
return "\n\n".join([
    cfg["base_character"], cfg["sticker_atmosphere"],
    cfg["reference_guidance"], cfg["face_pins"],
    s["clothing"], f"Frank's expression: {s['mood']}.",
    s["scene"], cfg["border_spec"],
])
```

`border_spec` trailing `scene` is the one counter-intuitive element — the
sticker finish is described *after* the scene it frames. Reordering those two
would produce a plausible-looking prompt that is not frank's.

### 2. `compose.py` — the `_template` directive

`_resolve_modifier` and `_resolve_selector_walk` both currently return either
a table hit or a free-form passthrough. Both gain a single post-step: if the
layer table declares `_template`, format the resolved string into it. A layer
that resolves to `""` stays `""` (an empty section is dropped by `compose`, and
templating an absent mood into `"Frank's expression: ."` would be a bug).

`{}` is the substitution point — `str.format` with a positional field, not an
f-string, so prose containing braces is not a hazard beyond ordinary
`format` escaping. Prose with literal `{`/`}` is a known sharp edge; the
validator should reject a `_template` without exactly one `{}`.

### 3. Feature module — `templates/features/stickers/`

Following the established `templates/features/<name>/` pattern (analytics,
glossary, mermaid-csp, mermaid-view, read-tracker), gated in
`tools/bootstrap-render.sh` on `features.stickers.enabled` exactly as
`features.glossary.enabled` is (`bootstrap-render.sh:118-123`).

Unlike every existing feature module, this one ships **no Hugo assets** —
only scripts:

```
templates/features/stickers/scripts/build-sheets.py
templates/features/stickers/scripts/generate-stickers.py
```

Both land at `<site_dir>/scripts/` and are classified `framework` by the
existing `scripts/**` manifest rows — no manifest class changes needed.

### 4. `generate-stickers.py` — a thin CLI-preserving shim

frank's README documents `--list`, `--only <keys>`, `--out <dir>`,
`--dry-run`. Preserving that CLI is part of "no behavioral changes": the
operator's runbook and muscle memory stay valid. The shim resolves
`features.stickers.prompts_file` and delegates to the shared engine:

| frank's flag | delegates to |
|---|---|
| `--list` | `generate-images.py --list` over the stickers prompts file |
| `--only k1,k2` | `--only k1,k2` |
| `--dry-run` | `--print-prompt` per key (prompt + resolved refs, no API call) |
| `--out regen` *(default)* | `--out regen` — the new non-destructive mode (§5) |

The default being `--out regen` rather than "write to `output:`" is the
load-bearing detail: it is what keeps finding 3 from becoming data loss.

### 5. `build-sheets.py` — the only new code

A near-verbatim port of frank's 59 lines, with the hardcoded constants read
from `features.stickers.sheet` and the three hardcoded paths read from
`features.stickers.{prompts_file, images_dir, sheets_dir}`.

**Page dimensions are derived, not configured** (corrected after phase 3, which
found `sheet: {size, dpi, grid, gutter}` did not cover frank's four constants).
frank hardcodes `A4_W, A4_H = 2480, 3508`; there is no key for them, and adding
one would let `size: a4` and an inconsistent pixel size disagree. Derive from
`size` + `dpi` against a known-sizes table in millimetres:

```
round(210 / 25.4 * 300) == 2480      # A4 width,  exactly frank's constant
round(297 / 25.4 * 300) == 3508      # A4 height, exactly frank's constant
```

The derivation is *exact* for frank's values, not an approximation — verified
2026-08-03. `size` is not validated by `validate_config` (phase 3's deliberate
choice), so `build-sheets.py` must `SystemExit` on an unrecognised size rather
than silently producing a wrong-sized page.

**`grid` must genuinely work, or not exist.** frank hardcodes `3` in five
places: `//3` twice inside the `cell` computation, `3*cell + 2*GUTTER`,
`range(1, 10)`, and `divmod(pos - 1, 3)`. Honouring `grid: [cols, rows]` is
therefore a small rewrite of the gutter algebra — `cell = min((W - (cols+1)·G)
// cols, (H - (rows+1)·G) // rows)`, `grid_w = cols·cell + (cols-1)·G` — plus a
change to `pos`'s valid range (`1..cols*rows`). It is not a constant read. A
key that accepts `[2, 4]` and silently lays out 3×3 is worse than no key, so
the phase pins a non-3×3 case. For `[3, 3]` the generalised algebra must
reproduce frank's numbers exactly; that equality is the regression test.

Everything else — the centred grid, `divmod` row/col placement, and
`dpi=(dpi, dpi)` written into the PNG — is copied unchanged, because that maths
*is* the print contract.

Output filename: frank's is `frank-stickers-A4-sheet<N>.png`. The `frank-`
prefix must come from config (`project.name` slugged, or an explicit
`sheets_prefix`) so the ported script is not frank-shaped. Preserving frank's
exact filename is required for no-behavioral-change.

### 6. Schema migration v6 → v7

The ladder convention is a pure, idempotent `setdefault` migration per rung
(`migrations/005_to_006.py`). `migrations/006_to_007.py` seeds
`features.stickers = {enabled: false}` and leaves an explicit operator value
alone. Migrations are pure functions over the config dict — they cannot and
must not touch the filesystem, so nothing about frank's *files* happens here.

`validate_config.py`'s `ACCEPTED_VERSIONS` extends to `2..7`.

### 7. What `/update` migrates, and what it cannot

This is the part worth being precise about, because the operator's requirement
("frank deletes his implementation") is only *partly* mechanizable.

**Automatic**, via `manifest.legacy_dests`:

```yaml
legacy_dests:
  "scripts/build-sheets.py":
    - "{site}/_private/frank-stickers/build-sheets.py"
  "scripts/generate-stickers.py":
    - "{site}/_private/frank-stickers/generate-stickers.py"
```

`/update` writes the shipped copy at `<site_dir>/scripts/`, `unlink()`s
frank's, and prunes the emptied directory. Inert for every blog that never had
those paths.

**Not automatic.** `plan_update` skips `content` outright
(`update.py:153`), and frank's remaining sticker files are all content:
`stickers.yaml` (frank's prose), `images/*.png` (18 curated masters),
`sheets/*.png` (2 print artifacts), `README.md`. `/update` will not move,
rewrite, or delete any of them — by design, and that design is right: these
are the operator's irreplaceable artifacts.

So frank's adoption needs a **one-time transform**, shipped by blog-craft as
`tools/migrate_stickers.py`, that frank runs once:

1. reads frank's `stickers.yaml`;
2. emits the six `sticker_*` layers — including `sticker_mood` carrying the
   `_template` — plus the `sticker` composition order, for the operator to
   paste into `.blog-craft.yaml` (it does **not** edit the config — that file
   is content, and silent config surgery is how #60 happened). It must **never**
   emit a `mood:` key: frank already has one, and merging `_template` into it
   double-frames every cover (see the warning in §1);
3. rewrites the 18 stickers as v5 entries — `composition.{order, modifiers,
   scene, reference_images}`, `aspect_ratio: '1:1'`, `output:`, and the
   `sheet`/`pos` fields — into the new `features.stickers.prompts_file`;
4. `git mv`s `images/` and `sheets/` to the configured dirs;
5. prints the diff and exits non-zero if anything is ambiguous.

Deriving the entries mechanically (rather than hand-editing 18 of them) is
what makes the golden test in § Testing a real proof instead of a
transcription check.

### 8. frank adoption runbook (frank's own PR, not this one)

1. `/update` to the blog-craft release carrying this feature → scripts land,
   frank's two script copies are deleted.
2. Run `tools/migrate_stickers.py` → new prompts file, layers to paste,
   images/sheets moved.
3. Paste the layer block; set `features.stickers.enabled: true`.
4. Run the golden check (`--dry-run` over all 18) and confirm zero prompt
   drift against the committed goldens.
5. `git rm` the now-empty `blog/_private/frank-stickers/` remnants
   (`stickers.yaml`, `README.md`).
6. Rebuild sheets; confirm the two PNGs are pixel-identical to the committed
   ones.

## Testing

The bar is "no behavioral changes", so the tests are equality proofs against
frank's real data, not synthetic smoke.

- **Golden prompts (the contract).** Vendor frank's real `stickers.yaml` as
  `tests/fixtures/stickers/frank-stickers.yaml`, and its 18 composed prompts
  as `tests/fixtures/stickers/golden/<key>.txt`, generated once from frank's
  *legacy* script. A test asserts `generate-images.py --print-prompt <key>`
  equals the golden for all 18. This is the single test that proves the port,
  and it exercises `_template`, the sticker order, layer namespacing, and the
  transform together. Precedent: `tests/unit/test_image_compose.py`, which
  proves the same property for covers (with synthetic layers).
- **Reference payload order.** Per sticker, assert the resolved payload is
  exactly `[canon_face, anchor_09, anchor_20, clothing_subject?]` in that
  order. Precedent: `tests/unit/test_generate_images_references.py`.
- **`_template` unit tests.** Table hit, free-form passthrough, empty
  resolution stays empty, a layer with no `_template` is unchanged, and a
  malformed `_template` is rejected by the validator.
- **Non-destructive mode.** `--out <dir>` writes `<dir>/<key>.png` and leaves
  a pre-existing `output:` file byte-unchanged. Guards finding 3.
- **Fallback + timeout.** With `BLOG_CRAFT_TEST_MODE=1`, assert the fallback
  model is attempted when the primary raises, and that `timeout_ms` reaches
  `HttpOptions`.
- **Sheet determinism.** Build sheets from 18 synthetic 1×1 PNGs and assert
  dimensions `2480×3508`, `dpi == (300, 300)`, and that each cell's top-left
  pixel offset matches the computed centered-grid position. Then, separately,
  a frank-fixture check that rebuilding from the committed masters reproduces
  the committed sheets byte-for-byte.
- **Gating.** `features.stickers.enabled: false` (and absent) renders no
  sticker scripts; `true` renders both. Precedent:
  `tests/unit/test_features_gating.py`.
- **Migration ladder.** `006_to_007` is pure and idempotent, preserves an
  explicit `enabled: true`, and the ladder test picks up the new rung.

## Test Plan

| # | Claim | Level | Verification |
|---|---|---|---|
| 1 | frank's 18 sticker prompts compose byte-identically through blog-craft | unit | `tests/unit/test_stickers_golden.py` vs 18 committed goldens |
| 2 | Sticker reference payloads keep frank's exact order | unit | `tests/unit/test_stickers_references.py` |
| 3 | `_template` frames a resolved mood and never frames an empty one | unit | `tests/unit/test_compose.py` (extended) |
| 4 | `--out <dir>` never writes the entry's `output:` | unit | `tests/unit/test_generate_images_out_dir.py` |
| 5 | `fallback_model` is attempted on primary failure; `timeout_ms` is honored | unit | `tests/unit/test_generate_images_fallback.py` |
| 6 | Sheets are 2480×3508 @ 300 DPI with a centered 3×3 grid | unit | `tests/unit/test_build_sheets.py` |
| 7 | Rebuilt sheets are byte-identical to frank's committed sheets | smoke | `tests/smoke-stickers.sh` |
| 8 | `features.stickers` gates both scripts in/out of a rendered blog | unit | `tests/unit/test_features_gating.py` (extended) |
| 9 | `006_to_007` is pure, idempotent, and preserves an explicit opt-in | unit | `tests/unit/test_migration_007.py` |
| 10 | `/update` retires frank's two script copies and prunes the dir | unit | `tests/unit/test_update_legacy_dests.py` (extended) |
| 11 | `migrate_stickers.py` produces a prompts file whose prompts match goldens | unit | `tests/unit/test_migrate_stickers.py` |
| 12 | No existing blog's composed cover prompts change | unit | existing `test_image_compose.py` must pass unmodified |

## Acceptance rows (matrix backfill — same PR)

Per `.claude/rules/acceptance-matrix.md`, a new spec with a Test Plan owes
rows in the same PR. Proposed, to be added with
`--origin blog-craft:docs/superpowers/specs/2026-08-03-sticker-generation-design.md`:

| id | capability | acceptance claim | status |
|---|---|---|---|
| STK-1 | sticker prompt fidelity | Operator regenerates any of frank's 18 stickers and the prompt is byte-identical to the pre-port one | `not-implemented` |
| STK-2 | non-destructive regen | Operator regenerates a sticker without overwriting the curated master | `not-implemented` |
| STK-3 | print-ready sheets | Operator rebuilds the A4 sheets and prints at 100% with the keyline as a true cut path | `not-implemented` |
| STK-4 | capability gating | A blog without `features.stickers` gets no sticker surface and no behavior change | `not-implemented` |
| STK-5 | consumer migration | frank's `/update` retires its private implementation and adopts the shipped one | `not-implemented` |

Each is business-level: STK-1 and STK-3 are the two artifacts the operator
actually consumes (a prompt and a printable sheet), STK-2 is the data-loss
guard, STK-4 is the blast-radius promise to gondor/stoa, and STK-5 is the
operator's stated requirement. None restates an implementation detail.

## Risks & open items

1. **`border_spec` position.** frank's order puts `border_spec` *after*
   `scene` — transcribed into §1 and shown against its source there. Called
   out because it is the most likely single cause of a red golden: swapping it
   with `scene` yields a prompt that reads correctly and is still wrong.
2. **Prose with literal braces.** `_template` uses `str.format`. Any sticker
   prose containing `{` or `}` would raise or mis-substitute. None of frank's
   current prose does, but the validator should require exactly one `{}` and
   the transform should refuse prose containing stray braces.
3. **Contact-sheet geometry is a named divergence** unless decision 6 is
   implemented. It is a review-only artifact, so the operator may prefer to
   accept the reflow rather than parameterize.
4. **`.reference-pool` paths.** frank's sticker refs resolve against the repo
   root and include two *sticker images* as style anchors — meaning the
   sticker set references its own output. Moving `images/` therefore changes
   the anchor paths, and the transform must rewrite them consistently or the
   goldens will pass while generation silently loses the style anchors.
5. **`0.20.0` → next version.** A shipped-surface change requires a version
   bump; `check_version_bump_needed.py` enforces it. The CHANGELOG entry and
   `pyproject.toml` bump ride this PR.
6. **Two engines during the gap.** Between this PR merging and frank's
   adoption PR, frank still runs its fork. The goldens are committed here, so
   drift is detectable, but frank is not fixed until its own PR lands.

## Out of scope

- A published sticker gallery, shortcode, or Hugo page (operator decision 3).
- Sticker sets for gondor or stoa. The capability is available; no content is
  authored.
- Page sizes beyond the known-sizes table (`a4`, `letter`). The table is small
  and additive; an unrecognised `size` is a hard error, never a silent
  fallback. Note this is narrower than an earlier draft of this spec, which
  left `grid` decorative — see §5: a config key that accepts a value and
  quietly ignores it is a trap, so `grid` is implemented and tested rather
  than deferred.
- Retiring frank's `scripts/lib/contact_sheet.py`, which serves frank's other
  scripts too.

## Implementation Plans

| Plan | Repo | File | Depends on |
|---|---|---|---|
| 2026-08-03-stickers | `derio-net/blog-craft` | `2026-08-03-stickers` | — |
