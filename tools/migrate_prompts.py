#!/usr/bin/env python3
"""Migrate a prompts file's entries to the v5 composition-block shape.

Per entry: `prompt` -> `composition.scene`; non-standard fields (the
selectors) -> `composition.modifiers`; `references:` ->
`composition.reference_images.clothing`; and — because v5 references are
EXPLICIT (the v4 precedence chain is gone) — the primary reference the old
chain would have picked (config `image.reference_image`, else the series /
generic pool sheet) is FROZEN into `composition.reference_images.primary`
when that file exists.

Standard fields stay top-level: key, output, description, aspect_ratio,
image_size, operator_generated, post_process. `series` is copied into
modifiers (v5 home) — reference selection no longer consumes it.

Non-destructive: writes a .bak. NOTE: yaml round-trip drops comments — the
same tradeoff as migrate_config.py; hand-migrate when comments matter.

Usage: migrate_prompts.py --config <path/to/.blog-craft.yaml> [--check]
"""
from __future__ import annotations

import sys
from pathlib import Path

STANDARD_TOP = {"key", "output", "description", "aspect_ratio", "image_size",
                "operator_generated", "post_process", "count"}


def _frozen_primary(entry: dict, image_cfg: dict, root: Path):
    """Statically resolve what the v4 precedence chain would pick today."""
    ref = image_cfg.get("reference_image")
    if ref and (root / ref).is_file():
        return ref
    pool = image_cfg.get("reference_pool", ".reference-pool")
    series = entry.get("series") or "generic"
    for cand in (f"{pool}/{series}/reference-{series}.png",
                 f"{pool}/generic/reference-generic.png"):
        if (root / cand).is_file():
            return cand
    return None


def migrate_entry(entry: dict, image_cfg: dict, root: Path) -> dict:
    if "composition" in entry:
        return entry                                   # already v5
    out = {k: v for k, v in entry.items() if k in STANDARD_TOP}
    comp: dict = {}
    refs: dict = {}
    primary = _frozen_primary(entry, image_cfg, root)
    if primary:
        refs["primary"] = primary
    if entry.get("references"):
        refs["clothing"] = list(entry["references"])
    if refs:
        comp["reference_images"] = refs
    modifiers = {k: v for k, v in entry.items()
                 if k not in STANDARD_TOP and k not in ("prompt", "references")}
    if modifiers:
        comp["modifiers"] = modifiers
    comp["scene"] = entry.get("prompt", "")
    out["composition"] = comp
    return out


def _main(argv: list[str]) -> int:
    import argparse

    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--check", action="store_true", help="exit 1 if any entry is not v5 yet")
    a = ap.parse_args(argv)
    cfg_path = Path(a.config).resolve()
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    root = cfg_path.parent
    image_cfg = cfg.get("image") or {}
    prompts_path = root / image_cfg.get("prompts_file", "prompt_for_images.yaml")
    doc = yaml.safe_load(prompts_path.read_text()) or {}
    entries = doc.get("images") or []
    legacy = [e.get("key") for e in entries if isinstance(e, dict) and "composition" not in e]
    if a.check:
        if legacy:
            print(f"{len(legacy)} legacy entr{'y' if len(legacy) == 1 else 'ies'}: "
                  f"{', '.join(map(str, legacy))}", file=sys.stderr)
            return 1
        print("all entries are v5")
        return 0
    if not legacy:
        print("already v5 — nothing to do")
        return 0
    doc["images"] = [migrate_entry(e, image_cfg, root) if isinstance(e, dict) else e
                     for e in entries]
    prompts_path.with_suffix(prompts_path.suffix + ".bak").write_text(prompts_path.read_text())
    prompts_path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    print(f"migrated {len(legacy)} entries -> v5 (backup: {prompts_path.name}.bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
