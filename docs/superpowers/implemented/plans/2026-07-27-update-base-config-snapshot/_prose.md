# An honest 3-way base: snapshot the config at sync time

Fixes derio-net/blog-craft#60 — enabling a `features.*` flag silently drops its
contribution to every `merged`-class file, because `update.py` recovers the
3-way base by rendering **the config the operator just edited** through the old
templates. The base then contains the new content, the on-disk file does not, and
`diff3` reads that as a deliberate deletion and keeps it.

Four phases, TDD throughout:

1. **`tools/sync_state.py`** — one stdlib-only module owning
   `.blog-craft.sync.yaml`: a verbatim, timestamp-free copy of the config as of
   the last successful sync, behind a comment-only provenance header.
2. **`update.py`** — render the base from the snapshot (falling back, loudly, to
   today's behaviour when there is none), and split the clean-merge branch so a
   merge that writes nothing reports as `NOOP` rather than masquerading as
   `MERGE`. Proven against the issue's real reproduction, not just synthetic trees.
3. **Close the loop** — bootstrap writes the snapshot too (bootstrap *is* the
   first sync, and the first toggle after a fresh bootstrap is the common case),
   the manifest classifies the file as `content`, and `smoke-update` grows the
   toggle leg that the original bug would have failed.
4. **Ship** — skill + config docs, the OpenCode mirror, acceptance rows for the
   spec's Test Plan claims, CHANGELOG, and the version bump CI's guard requires.

The narrower feature-flag-diffing mitigation was rejected: it fixes toggles only,
leaving `site_dir`, palette and series changes broken with the identical shape,
and it needs a hand-maintained per-feature path registry — a second manifest to
drift.
