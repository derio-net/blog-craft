# An honest 3-way base: snapshot the config at sync time

- **Issue:** derio-net/blog-craft#60
- **Branch:** `fix/update-base-config-snapshot`
- **Date:** 2026-07-27
- **Type:** fix (updater correctness + reporting)

## Problem (reproduced)

`tools/update.py` recovers the 3-way-merge base by re-rendering the templates at
the recorded `blog_craft_version` — but it feeds them **the config the operator
just edited**:

```python
subprocess.run(["bash", str(old / "tools" / "bootstrap-render.sh"), str(config), str(base_dir)], ...)
```

The base is meant to answer *"what did blog-craft last give this blog?"*, i.e.
`render(config_at_last_sync, templates_at_recorded_version)`. Only the second
half is honoured. So the moment the config changes, the base describes a blog
that never existed, and every `merged`-class path is diffed against a lie.

For a newly-enabled feature the lie is maximally damaging:

| | has the feature's contribution? |
|---|---|
| base (rendered with the **new** config) | yes |
| local (on disk, synced before the edit) | no |
| incoming (staging, new config) | yes |

`diff3` reads local as a **deliberate deletion** and keeps the deletion. The
new content is discarded, silently.

### Reproduction (run on this branch, 2026-07-27)

Blog bootstrapped at `v0.13.0` with `features.glossary` off, then toggled on:

```
--- glossary hits in freshly-synced blog CI (expect 0) ---
0
--- update.py --apply ---
MERGE    .github/workflows/blog-ci.yml [merged]
ADD      assets/css/glossary.css [merged]
ADD      layouts/shortcodes/abbr.html [framework]
ADD      layouts/shortcodes/glossary-index.html [framework]
update applied
--- glossary hits in CI after apply ---
0
--- glossary shortcodes added? ---
abbr.html
```

Three of four planned paths landed. `MERGE` was printed for the CI workflow,
`update applied` was printed, and the `Validate glossary` step never arrived.
Nothing in the output distinguishes that `MERGE` from one that wrote something.

### Scope of the defect

Structural, not glossary-specific. It hits **any** config change whose output
lands in a `merged` path (`hugo.toml`, `go.mod`, `go.sum`, `README.md`,
`assets/css/**`, `.github/**`): feature toggles, a changed `site_dir`, a new
`series_index.layers` palette, an added series. `framework` paths replace
unconditionally and genuinely-new files take the `add` branch, which is what
makes the failure look like a success.

It is also self-concealing: after the first apply the recorded version is
unchanged and the base still contains the content, so re-running `/update`
reports nothing outstanding.

## Decisions

The operator's brief pre-answered the one design fork — **take the general
fix** (config snapshot), not the narrow feature-flag-diff mitigation, which
would fix toggles only and leave `site_dir` / palette / series changes broken.
This session is non-interactive (no Q&A channel), so the remaining calls are
recorded here with their reasoning and flagged in the PR for review. All are
reversible.

1. **Snapshot file: `.blog-craft.sync.yaml`, at the blog root, tracked.**
   A sibling of `.blog-craft.yaml`, mirroring the name so its relationship is
   obvious. Tracked in the blog's git repo — untracked state would be lost on
   every fresh clone and silently degrade to the buggy fallback. One small YAML
   file, not a rendered tree, so spec §8.2's "no stored baseline" concern (tree
   drift, size, merge noise) does not apply.
2. **Written by both sync paths, from one helper.**
   `tools/bootstrap-render.sh` (bootstrap **is** the first sync) and
   `tools/update.py --apply`. A skill-prose-only instruction would be skipped;
   a bootstrapped blog with no snapshot falls back to today's behaviour on its
   very first toggle, which is the common case.
3. **`--apply` writes the snapshot only when the run is conflict-free.**
   A conflicted apply leaves paths unresolved; claiming "the blog is synced to
   config X" would then be false, and the stale-but-honest previous snapshot is
   the safer base. Worst case a later run re-offers a change the operator
   already has — a NOOP, not a loss.
4. **A merge that changes nothing is reported as `NOOP`, not `MERGE`.**
   A distinct action, so `MERGE` means "this file changes". A NOOP on a path
   the operator expected to change is the exact fingerprint of a wrong base.
5. **No auto-bump of `blog_craft_version`.** Out of scope, and the fix is
   correct either way: bumped → base is `render(snapshot, new templates)`;
   not bumped → the just-applied changes re-offer as NOOPs.

## Design

### `tools/sync_state.py` (new)

One small module owning the snapshot, so both writers and the reader agree:

```python
SNAPSHOT_NAME = ".blog-craft.sync.yaml"
snapshot_path(blog_root) -> Path
read_snapshot(blog_root)  -> Path | None      # None when absent/empty
write_snapshot(config_path, blog_root) -> Path
```

`write_snapshot` copies the **effective** config **verbatim** (bytes, not a YAML
round-trip) behind a provenance header. Verbatim matters: comments and key order
are preserved, so the old templates are handed byte-for-byte what they were
handed at sync time, and a re-render is deterministic. The header is YAML
comments, invisible to the renderer:

```yaml
# blog-craft sync snapshot — GENERATED, DO NOT EDIT.
# The .blog-craft.yaml as of the last successful blog-craft sync (bootstrap, or
# `tools/update.py --apply`). tools/update.py renders THIS — not your current,
# possibly-edited config — through the templates at `blog_craft_version` to
# recover an honest 3-way-merge base. See derio-net/blog-craft#60.
```

"Effective" config: at bootstrap this is the answers file **after**
`bootstrap-render.sh` stamps `blog_craft_version` — the file actually rendered,
not the operator's pre-stamp input.

`read_snapshot` returns `None` for absent, empty, or unreadable, so the caller
has exactly one fallback branch.

### `tools/update.py` — base resolution

`base_by_rerender(config, blog_craft_version, base_dir)` keeps its signature and
stays single-purpose: *render THIS config at THAT tag*. The caller chooses which
config:

```
base config = snapshot if present else the live config (+ warning)
```

The fallback is the issue's own compatibility requirement: existing blogs keep
working, and the first `--apply` writes the snapshot, so they are exact from
their next sync onward. It is **warned, not silent** — the whole defect was an
absence of signal:

```
[update] no .blog-craft.sync.yaml — the 3-way base is rendered with the CURRENT
         config, so changes you have made to .blog-craft.yaml since the last sync
         may be dropped on `merged` paths (blog-craft#60). This run records the
         snapshot; the next update will be exact.
```

If the snapshot render **fails** (a snapshot whose schema the recorded release
predates, say), fall back to the live config with a warning rather than aborting
the run — degraded is better than dead, and the previous behaviour is the
degraded mode.

`--base <dir>` still overrides everything, unchanged.

### `tools/update.py` — the `noop` action

In `plan_update`, a `merged` path whose clean 3-way merge equals what is already
on disk becomes `action: "noop"` instead of `"merge"`:

```python
merged, conflict = three_way(b, loc, inc)
if conflict:      action = "conflict"
elif merged == loc.read_bytes():
                  action = "noop"      # merge kept local wholesale — writes nothing
else:             action = "merge"
```

- `dry_run_diff` prints `NOOP <dest> [merged]  (merge produced no change)`.
- `apply_plan` skips `noop` — it writes nothing today either, via an identical
  byte-for-byte rewrite; making that explicit is the point.
- `_main` prints a per-action tally after the plan, so a dry-run reads as
  "2 replace, 1 merge, 1 noop" rather than an undifferentiated wall.

This is distinct from the existing "already up to date" skip (local == incoming,
never planned). A NOOP means the two sides *do* differ and the base said to keep
local — which is either a real operator deletion or a wrong base.

### `tools/bootstrap-render.sh`

After the render passes, before the Hugo smoke build, invoke `sync_state.py` to
write `<TARGET>/.blog-craft.sync.yaml` from the effective answers file.

Because the snapshot is a byte copy, `sync_state.py` imports nothing outside the
stdlib — unlike the layer-palette step it cannot fail for want of PyYAML, so a
plain `python3` always suffices. The call is still non-fatal (matching the
layer-palette treatment): a bootstrap must not die over its own bookkeeping, and
`update.py`'s fallback covers a missing snapshot.

The header carries **no timestamp**. `tests/reproduction/test_golden_configs.py`
renders a config twice and asserts zero structural drift; a clock in the header
would make every render differ from every other.

Every tree `bootstrap-render.sh` produces therefore carries a truthful snapshot,
including the staging tree `update.py` renders. That is self-consistent rather
than special-cased, and requires one manifest row.

### `templates/manifest.yaml`

`.blog-craft.sync.yaml` joins **`content`** — never merged, never replaced by an
update; `update.py` writes it explicitly, outside the plan. The row is required,
not cosmetic: without it, `reproduce.structural_diff` reports the file in a
staging tree as `unclassified materialized path` (spec §11) and the reproduction
harness and `smoke-update` go red.

`content` is the right class by its operational meaning — "the update flow never
touches this path" — even though the file is machine-written rather than
operator-authored.

## Alternatives rejected

- **Feature-flag diffing** (the issue's narrower mitigation): reconstruct which
  features the local tree evidences, treat a newly-enabled feature's paths as
  `add`. Fixes toggles only; `site_dir`, palette and series changes have the
  identical shape and stay broken. Also needs a per-feature path registry that
  must be updated by hand with every new feature — a second manifest to drift.
- **Store the rendered baseline tree** (spec §8.2's rejected option): correct
  but heavy — a full duplicate tree in every blog's repo, noisy in diffs. The
  snapshot buys the same correctness for one file.
- **Reconstruct the old config from git history of `.blog-craft.yaml`**: needs
  the blog to be a git repo, needs a reliable "last sync" commit marker (there
  is none), and breaks on squashed or shallow histories.

## Test strategy

Unit (`tests/unit/`), all offline:

- `test_sync_state.py` — path resolution; write/read round-trip; verbatim bytes
  (comments + key order preserved); header is comment-only so the payload still
  parses to the original mapping; `read_snapshot` returns `None` for absent /
  empty / unreadable.
- `test_update_flow.py` — the `noop` action: a merged path whose merge keeps
  local plans `noop` and `apply_plan` leaves the file byte-identical; `MERGE`
  still means a real change; `dry_run_diff` renders `NOOP`.
- `test_update_base_snapshot.py` — **the #60 regression, at the level the bug
  lives**: base rendered from a pre-toggle config vs the post-toggle config,
  asserting the feature's line arrives in the first case and (today) is dropped
  in the second; plus base-config selection (snapshot wins, absent → live config
  + warning, unreadable snapshot → live config + warning).

End-to-end (`tests/smoke-update.sh`): extend the existing vN→vN+1 cycle with a
config-toggle leg — bootstrap with a feature off, toggle it on, apply, and
assert the feature's contribution lands in the `merged` CI workflow, and that
the snapshot is written at bootstrap and refreshed on apply.

## Implementation Plans

| Plan | Repo | File | Depends on |
|------|------|------|------------|
| 2026-07-27-update-base-config-snapshot | `derio-net/blog-craft` | `2026-07-27-update-base-config-snapshot` | — |

## Test Plan

Post-merge, operator-driven — these need a real blog and a real release tag.

1. On a blog synced at the pre-fix release, run `/update` dry-run. Expect the
   `no .blog-craft.sync.yaml` warning and a plan whose `MERGE`/`NOOP` split is
   readable.
2. `--apply`; confirm `.blog-craft.sync.yaml` appears at the blog root, contains
   the config as applied, and is committed.
3. Toggle a `features.*` flag that contributes to a `merged` path (e.g.
   `features.glossary.enabled`), run `/update --apply`, and confirm the
   contribution **lands** — for glossary, `grep -c 'Validate glossary'
   .github/workflows/blog-ci.yml` is non-zero.
4. `hugo --buildDrafts` still builds; the operator's own edits to `hugo.toml` /
   `assets/css/**` survived.
5. Re-run `/update` — the second run reports no outstanding change for those
   paths (no oscillation).

## Shipped beyond this spec

Recorded after the fact, so the design record matches what merged in #62.

**The backfilling run names what it may have frozen** (`baselined_by_fallback`).
The spec treats the no-snapshot fallback purely as a compatibility path: warn,
apply, record, be exact from the next run. That is true going *forward* and
misses what recording the snapshot does *backward*. The first snapshot asserts
"this blog is synced to this config" over a tree that may already be missing a
change an earlier, pre-#60 run dropped — so from the run after it, that path is
an ordinary `NOOP` with no warning attached, and the tool has stopped
disagreeing with the drift it inherited.

The backfilling run is therefore the last run that can still see it. It now
lists, by mapped destination, every `merged` path its fallback base resolved to
`NOOP`, and says how to diff each against a fresh render. Silent on a
snapshot-backed run and on a fallback run whose plan had no `NOOP`s — a warning
that fires on clean plans is one operators learn to skip.

The two cases are genuinely indistinguishable from inside a single run (an
honest `NOOP` and an inherited drop look identical), which is why the tool names
the candidates rather than guessing. Covered by matrix row **UB-5** and four
tests in `tests/unit/test_update_base_snapshot.py`, pinning both directions plus
`site_dir`-aware destination mapping.
