#!/usr/bin/env python3
"""One-time transform of a legacy private sticker set into blog-craft's v5 shape.

`/update` cannot do this. `plan_update` skips the `content` class outright
(`update.py:153`), and every remaining file of frank's sticker set IS content:
`stickers.yaml` (his prose), `images/*.png` (18 curated masters), `sheets/*.png`
(2 print artifacts), `README.md`. That skip is *correct* — those are the
operator's irreplaceable artifacts — so the port needs a transform run once, by
hand (spec §7, and §8 for the runbook it slots into).

What it does:

1. reads the legacy `stickers.yaml`;
2. **prints** the six `sticker_*` layers + the `sticker` composition order as two
   fragments the operator MERGES into the `image.layers:` and
   `image.composition_orders:` mappings their config already has. The fragments
   carry no `image:`, `layers:` or `composition_orders:` key of their own, so
   there is nothing a paste can duplicate — see `PASTE_BEGIN`. It does NOT edit
   `.blog-craft.yaml`: that file is `content` class, and silent config surgery is
   how #60 happened;
3. rewrites the 18 sticker records as v5 entries into
   `features.stickers.prompts_file`;
4. `--move-assets` `git mv`s `images/` and `sheets/` to the configured dirs,
   REFUSING when a destination already exists;
5. prints a unified diff, and exits non-zero naming anything ambiguous.

Three properties worth stating, because each is a way the migration can look fine
and be wrong:

**It never emits a bare `mood:`.** `_template` attaches to a *layer*, so it
applies to every order naming that layer. frank's cover `mood` table already holds
complete sentences and his `hero`/`banner` orders name plain `mood`, so a
`_template` there composes "Frank's expression: Frank's expression is curious — …"
on all ~84 of his covers. Nothing in blog-craft would catch it. Hence
`sticker_mood`, a `_template`-only layer of its own.

**`clothing: {}` is emitted deliberately.** A layer that is *absent* from
`image.layers` resolves to `""`, and `compose()` drops empty sections — so
omitting it would silently delete the clothing sentence from all 18 prompts.

**Reference paths under the legacy directory are relocated.** frank's style
anchors are two of his own sticker masters, so the set references its own output;
moving `images/` moves the anchors with it. The prompt text never names a path, so
the goldens pass either way and only generation would notice (spec risk 4).

Prose containing `{` or `}` passes through **unharmed**: `str.format` never
rescans the substituted argument, so only the `_template` string itself is parsed.
An earlier draft of the spec (§Risks 2, now withdrawn) said the opposite; a brace
guard here would reject valid content for no reason.

Usage:
    tools/migrate_stickers.py --config <blog>/.blog-craft.yaml \\
        --legacy <blog>/blog/_private/frank-stickers/stickers.yaml \\
        [--move-assets] [--dry-run]
"""
from __future__ import annotations

import argparse
import difflib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# Transcribed from frank's `compose_prompt` (`generate-stickers.py:49-54`). The
# counter-intuitive element is last: `border_spec` follows `scene`, because the
# sticker finish is described after the scene it frames. Swapping those two yields
# a prompt that reads perfectly well and is not frank's.
STICKER_ORDER = [
    "sticker_base_character",
    "sticker_atmosphere",
    "sticker_reference_guidance",
    "sticker_face_pins",
    "clothing",
    "sticker_mood",
    "scene",
    "sticker_border_spec",
]

# layer name -> legacy top-level key. The rename is REQUIRED, not cosmetic: the
# sticker `base_character` says the head is "NOT a hard blocky / square flat-top"
# while frank's COVER `base_character` says "flat-top hair" — they contradict each
# other and cannot share a layer name (spec §Findings 2).
PROSE_LAYERS = {
    "sticker_base_character": "base_character",
    "sticker_atmosphere": "sticker_atmosphere",
    "sticker_reference_guidance": "reference_guidance",
    "sticker_face_pins": "face_pins",
    "sticker_border_spec": "border_spec",
}

# frank's f-string, as a `_template`. Exactly one `{}` and no other brace, which is
# what `validate_config._validate_template` requires (by policy, so a frame has one
# obvious spelling and is mechanically emittable — which is this file).
MOOD_TEMPLATE = "Frank's expression: {}."

# The instruction the operator FOLLOWS, so it has to name the merge and the hazard.
# An earlier version said "paste this under `image:`" above a fragment whose own root
# key WAS `image:`, holding `composition_orders:` and `layers:` — all three keys a
# blog with covers already has. Both readings of that instruction destroyed data:
# appended at top level, PyYAML's duplicate-key last-wins replaced the whole `image:`
# mapping (`model`, `prompts_file`, every cover layer, every cover order); pasted as
# two sub-keys, it replaced `composition_orders` and `layers` wholesale. Nothing
# errors — `validate_config` returns [] — and the only symptom is an empty composed
# prompt per cover, at exit code 0.
#
# So the emission carries NO structural key: two fragments, each already at the depth
# it occupies inside `image:`, leaving nothing for a paste to duplicate. The residual
# hazard is a leaf name the config already defines, which is what the WARN in `_run`
# is for; the full list is one order name (`sticker`) and at most seven layer names.
PASTE_BEGIN = (
    "# ---8<--- MERGE the two fragments below INTO the mappings that ALREADY EXIST\n"
    "#          under `image:` in .blog-craft.yaml, keeping the indentation shown.\n"
    "#          Do NOT add a second `image:`, `composition_orders:` or `layers:`\n"
    "#          key: YAML resolves duplicate keys by silently taking the LAST one,\n"
    "#          so a second copy DELETES everything the existing one holds — every\n"
    "#          cover layer, every cover order — and nothing warns you.\n"
    "#          If `image:` has no `composition_orders:` (or no `layers:`) yet, add\n"
    "#          that one key once and put the fragment under it. ---8<---")
ORDERS_MARK = "# --- merge into `image.composition_orders:` ---"
LAYERS_MARK = "# --- merge into `image.layers:` ---"
PASTE_END = "# ---8<--- end of the two fragments ---8<---"

# Printed INSTEAD of a `clothing:` key when the target config already has that
# layer. The operator merges the fragments into their config, and PyYAML resolves a
# duplicate mapping key by silently taking the LAST one — so emitting `clothing: {}`
# against an existing table does not merely repeat it, it DESTROYS it, and every
# entry selecting from it loses its clothing section with no error anywhere.
CLOTHING_KEPT_NOTE = (
    "NOTE: image.layers.clothing already exists in this config, so it is "
    "deliberately NOT part of the fragments above.\n"
    "      Sticker entries carry free-form clothing prose, which _resolve_modifier "
    "returns unchanged via its\n"
    "      passthrough (verified here for every sticker), so the existing layer "
    "already serves the stickers as-is.\n"
    "      A second `clothing:` key would SILENTLY REPLACE that table — YAML "
    "duplicate keys are last-wins — and\n"
    "      every entry selecting from it would then compose with no clothing "
    "section at all."
)

# Composed into the prompt, so an empty one changes the section COUNT: frank's
# `"\n\n".join` does not filter empty sections while `compose()` does. The two
# agree only because all eight sections are non-empty for all 18 stickers.
COMPOSED_FIELDS = ("clothing", "mood", "scene")


class Fail(Exception):
    """An ambiguity the operator has to resolve. Printed, then exit non-zero."""


# --- YAML emission -----------------------------------------------------------

class _Block(str):
    """A prose string to emit as a `|-` block scalar rather than a folded line."""


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(
    _Block,
    lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", str(v), style="|"),
)


def dump(obj) -> str:
    """`width` is effectively unbounded on purpose: re-wrapping prose is exactly
    what makes a "was this edited?" diff unreadable, and prose fidelity is the
    thing the whole port is judged on."""
    return yaml.dump(obj, Dumper=_Dumper, sort_keys=False, allow_unicode=True,
                     width=10 ** 9)


def fragment(mapping: dict, indent: int = 4) -> str:
    """`dump(mapping)` shifted to the depth it occupies INSIDE `image:`.

    Four spaces: blog-craft's configs are two-space indented, so `image.layers` and
    `image.composition_orders` hold their keys at depth 2. Emitting at the real
    indentation is what lets the printed text carry no enclosing `image:` /
    `layers:` / `composition_orders:` key — the three keys that made the old
    `image:`-rooted block destructive to paste (see `PASTE_BEGIN`).

    A blank line inside a block scalar is left unindented: legal YAML (block-scalar
    empty lines need no indentation) and it keeps trailing whitespace out of
    something the operator is about to commit.
    """
    pad = " " * indent
    return "".join(pad + ln if ln.strip() else ln
                   for ln in dump(mapping).splitlines(keepends=True))


# --- the two fragments the operator merges -----------------------------------

def layer_block(legacy: dict, existing_layers: dict | None = None) -> dict:
    """The two `image:` sub-mappings: the eight-token order plus the layers it names.

    Layers are emitted in composition order (minus the reserved `scene`), which is
    both the most readable arrangement for a reader checking the order against the
    layers and the arrangement the committed fixture config carries.

    `clothing` is the one key whose emission depends on the TARGET config, because
    it is the one name the sticker order shares with an ordinary cover layer — see
    `CLOTHING_KEPT_NOTE`. The five `sticker_*` names and `sticker_mood` are
    namespaced precisely so they cannot collide, and `composition_orders.sticker` is
    a new named order; `mood` is never emitted at all.
    """
    existing = existing_layers or {}
    missing = [k for k in PROSE_LAYERS.values() if not str(legacy.get(k) or "").strip()]
    if missing:
        raise Fail("the legacy file is missing prose for: " + ", ".join(missing))
    layers: dict = {}
    for tok in STICKER_ORDER:
        if tok == "scene":
            continue                              # reserved: comes from the entry
        if tok == "clothing":
            if tok in existing:
                # Emitting it here would not be redundant, it would be DESTRUCTIVE.
                continue
            # Absent from the target: it MUST be emitted. An unknown layer resolves
            # to "" and compose() drops the section — the clothing sentence would
            # vanish from all 18 prompts.
            layers[tok] = {}
        elif tok == "sticker_mood":
            layers[tok] = {"_template": MOOD_TEMPLATE}
        else:
            layers[tok] = _Block(legacy[PROSE_LAYERS[tok]])
    return {"composition_orders": {"sticker": list(STICKER_ORDER)}, "layers": layers}


def _resolve_layer():
    """The shipped `tools/compose.py` resolver — the engine's own, not a model of it."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    from compose import resolve_layer
    return resolve_layer


def check_clothing_passthrough(layer, stickers: list) -> None:
    """Verify the EXISTING clothing layer returns each sticker's prose unchanged.

    Omitting `clothing` from the block rests on a claim — that a cover clothing
    table already serves stickers, because their value is free-form prose and
    `_resolve_modifier` passes an unmatched string through. That claim is true for
    frank's table and it is checked rather than trusted, because the ways it can
    fail are all silent:

    - a value that happens to equal a GROUP name hits the named lookup, resolves to
      a container, and `_chunk` returns "" — seven sections instead of eight;
    - a multi-step `_select` on the existing layer walks entry fields that sticker
      entries do not carry, and an intermediate miss returns "" for all of them;
    - a `_template` on the existing layer would frame every sticker's clothing.

    Running the real resolver over the real values catches all three at once, and
    anything else of the same shape that nobody has thought of yet.
    """
    resolve_layer = _resolve_layer()
    bad = []
    for s in stickers:
        want = s["clothing"]
        got = resolve_layer("clothing", layer, {"clothing": want})
        if got != want:
            bad.append(f"{s['key']} -> {(got or '<dropped>')[:60]!r}")
    if bad:
        raise Fail(
            "the config's existing image.layers.clothing does not return these "
            "stickers' clothing prose unchanged, so their clothing section would be "
            "reworded or dropped: " + "; ".join(bad) + ". Most often the value is a "
            "bare group name from that table rather than a sentence — reword the "
            "sticker's clothing prose, or give the sticker order its own layer name")


# --- path relocation ---------------------------------------------------------

def _relocations(legacy_rel: str, stk: dict) -> list[tuple[str, str]]:
    return [(f"{legacy_rel}/images", stk["images_dir"]),
            (f"{legacy_rel}/sheets", stk["sheets_dir"])]


def relocate(rel: str, legacy_rel: str, moves: list[tuple[str, str]]) -> str:
    """Rewrite a legacy-relative reference path to its configured destination.

    Only paths under the legacy directory move; the canon face and the clothing
    subjects live in `.reference-pool/`, which does not move — rewriting those
    would kill 13 of the 18 payloads.
    """
    for old, new in moves:
        if rel == old or rel.startswith(old + "/"):
            return new + rel[len(old):]
    if rel == legacy_rel or rel.startswith(legacy_rel + "/"):
        raise Fail(f"reference {rel!r} is inside the legacy directory but in neither "
                   f"images/ nor sheets/, so there is no configured destination for "
                   f"it — move it by hand and re-run")
    return rel


# --- entries -----------------------------------------------------------------

def _refs(legacy: dict, s: dict) -> list[str]:
    """frank's payload, primary FIRST: `[canon_face, *style_anchors, subject?]`.

    Order is not cosmetic — the composed prose declares the FIRST attached image
    the authority for Frank's face ("IGNORE those facial details" for the rest), so
    a payload led by a clothing anchor takes the face from the wrong picture.
    """
    refs = dict(legacy.get("references") or {})
    for key in ("canon_face", "style_anchors"):
        if not refs.get(key):
            raise Fail(f"the legacy file is missing references.{key}")
    if not isinstance(refs["style_anchors"], list):
        raise Fail("references.style_anchors must be a list")
    out = [str(refs["canon_face"]), *[str(a) for a in refs["style_anchors"]]]
    anchor = s.get("clothing_anchor")
    if anchor:
        if not refs.get("subjects_dir"):
            raise Fail(f"{s['key']}: clothing_anchor {anchor!r} needs "
                       f"references.subjects_dir")
        out.append(f"{refs['subjects_dir']}/{anchor}")
    return out


def sticker_entry(legacy: dict, s: dict, stk: dict, legacy_rel: str,
                  moves: list[tuple[str, str]]) -> dict:
    """One legacy record as a v5 `composition` entry (spec §5b).

    Every field is load-bearing:

    - `order` is the BRACKETED reference. A bare `sticker` is not a synonym:
      `_ORDER_REF` (`generate-images.py:99`) only matches the bracketed form, an
      unmatched string resolves to `[]`, `compose([])` is `""`, and `main()` SKIPS
      an entry whose prompt is empty — so the wrong spelling means all 18
      stickers, no output, exit code 0.
    - the mood modifier is `sticker_mood`, not `mood`: `_resolve_modifier` looks up
      `entry.get(<layer name>)`, and the frame lives on its own layer so it cannot
      double-frame frank's covers.
    - `scene` goes in `composition.scene`, which `selector_source` exposes to the
      reserved `scene` token as `prompt`.
    - `sheet` / `pos` ride along untouched, for `build-sheets.py`.
    """
    key = s["key"]
    refs = [relocate(r, legacy_rel, moves) for r in _refs(legacy, s)]
    entry = {
        "key": key,
        "description": s["description"],
        "output": f"{stk['images_dir']}/sticker-{key}.png",
        "aspect_ratio": (legacy.get("defaults") or {}).get("aspect_ratio", "1:1"),
    }
    # frank's own skip rule: a sticker with no sheet/pos is simply not on a sheet
    # (`build-sheets.py`). Absent stays absent rather than becoming a guess.
    for field in ("sheet", "pos"):
        if s.get(field) is not None:
            entry[field] = s[field]
    entry["composition"] = {
        "order": "composition_orders[sticker]",
        "modifiers": {"sticker_mood": s["mood"], "clothing": s["clothing"]},
        "scene": s["scene"],
        "reference_images": {"primary": refs[0], "clothing": refs[1:]},
    }
    return entry


def _check_stickers(stickers: list) -> None:
    if not isinstance(stickers, list) or not stickers:
        raise Fail("the legacy file has no `stickers:` list")
    seen: set[str] = set()
    for i, s in enumerate(stickers):
        if not isinstance(s, dict):
            raise Fail(f"sticker #{i + 1} is not a mapping")
        key = str(s.get("key") or "").strip()
        if not key:
            raise Fail(f"sticker #{i + 1} has no `key`")
        if key in seen:
            raise Fail(f"duplicate sticker key {key!r} — keys become the output "
                       f"filename `sticker-{key}.png`, so two records would "
                       f"overwrite one master")
        seen.add(key)
        if not str(s.get("description") or "").strip():
            raise Fail(f"{key}: no `description` — it becomes the entry's label")
        for field in COMPOSED_FIELDS:
            if not str(s.get(field) or "").strip():
                raise Fail(
                    f"{key}: `{field}` is empty, so the composed prompt would have "
                    f"SEVEN sections where the legacy generator produced eight "
                    f"(its join does not filter empty sections; compose() does). "
                    f"Fill it in or drop the sticker — migrating it would silently "
                    f"stop being prompt-preserving")


def entries(legacy: dict, stk: dict, legacy_rel: str) -> list[dict]:
    stickers = legacy.get("stickers")
    _check_stickers(stickers)
    moves = _relocations(legacy_rel, stk)
    out = [sticker_entry(legacy, s, stk, legacy_rel, moves) for s in stickers]
    for s in stickers:
        slug = str(s.get("slug") or "")
        if slug and slug != re.sub(r"^\d+-", "", s["key"]):
            # `slug` has no consumer (neither the shim nor build-sheets.py reads
            # it) and is normally the key minus its numeric prefix, so dropping it
            # loses nothing. A slug that is NOT derivable is operator information
            # the transform would silently discard — say so, but do not block a
            # migration over a field nothing generates from.
            print(f"NOTE: {s['key']}: slug {slug!r} is not derivable from the key "
                  f"and is not carried into the v5 entry", file=sys.stderr)
    return out


# --- assets ------------------------------------------------------------------

def _git_toplevel(path: Path):
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def plan_moves(legacy_dir: Path, root: Path, stk: dict) -> list[tuple[Path, Path]]:
    """`(src, dest)` for each directory that actually has to move.

    These 20 PNGs are `content` class — `/update` skips them by design
    (`update.py:153`) because they are irreplaceable operator artifacts. That is
    exactly why an existing destination is a REFUSAL and never an overwrite.
    """
    todo = []
    for sub, key in (("images", "images_dir"), ("sheets", "sheets_dir")):
        src, dest = legacy_dir / sub, root / stk[key]
        if src.resolve() == dest.resolve():
            print(f"{sub}/ is already at the configured path ({stk[key]})")
            continue
        if not src.exists():
            print(f"nothing to move: {src} is already gone")
            continue
        if dest.exists():
            raise Fail(f"refusing to move {src} -> {dest}: the destination already "
                       f"exists. Those PNGs are irreplaceable curated masters — "
                       f"merge or remove {dest} by hand, then re-run")
        todo.append((src, dest))
    return todo


def move(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    top = _git_toplevel(src.parent)
    if top is not None:
        r = subprocess.run(["git", "-C", str(top), "mv", str(src), str(dest)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            print(f"git mv {src} -> {dest}")
            return
        # untracked sources, or a path outside the index: a plain move is still
        # the right outcome, but say why git declined.
        print(f"NOTE: git mv declined ({r.stderr.strip()}); moving without git",
              file=sys.stderr)
    shutil.move(str(src), str(dest))
    print(f"moved {src} -> {dest}")


# --- main --------------------------------------------------------------------

def _inside(root: Path, p: Path, what: str) -> Path:
    try:
        p.resolve().relative_to(root.resolve())
    except ValueError:
        raise Fail(f"{what} escapes the blog root: {p} is outside {root}") from None
    return p


def _stickers_block(cfg: dict) -> dict:
    stk = ((cfg.get("features") or {}).get("stickers")) or {}
    if not isinstance(stk, dict) or not stk:
        raise Fail("features.stickers is missing from the config — run /update "
                   "first so the v6->v7 rung seeds it, then set its three paths")
    for key in ("prompts_file", "images_dir", "sheets_dir"):
        if not str(stk.get(key) or "").strip():
            raise Fail(f"features.stickers.{key} is missing or empty")
    return stk


def _run(a) -> int:
    cfg_path = Path(a.config).expanduser().resolve()
    if not cfg_path.is_file():
        raise Fail(f"no config at {cfg_path}")
    root = cfg_path.parent
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    stk = _stickers_block(cfg)

    legacy_path = Path(a.legacy).expanduser().resolve()
    if not legacy_path.is_file():
        raise Fail(f"no legacy sticker file at {legacy_path}")
    _inside(root, legacy_path, "the legacy file")
    legacy_dir = legacy_path.parent
    if legacy_dir.resolve() == root.resolve():
        raise Fail("the legacy stickers.yaml must live in its own directory "
                   "(its images/ and sheets/ siblings are what get moved)")
    legacy_rel = legacy_dir.resolve().relative_to(root.resolve()).as_posix()

    legacy = yaml.safe_load(legacy_path.read_text()) or {}
    if "stickers" not in legacy and "images" in legacy:
        # Its own output: entries under `images:`, no legacy `stickers:` list.
        # A no-op, not a double transform.
        print(f"{legacy_path} is already migrated (v5 entries) — nothing to do")
        return 0

    dest = _inside(root, root / stk["prompts_file"], "features.stickers.prompts_file")
    if dest.resolve() == legacy_path.resolve():
        raise Fail(f"features.stickers.prompts_file resolves to the legacy source "
                   f"({legacy_path}); writing it would destroy the only copy of "
                   f"the prose being migrated — point it somewhere else")
    _inside(root, root / stk["images_dir"], "features.stickers.images_dir")
    _inside(root, root / stk["sheets_dir"], "features.stickers.sheets_dir")

    existing_layers = (cfg.get("image") or {}).get("layers") or {}
    reuse_clothing = isinstance(existing_layers, dict) and "clothing" in existing_layers
    block = layer_block(legacy, existing_layers if reuse_clothing else None)
    items = entries(legacy, stk, legacy_rel)
    if reuse_clothing:
        check_clothing_passthrough(existing_layers["clothing"], legacy["stickers"])
    # Any REMAINING key the fragments emit that the config already defines will be
    # replaced on merge, silently, by YAML's last-wins rule. That set is now the
    # WHOLE collision surface — the fragments carry no `image:` / `layers:` /
    # `composition_orders:` key, so only leaves can collide: one order name
    # (`sticker`) and at most seven layer names (six `sticker_*` plus `clothing`).
    # Against frank the set is empty (measured: his layers are base_character,
    # base_atmosphere, reference_guidance, clothing, mood, and his orders are hero /
    # scenery / banner / banner_transform) — the `sticker_*` namespacing is exactly
    # what makes it empty. A WARN rather than a refusal: for a prose layer, replacing
    # it with the legacy prose is what re-running the migration MEANS. Only
    # `clothing` needs the value preserved, and that one is omitted above.
    existing_orders = (cfg.get("image") or {}).get("composition_orders") or {}
    clashes = [f"image.layers.{k}" for k in block["layers"]
               if isinstance(existing_layers, dict) and k in existing_layers]
    if isinstance(existing_orders, dict) and "sticker" in existing_orders:
        clashes.append("image.composition_orders.sticker")
    if clashes:
        print(f"WARN: merging these fragments REPLACES keys the config already "
              f"defines (YAML duplicate keys are last-wins): {', '.join(clashes)}",
              file=sys.stderr)
    new_text = (f"# Sticker prompts — generated by tools/migrate_stickers.py from "
                f"{legacy_rel}/{legacy_path.name}.\n"
                f"# Merge the two fragments the tool printed into image.layers: and "
                f"image.composition_orders: in\n"
                f"# .blog-craft.yaml, then set features.stickers.enabled: true.\n"
                + dump({"images": items}))
    todo = plan_moves(legacy_dir, root, stk) if a.move_assets else []

    old_text = dest.read_text() if dest.is_file() else ""
    if old_text == new_text:
        print(f"{stk['prompts_file']}: unchanged ({len(items)} entries)")
    else:
        rel = stk["prompts_file"]
        sys.stdout.writelines(difflib.unified_diff(
            old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
            fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        if a.dry_run:
            print(f"\n--dry-run: would write {len(items)} entries to {rel}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if old_text:
                backup = dest.with_suffix(dest.suffix + ".bak")
                backup.write_text(old_text)
                print(f"backed up the previous {rel} -> {backup.name}")
            dest.write_text(new_text)
            print(f"wrote {len(items)} entries to {rel}")

    for src, dst in todo:
        if a.dry_run:
            print(f"--dry-run: would move {src} -> {dst}")
        else:
            move(src, dst)

    print(f"\n{PASTE_BEGIN}\n"
          f"{ORDERS_MARK}\n{fragment(block['composition_orders'])}"
          f"{LAYERS_MARK}\n{fragment(block['layers'])}{PASTE_END}")
    if reuse_clothing:
        print(CLOTHING_KEPT_NOTE)
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="path to the blog's .blog-craft.yaml")
    ap.add_argument("--legacy", required=True, help="path to the legacy stickers.yaml")
    ap.add_argument("--move-assets", action="store_true",
                    help="git mv images/ and sheets/ to the configured dirs")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the diff and the planned moves; write nothing")
    a = ap.parse_args(argv)
    try:
        return _run(a)
    except Fail as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
