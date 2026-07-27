"""P4 — seed_config.py dotted-key (nested) seeding for quality.lint.enabled.

The spec's config-seeding contract: `quality.lint` seeded when absent,
untouched when present. /blog-post Step 0 runs
`seed_config.py --key quality.lint.enabled --default true`, so seed_key must
create the real nested block the validator reads
(cfg["quality"]["lint"]["enabled"]) — not a flat literal
"quality.lint.enabled" top-level key — and the value must be a boolean.
"""
import yaml

from seed_config import seed_key  # tools/ on sys.path via conftest


def _write(path, text):
    path.write_text(text)
    return path


def test_seeds_nested_quality_lint_enabled_when_absent(tmp_path):
    cfg_path = _write(tmp_path / ".blog-craft.yaml", "site_dir: .\nvoice_level: dry\n")
    seeded = seed_key(
        cfg_path,
        "quality.lint.enabled",
        "true",
        comment="Warnings-first AI-tells lint; severities/thresholds in docs/CONFIG.md.",
        values="true,false",
    )
    assert seeded is True
    data = yaml.safe_load(cfg_path.read_text())
    assert data["quality"]["lint"]["enabled"] is True  # nested AND boolean
    assert "quality.lint.enabled" not in data  # no flat literal key
    assert "Warnings-first AI-tells lint" in cfg_path.read_text()


def test_untouched_when_nested_key_present(tmp_path):
    original = "site_dir: .\nquality:\n  lint:\n    enabled: false\n"
    cfg_path = _write(tmp_path / ".blog-craft.yaml", original)
    seeded = seed_key(cfg_path, "quality.lint.enabled", "true")
    assert seeded is False
    assert cfg_path.read_text() == original  # byte-for-byte untouched


def test_partial_path_extends_existing_quality_block(tmp_path):
    cfg_path = _write(
        tmp_path / ".blog-craft.yaml",
        "site_dir: .\nquality:\n  gate:\n    require_commands: true\n",
    )
    seeded = seed_key(cfg_path, "quality.lint.enabled", "true")
    assert seeded is True
    data = yaml.safe_load(cfg_path.read_text())
    assert data["quality"]["lint"]["enabled"] is True
    assert data["quality"]["gate"]["require_commands"] is True  # preserved
    assert cfg_path.read_text().count("quality:") == 1  # no duplicate block


def test_top_level_flat_key_unchanged_behavior(tmp_path):
    cfg_path = _write(tmp_path / ".blog-craft.yaml", "site_dir: .\n")
    seeded = seed_key(
        cfg_path, "voice_level", "balanced",
        comment="How thick the persona frame is.", values="dry,balanced,rich",
    )
    assert seeded is True
    data = yaml.safe_load(cfg_path.read_text())
    assert data["voice_level"] == "balanced"
    assert seed_key(cfg_path, "voice_level", "balanced") is False
