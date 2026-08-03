#!/usr/bin/env python3
"""Re-derive the 18 sticker goldens from frank's OWN `compose_prompt()`.

This is the mechanized form of the provenance recorded in
`GOLDEN-PROVENANCE.md`: the goldens in `golden/` are the output of frank's
legacy private generator, not of blog-craft, so `tests/unit/test_stickers_golden.py`
is an equality proof rather than a transcription check.

It is NOT run by the test suite and cannot be: frank's repo is not mounted in
blog-craft's isolation container (journal `orch-frank-not-mounted-in-container`),
and after vendoring nothing in CI needs it. It exists so the derivation is
repeatable by hand on a machine that has frank checked out:

    tests/fixtures/stickers/derive-goldens.py --frank /path/to/frank [--check]

`--check` re-derives into memory and diffs against the committed goldens instead
of writing them — the way to prove a frank-side prose edit has (or has not)
drifted from the committed set.

WHY the module has to be stubbed. `frank/blog/_private/frank-stickers/generate-stickers.py`
cannot be imported as-is: it does `from lib.contact_sheet import compose_contact_sheet`
at module level and that module no longer exists (frank's own blog-craft cutover
`bd0415e6` deleted `scripts/lib/contact_sheet.py` AND `lib/__init__.py`), so the
generator has raised ModuleNotFoundError since that cutover. `--dry-run` is no help
either: it truncates every prompt to 300 chars (`generate-stickers.py:101`) while
the real prompts are ~4.6k. So we stub the API-only imports and call the two pure
functions directly. `compose_prompt` and `scene_refs` touch NONE of the stubbed
modules — `compose_prompt` is a `"\n\n".join` over dict lookups, `scene_refs` is
`pathlib` + `.exists()` — which is what makes the stubbing safe rather than
convenient.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import types
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
VENDORED = HERE / "frank-stickers.yaml"
GOLDEN = HERE / "golden"
REL_SRC = "blog/_private/frank-stickers/generate-stickers.py"

# The five API-only modules. Each is imported at frank's module level and used
# ONLY on the generation path (genai client / PIL image objects / the deleted
# contact-sheet helper), never by compose_prompt or scene_refs.
STUBS = ("google", "google.genai", "PIL", "lib", "lib.contact_sheet")


def load_frank_module(src: Path):
    """Import frank's generator with its API-only imports stubbed out."""
    for name in STUBS:
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["google"].genai = sys.modules["google.genai"]
    sys.modules["google.genai"].types = types.SimpleNamespace()
    sys.modules["PIL"].Image = types.SimpleNamespace()
    sys.modules["lib.contact_sheet"].compose_contact_sheet = lambda *a, **k: None
    sys.modules["lib"].contact_sheet = sys.modules["lib.contact_sheet"]
    spec = importlib.util.spec_from_file_location("frank_stickers_legacy", str(src))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive(frank_root: Path) -> dict[str, tuple[str, list[str]]]:
    """{key: (prompt, [reference basenames])} from frank's own functions.

    The config is the VENDORED copy, so the committed goldens are provably the
    composition of the committed fixture — not of a frank checkout that may have
    moved on since.
    """
    src = frank_root / REL_SRC
    if not src.is_file():
        raise SystemExit(f"frank's generator not found: {src}")
    mod = load_frank_module(src)
    cfg = yaml.safe_load(VENDORED.read_text())
    out = {}
    for s in cfg["stickers"]:
        out[s["key"]] = (mod.compose_prompt(cfg, s),
                         [p.name for p in mod.scene_refs(cfg, s)])
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frank", default="/Users/derio/Docs/projects/DERIO_NET/frank",
                    help="path to a frank checkout")
    ap.add_argument("--check", action="store_true",
                    help="diff against the committed goldens instead of writing")
    a = ap.parse_args(argv)
    derived = derive(Path(a.frank).expanduser().resolve())

    if a.check:
        bad = []
        for key, (prompt, refs) in derived.items():
            for name, want in ((f"{key}.txt", prompt + "\n"),
                               (f"{key}.refs.txt", "".join(r + "\n" for r in refs))):
                have = (GOLDEN / name).read_text() if (GOLDEN / name).is_file() else None
                if have != want:
                    bad.append(name)
        print(f"{len(derived)} stickers derived; {len(bad)} drifted" +
              (": " + ", ".join(bad) if bad else ""))
        return 1 if bad else 0

    GOLDEN.mkdir(parents=True, exist_ok=True)
    for key, (prompt, refs) in derived.items():
        # A trailing newline so the file is exactly what `generate-images.py
        # --print-prompt <key>` puts on stdout (`print()` adds one), which lets
        # the test compare BYTES with no normalisation step to get wrong.
        (GOLDEN / f"{key}.txt").write_text(prompt + "\n")
        (GOLDEN / f"{key}.refs.txt").write_text("".join(r + "\n" for r in refs))
    print(f"wrote {2 * len(derived)} files for {len(derived)} stickers into {GOLDEN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
