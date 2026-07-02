#!/usr/bin/env python3
"""Schema-migration ladder runner (spec §8.1).

Discovers migrations/NNN_to_MMM.py, applies them in order from a config's
`version:` up to the latest, purely and idempotently. Non-destructive: the CLI
writes a `.bak` and only rewrites the config when something changed.

Library:
  upgrade(cfg: dict) -> dict     # config migrated to the latest version
  latest_version() -> int
CLI:
  migrate_config.py <config.yaml>            # in-place upgrade (+ .bak)
  migrate_config.py --check <config.yaml>    # exit 1 if not at latest
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MIGR_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _load_migrations():
    mods = []
    for f in sorted(MIGR_DIR.glob("[0-9][0-9][0-9]_to_[0-9][0-9][0-9].py")):
        spec = importlib.util.spec_from_file_location(f.stem, f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods.append(m)
    return sorted(mods, key=lambda m: m.FROM_VERSION)


def latest_version():
    return max((m.TO_VERSION for m in _load_migrations()), default=None)


def upgrade(cfg: dict) -> dict:
    by_from = {m.FROM_VERSION: m for m in _load_migrations()}
    v = cfg.get("version")
    while v in by_from:
        cfg = by_from[v].migrate(cfg)
        nv = cfg.get("version")
        if nv == v:                      # guard: a migration must advance the version
            break
        v = nv
    return cfg


def _main(argv):
    import argparse
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    path = Path(a.config)
    cfg = yaml.safe_load(path.read_text())
    if a.check:
        if cfg.get("version") == latest_version():
            print(f"config at latest (v{latest_version()})")
            return 0
        print(f"config v{cfg.get('version')} < latest v{latest_version()}", file=sys.stderr)
        return 1
    upgraded = upgrade(cfg)
    if upgraded == cfg:
        print(f"already at latest (v{cfg.get('version')})")
        return 0
    path.with_suffix(path.suffix + ".bak").write_text(path.read_text())  # non-destructive
    path.write_text(yaml.safe_dump(upgraded, sort_keys=True, allow_unicode=True))
    print(f"upgraded v{cfg.get('version')} -> v{upgraded.get('version')} (backup: {path.name}.bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
