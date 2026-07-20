# Image composition as a first-class generic optional system — implementation plan

Spec: `docs/superpowers/specs/2026-07-20-image-composition-system-design.md`.
Closes #39 end-to-end and supersedes PR #40 (absorbed in Phase 1).

## Shape of the work

The layered composition *engine* already ships (`compose.py` +
`generate-images.py`); what this plan changes is (a) the engine's last two
hardcoded layer names become config data (`_select` walk, Phase 2), and (b)
everything *around* the engine — scaffolder, skills, bootstrap, `/update` —
finally speaks the engine's own config contract instead of the dead
`metaphor.*`/`image_gen.*` vocabulary (Phases 3–7).

Byte-parity is the invariant threaded through every phase: frank's and
gondor's composed prompts must not change. Phase 2 proves it with unchanged
expected strings in `test_image_compose.py`; Phase 3 proves the migration
reproduces the old skill's hand-concatenation; Phase 6 proves the character
sheet's default output is unchanged; the post-merge Test Plans (spec) prove it
on the real blogs.

## Phase map

1. **Absorb PR #40** — take its two content files (generator + tests), fix the
   `gen-character-sheet.py` caller that failed its CI, defer versioning to
   Phase 7.
2. **Generic engine** — `_select` walk in `compose.py`; torso/mood branches
   deleted; frank fixture gains the explicit `_select` the migration will
   write, expected strings untouched.
3. **Config v4** — `migrations/003_to_004.py` (metaphor→layers,
   image_gen→image, torso `_select` injection), `validate_config.py` v4 keys.
4. **Scaffolder** — `blog_config.py` reader, `blog-post-create.sh` rewritten
   config-driven (`site_dir`, `--entry-field`, `--output`, no forced
   reference).
5. **`/update`** — `map_dest` path mapping (site_dir + config-rooted pool and
   prompts relocations), `--only` scoping, frank-shaped end-to-end fixture.
6. **D8 extras** — character sheet from `image.character_sheet.layers`,
   `validate_images.py` (+ CI wiring), `extract-subject.swift` port.
7. **Skills + docs + version** — blog-post/bootstrap-blog/update SKILL
   rewrites, CONFIG.md v4, matrix rows to `ci`, OpenCode mirror resync,
   CHANGELOG, single minor bump 0.8.0 → 0.9.0.

Phases 1→2→3→4→5 are a chain; Phase 6 needs only the engine (Phase 2); Phase 7
fans in from 5 and 6.

No manual phases: the operator-driven migrations of frank and gondor-blog are
post-merge Test Plans in the spec (IMG-COMP-8/9), not plan phases.

## Execution notes

- Every command runs in the isolation worktree
  (`/Users/derio/.cache/fr/worktrees/blog-craft/feat__image-composition-system`).
- `templates/hugo-hextra/scripts/*` and their `tools/*` twins must stay
  byte-identical where the repo already enforces mirrors; new files
  (`blog_config.py`, `validate_images.py`) follow the `validate_educational.py`
  mirror pattern and get manifest `framework` entries.
- Versioning happens exactly once (P7.T4.S2) — Phase 1 deliberately does NOT
  carry PR #40's 0.8.1 bump.
