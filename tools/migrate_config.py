#!/usr/bin/env python3
"""Schema-migration ladder runner (spec §8.1).

Discovers migrations/NNN_to_MMM.py, applies them in order from a config's
`version:` up to the latest, purely and idempotently. Non-destructive: the CLI
writes a `.bak` and only rewrites the config when something changed.

The config is operator-owned (`content` in the manifest), so the rewrite is
SURGICAL (#73): migrations still run on a plain dict, and only the difference
is applied onto a ruamel.yaml round-trip document — comments, key order,
quoting and indentation of every untouched line survive. A PyYAML
load -> dump used to delete every comment (load-bearing warnings included) and
alphabetise every key, turning a two-key migration into an unreviewable diff.

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


# --- surgical rewrite (#73) ---------------------------------------------------
# ruamel's round-trip keeps comments and key order, but it still re-emits every
# node: flow maps lose their padding (`{ a: 1 }` -> `{a: 1}`), multi-line flow
# maps are joined, alignment goes. So ruamel only RENDERS the migrated document;
# the result is then spliced key by key — every key whose value the migration
# left alone gets the operator's ORIGINAL lines back, recursing into changed
# block mappings, so only the keys a migration actually touched are re-rendered.

def _same(a, b) -> bool:
    # bool apart: True == 1. (A type() check would also flag every quoted
    # scalar, which ruamel loads as a str subclass.)
    return a == b and isinstance(a, bool) == isinstance(b, bool)


def _apply_onto(doc, new):
    """Make round-trip mapping `doc` equal `new` in place, touching only what differs."""
    for k in [k for k in doc if k not in new]:
        del doc[k]
    for k, v in new.items():
        if k in doc and isinstance(doc[k], dict) and isinstance(v, dict):
            _apply_onto(doc[k], v)
        elif k not in doc or not _same(doc[k], v):
            doc[k] = v


def _is_block_map(node) -> bool:
    from ruamel.yaml.comments import CommentedMap
    return isinstance(node, CommentedMap) and len(node) > 0 and not node.fa.flow_style()


def _spans(node, end: int) -> dict:
    """key -> [first line, end line) of that key's region inside a block mapping."""
    starts = [node.lc.key(k)[0] for k in node]
    return {k: (s, e) for k, s, e in zip(node, starts, starts[1:] + [end])}


def _splice(o_lines, o_node, o_end, r_lines, r_node, r_end, old, new) -> list:
    o_sp, r_sp = _spans(o_node, o_end), _spans(r_node, r_end)
    # Blank lines / outdented comments closing the original region separate it
    # from what follows; they stay at the END even when a key is appended.
    last = list(o_node)[-1]
    s, t = o_sp[last]
    col = o_node.lc.key(last)[1]
    while t > s + 1 and (not o_lines[t - 1].strip() or (
            o_lines[t - 1].lstrip().startswith("#")
            and len(o_lines[t - 1]) - len(o_lines[t - 1].lstrip()) < col)):
        t -= 1
    tail, o_sp[last] = o_lines[t:o_sp[last][1]], (s, t)

    out = []
    for k in r_node:
        if k in o_sp and k in old and _same(old[k], new[k]):
            out += o_lines[slice(*o_sp[k])]
        elif (k in o_sp and isinstance(old.get(k), dict)
              and _is_block_map(o_node[k]) and _is_block_map(r_node[k])):
            s, e = o_sp[k]
            first_child = o_node[k].lc.key(next(iter(o_node[k])))[0]
            out += o_lines[s:first_child]                 # the key line, its comment
            out += _splice(o_lines, o_node[k], e, r_lines, r_node[k], r_sp[k][1],
                           old[k], new[k])
        else:
            s, e = r_sp[k]
            if k not in o_sp:
                # A NEW key has no comments of its own; ruamel parks the mapping's
                # trailing comment after the last key, which may now be this one.
                # The original span above already kept it — don't print it twice.
                while e > s + 1 and (not r_lines[e - 1].strip()
                                     or r_lines[e - 1].lstrip().startswith("#")):
                    e -= 1
            out += r_lines[s:e]
    return out + tail


def _indents(doc, lines) -> tuple[int, int]:
    """(mapping indent, block-sequence dash offset) the operator's file uses."""
    from ruamel.yaml.comments import CommentedSeq
    mapping = offset = None
    stack = [(doc, 0)]
    while stack and (mapping is None or offset is None):
        node, col = stack.pop()
        if not _is_block_map(node):
            continue
        for k, v in node.items():
            if _is_block_map(v):
                mapping = mapping or v.lc.key(next(iter(v)))[1] - col
                stack.append((v, v.lc.key(next(iter(v)))[1]))
            elif isinstance(v, CommentedSeq) and v and not v.fa.flow_style() and offset is None:
                line = lines[v.lc.item(0)[0]]
                offset = line.index("-") - col if "-" in line else None
    return mapping or 2, offset or 0


def _rewrite(text: str, old: dict, upgraded: dict) -> str:
    """`text` with `upgraded` applied surgically (see the block comment above)."""
    import io
    from ruamel.yaml import YAML
    rt = YAML(typ="rt")
    rt.preserve_quotes = True
    rt.width = 4096                       # never re-wrap an operator's long lines
    doc = rt.load(text)
    lines = text.splitlines(keepends=True)
    mapping, offset = _indents(doc, lines)
    rt.indent(mapping=mapping, sequence=offset + 2, offset=offset)
    _apply_onto(doc, upgraded)
    buf = io.StringIO()
    rt.dump(doc, buf)
    rendered = buf.getvalue()
    if not _is_block_map(doc):
        return rendered
    o_doc = rt.load(text)
    r_doc = rt.load(rendered)
    r_lines = rendered.splitlines(keepends=True)
    head = lines[:o_doc.lc.key(next(iter(o_doc)))[0]]    # comments above the first key
    spliced = "".join(head + _splice(lines, o_doc, len(lines), r_lines, r_doc,
                                     len(r_lines), old, upgraded))
    # Parity guard: the splice works on lines, so a YAML corner it does not model
    # (e.g. a trailing `|+` block scalar) could shift a value. Never ship that —
    # fall back to ruamel's whole render, which still keeps comments and order.
    import yaml
    try:
        if yaml.safe_load(spliced) == upgraded:
            return spliced
    except yaml.YAMLError:
        pass
    return rendered


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
    text = path.read_text()
    try:
        # a FRESH parse as the "before": migrations shallow-copy, so `cfg` itself
        # may share nested objects with `upgraded` and hide a change
        new_text = _rewrite(text, yaml.safe_load(text), upgraded)
    except ImportError:
        print("migrate_config needs ruamel.yaml to rewrite the config without losing its "
              "comments: pip install ruamel.yaml  (nothing was written)", file=sys.stderr)
        return 2
    path.with_suffix(path.suffix + ".bak").write_text(text)  # non-destructive
    path.write_text(new_text)
    print(f"upgraded v{cfg.get('version')} -> v{upgraded.get('version')} (backup: {path.name}.bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
