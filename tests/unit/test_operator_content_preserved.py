"""/update and the migration ladder must not destroy operator-owned content.

Two independent defects, one invariant — a file the operator is expected to
edit is never rewritten wholesale:

  * #73 — `migrate_config.py` round-tripped `.blog-craft.yaml` (a `content`
    path) through `yaml.safe_load` -> `yaml.safe_dump(sort_keys=True)`, deleting
    every comment (including load-bearing warnings) and alphabetising every key.
    A two-key migration became a 500-line diff nobody could review.
  * #83 — `.gitignore` was classified `framework`, so every `--apply` replaced
    it and silently dropped operator-added rules (`*.bak`, `.DS_Store`).
"""
import difflib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from migrate_config import upgrade
from path_ownership import classify
from update import apply_plan, default_manifest, plan_update

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "migrate_config.py")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _migrate(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, TOOL, str(path)], capture_output=True, text=True)


# --- #73: migrate_config keeps comments, key order and quoting ----------------

V6 = """\
# Operator header — why this blog is configured the way it is.
version: 6
blog_craft_version: "v0.18.1"   # update.py re-renders AT this tag — bump AFTER an apply

project:
  name: "Zed"        # slug: drives the read-tracker storage key
  title: Zed's Blog

# Deliberately unsorted: zeta before alpha.
zeta: 1
alpha: 2
features:
  mermaid_view: false   # explicit opt-out; a migration must keep it
"""


def test_migration_changes_only_the_migrated_lines(tmp_path):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(V6)
    r = _migrate(cfg)
    assert r.returncode == 0, r.stderr
    new = cfg.read_text()
    removed = [l for l in difflib.ndiff(V6.splitlines(), new.splitlines()) if l.startswith("- ")]
    added = [l for l in difflib.ndiff(V6.splitlines(), new.splitlines()) if l.startswith("+ ")]
    # 006 -> 007 bumps the version and seeds features.stickers — nothing else moves.
    assert removed == ["- version: 6"], new
    assert added[0] == "+ version: 7", new
    assert all("stickers" in l or "enabled" in l for l in added[1:]), new


def test_migration_result_parses_to_what_the_ladder_computes(tmp_path):
    """Parity: preserving the text must not change the semantics (#73's workaround)."""
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(V6)
    _migrate(cfg)
    assert yaml.safe_load(cfg.read_text()) == upgrade(yaml.safe_load(V6))


def test_multi_rung_migration_keeps_every_comment_and_top_level_order(tmp_path):
    """frank's real-shape config, v2 -> latest: five rungs, comments intact."""
    src = Path(FIX) / "frank.blog-craft.yaml"
    cfg = tmp_path / ".blog-craft.yaml"
    shutil.copy(src, cfg)
    original = src.read_text()
    r = _migrate(cfg)
    assert r.returncode == 0, r.stderr
    new = cfg.read_text()
    assert yaml.safe_load(new) == upgrade(yaml.safe_load(original))
    # Byte-level: the ONLY original lines allowed to go are the two the ladder
    # rewrites (the version, and 001->002's composition_order -> composition_orders
    # rename). Flow maps, alignment padding, inline comments, block scalars and
    # indentation everywhere else are the operator's and must survive verbatim.
    diff = list(difflib.ndiff(original.splitlines(), new.splitlines()))
    removed = [l[2:] for l in diff if l.startswith("- ")]
    assert removed == [
        "version: 2",
        "  composition_order: [base_character, base_atmosphere, reference_guidance, torso, mood, scene]",
    ], new
    # ...and nothing added but the migrated keys: no comment printed twice, no
    # stray blank line (ruamel relocates a mapping's trailing comment).
    added = [l[2:] for l in diff if l.startswith("+ ")]
    assert not [l for l in added if not l.strip() or l.lstrip().startswith("#")], new
    orig_keys = list(yaml.safe_load(original))
    assert [k for k in yaml.safe_load(new) if k in orig_keys] == orig_keys   # not alphabetised


def test_migration_leaves_a_backup_of_the_exact_original(tmp_path):
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(V6)
    _migrate(cfg)
    assert (tmp_path / ".blog-craft.yaml.bak").read_text() == V6


def test_keep_chomped_block_scalar_value_survives(tmp_path):
    """A `|+` scalar's trailing blank lines are CONTENT, not section spacing.

    The splice moves a mapping's trailing blank lines after appended keys; for a
    keep-chomped last value that would change the value. The parity guard must
    catch it, so the written config always parses to what the ladder computed.
    """
    text = "version: 6\nfeatures:\n  mermaid_view: true\n  note: |+\n    keep me\n\n\nvoice: x\n"
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(text)
    assert _migrate(cfg).returncode == 0
    assert yaml.safe_load(cfg.read_text()) == upgrade(yaml.safe_load(text))


def test_missing_ruamel_writes_nothing(tmp_path, monkeypatch, capsys):
    """Without ruamel the tool refuses loudly — it never falls back to the lossy dump."""
    import migrate_config
    monkeypatch.setitem(sys.modules, "ruamel", None)       # `import ruamel.yaml` -> ImportError
    cfg = tmp_path / ".blog-craft.yaml"
    cfg.write_text(V6)
    assert migrate_config._main([str(cfg)]) == 2
    assert "ruamel.yaml" in capsys.readouterr().err
    assert cfg.read_text() == V6
    assert not (tmp_path / ".blog-craft.yaml.bak").exists()


# --- #83: .gitignore is merged, so operator rules survive /update -------------

M = default_manifest()


def test_gitignore_is_merged_not_framework():
    assert classify(".gitignore", M) == "merged"


def _mk(root: Path, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


SHIPPED_OLD = "public/\nresources/\n.env\n__pycache__/\n\n# Image curation\n.regen-archive/\n"


def test_update_keeps_operator_gitignore_rules_and_ships_new_ones(tmp_path):
    shipped_new = SHIPPED_OLD.replace("resources/\n", "resources/\n.hugo_build.lock\n")
    _mk(tmp_path / "base", {".gitignore": SHIPPED_OLD})
    _mk(tmp_path / "stg", {".gitignore": shipped_new})
    _mk(tmp_path / "blog", {".gitignore": SHIPPED_OLD + "\n*.bak\n.DS_Store\n"})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M)
    assert [(e["path"], e["action"]) for e in plan] == [(".gitignore", "merge")]
    assert apply_plan(tmp_path / "blog", tmp_path / "stg", plan) == []
    out = (tmp_path / "blog" / ".gitignore").read_text()
    assert "*.bak" in out and ".DS_Store" in out          # operator rules kept
    assert ".hugo_build.lock" in out                       # shipped rule delivered


def test_gitignore_clash_is_a_conflict_that_keeps_the_operator_file(tmp_path):
    """Shipped and operator lines touching the same spot: surfaced, never dropped."""
    blog = SHIPPED_OLD + "*.bak\n"
    _mk(tmp_path / "base", {".gitignore": SHIPPED_OLD})
    _mk(tmp_path / "stg", {".gitignore": SHIPPED_OLD + "node_modules/\n"})
    _mk(tmp_path / "blog", {".gitignore": blog})
    plan = plan_update(tmp_path / "blog", tmp_path / "stg", tmp_path / "base", M)
    assert [(e["path"], e["action"]) for e in plan] == [(".gitignore", "conflict")]
    assert apply_plan(tmp_path / "blog", tmp_path / "stg", plan) == [".gitignore"]
    assert (tmp_path / "blog" / ".gitignore").read_text() == blog
