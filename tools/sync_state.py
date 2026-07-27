#!/usr/bin/env python3
"""The sync snapshot — what config blog-craft last applied to this blog (#60).

`tools/update.py` recovers the 3-way-merge base by re-rendering the templates at
the recorded `blog_craft_version`. The base is meant to answer *"what did
blog-craft last give this blog?"* — that is `render(config_at_last_sync,
templates_at_recorded_version)`. Without a record of the first half, the
updater fed the old templates the operator's CURRENT config, so every config
edit showed up in the base as content blog-craft had supposedly already
shipped; `diff3` then read the on-disk file as a deliberate deletion and kept
it, silently discarding the change.

`.blog-craft.sync.yaml` is that record: the config, verbatim, as of the last
successful sync — written by `bootstrap-render.sh` (a bootstrap IS the first
sync) and by `update.py --apply` when the run is conflict-free.

Two properties are load-bearing:

* **Verbatim.** The payload is a byte copy, not a YAML round-trip, so the old
  templates are handed exactly what they were handed at sync time — comments,
  key order and all.
* **Deterministic.** No timestamp, no host, no run id. The reproduction harness
  renders a config twice and requires the two trees to be byte-identical.

Deliberately stdlib-only: `bootstrap-render.sh` calls this with a bare
`python3` that may have no PyYAML, on the same machines where the layer-palette
step already degrades to a warning.

Library:
  snapshot_path(blog_root)          -> Path
  read_snapshot(blog_root)          -> Path | None     # None when there is nothing usable
  write_snapshot(config, blog_root) -> Path

CLI:
  sync_state.py --config <.blog-craft.yaml> --blog <blog-root>
"""
from __future__ import annotations

import sys
from pathlib import Path

SNAPSHOT_NAME = ".blog-craft.sync.yaml"

_HEADER = """\
# blog-craft sync snapshot — GENERATED, DO NOT EDIT.
#
# The .blog-craft.yaml as of the last successful blog-craft sync (a bootstrap,
# or `tools/update.py --apply`). update.py renders THIS file — not your current,
# possibly-edited config — through the templates at `blog_craft_version`, to
# recover an honest 3-way-merge base.
#
# Rendering the base with the *current* config makes every config edit look like
# content blog-craft already shipped, so the merge reads your on-disk file as a
# deliberate deletion and keeps the deletion. See derio-net/blog-craft#60.
#
# COMMIT THIS FILE. Without it the updater falls back to the current config and
# says so. Delete it only to deliberately forget what was last synced.
"""


def snapshot_path(blog_root: str | Path) -> Path:
    """Where the snapshot lives: beside the blog's `.blog-craft.yaml`."""
    return Path(blog_root) / SNAPSHOT_NAME


def _has_payload(text: str) -> bool:
    """True when something other than comments and blank lines is present.

    A snapshot that is all header — a truncated or hand-mangled write — would
    render to nothing, so the caller must see it as "no snapshot" and take the
    warned fallback rather than failing mid-render.
    """
    return any(line.strip() and not line.lstrip().startswith("#")
               for line in text.splitlines())


def read_snapshot(blog_root: str | Path) -> Path | None:
    """The snapshot path, or None when there is nothing usable to render.

    Absent, empty, comment-only, a directory, unreadable — all collapse to None,
    so callers have exactly one fallback branch to reason about.
    """
    p = snapshot_path(blog_root)
    try:
        if not p.is_file():
            return None
        return p if _has_payload(p.read_text(encoding="utf-8", errors="replace")) else None
    except OSError:
        return None


def write_snapshot(config_path: str | Path, blog_root: str | Path) -> Path:
    """Record `config_path` as the config this blog is now synced to."""
    payload = Path(config_path).read_bytes()
    dest = snapshot_path(blog_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_HEADER.encode("utf-8") + payload)
    return dest


def _main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="the config to record")
    ap.add_argument("--blog", required=True, help="blog root (where the snapshot lands)")
    a = ap.parse_args(argv)
    try:
        print(write_snapshot(a.config, a.blog))
    except OSError as e:
        print(f"sync_state: cannot record {a.config}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
