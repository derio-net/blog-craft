"""blog-craft installs under its OWN marketplace name, never `derio-net`.

Root cause (super-fr PR #392 / its debug journal
2026-07-23-marketplace-config-clobber): a Claude Code marketplace name is a 1:1
namespace over ONE source repo.  Its manifest at
`~/.claude/plugins/marketplaces/<name>/.claude-plugin/marketplace.json` is a
single file listing every plugin of that marketplace, and every installer
populates it with `rsync -a --delete <own repo root>/` — replace, never merge.

blog-craft's installer used to claim `derio-net`, the name the sibling
super-fr repo owns (super-fr's manifest declares `"name": "derio-net"`; ours
declares `"name": "blog-craft"`).  Both rsync'd into the same directory, so
whichever installer ran last evicted the other's plugins from the manifest
while their `enabledPlugins` / `installed_plugins.json` entries survived as
dangling references.  blog-craft is the party in the wrong and moves to
`blog-craft` — the name it already declares.

Two invariants pinned here, and the migration off the squat:

- write the keys you OWN unconditionally (skip-if-present means
  first-writer-wins, so a stale wrong source survives every reinstall);
- delete only the keys you own — `--uninstall` must never remove the shared
  `derio-net` marketplace, which would deregister super-fr too.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"

MARKETPLACE_NAME = "blog-craft"
PLUGIN_ID = "blog-craft@blog-craft"
SQUATTED_NAME = "derio-net"
SQUATTED_PLUGIN_ID = "blog-craft@derio-net"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("rsync") is None,
    reason="install.sh hard-requires jq and rsync",
)


def _manifest() -> dict:
    return json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())


@pytest.fixture()
def fake_home(tmp_path: Path) -> Path:
    """A HOME with the plugin JSON files install.sh reads and rewrites."""
    home = tmp_path / "home"
    plugins = home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "installed_plugins.json").write_text(json.dumps({"plugins": {}, "version": 2}))
    (plugins / "known_marketplaces.json").write_text(json.dumps({}))
    (home / ".claude" / "settings.json").write_text(json.dumps({}))
    return home


def _run_install(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    result = subprocess.run(
        ["bash", str(INSTALL_SH), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"install.sh {' '.join(args)} failed (rc={result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return result


def _known(home: Path) -> dict:
    return json.loads((home / ".claude" / "plugins" / "known_marketplaces.json").read_text())


def _settings(home: Path) -> dict:
    return json.loads((home / ".claude" / "settings.json").read_text())


def _installed(home: Path) -> dict:
    return json.loads((home / ".claude" / "plugins" / "installed_plugins.json").read_text())


def _seed_super_fr(home: Path) -> None:
    """Pre-seed the machine as if super-fr's installer had already run."""
    plugins = home / ".claude" / "plugins"
    (plugins / "known_marketplaces.json").write_text(
        json.dumps(
            {
                SQUATTED_NAME: {
                    "source": {"source": "github", "repo": "derio-net/super-fr"},
                    "installLocation": str(plugins / "marketplaces" / SQUATTED_NAME),
                }
            }
        )
    )
    (home / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "extraKnownMarketplaces": {
                    SQUATTED_NAME: {
                        "source": {"source": "github", "repo": "derio-net/super-fr"}
                    }
                },
                "enabledPlugins": {
                    "super-fr@derio-net": True,
                    "super-fr-dispatch@derio-net": True,
                },
            }
        )
    )
    (plugins / "installed_plugins.json").write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "super-fr@derio-net": [
                        {
                            "scope": "user",
                            "installPath": str(
                                plugins / "cache" / SQUATTED_NAME / "super-fr" / "current"
                            ),
                            "version": "3.12.1",
                        }
                    ]
                },
            }
        )
    )
    manifest = (
        plugins / "marketplaces" / SQUATTED_NAME / ".claude-plugin" / "marketplace.json"
    )
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "name": SQUATTED_NAME,
                "plugins": [{"name": "super-fr", "version": "3.12.1", "source": "./"}],
            }
        )
    )


# ── We install under our own name ─────────────────────────────────────


class TestOwnMarketplaceName:
    def test_manifest_name_is_what_we_register(self) -> None:
        """The registry key must match the name our own manifest declares —
        the self-consistency whose absence caused the collision."""
        assert _manifest()["name"] == MARKETPLACE_NAME

    def test_registers_its_own_marketplace_key(self, fake_home: Path) -> None:
        _run_install(fake_home)

        entry = _known(fake_home)[MARKETPLACE_NAME]
        assert entry["source"]["repo"] == "derio-net/blog-craft"
        assert entry["installLocation"].endswith(f"/marketplaces/{MARKETPLACE_NAME}")

        source = _settings(fake_home)["extraKnownMarketplaces"][MARKETPLACE_NAME]["source"]
        assert source["repo"] == "derio-net/blog-craft"

    def test_never_creates_a_derio_net_marketplace(self, fake_home: Path) -> None:
        _run_install(fake_home)

        assert SQUATTED_NAME not in _known(fake_home), (
            "blog-craft must not register the marketplace name super-fr owns"
        )
        assert SQUATTED_NAME not in _settings(fake_home).get("extraKnownMarketplaces", {})

    def test_plugin_id_is_namespaced_to_our_marketplace(self, fake_home: Path) -> None:
        _run_install(fake_home)

        assert PLUGIN_ID in _installed(fake_home)["plugins"]
        assert SQUATTED_PLUGIN_ID not in _installed(fake_home)["plugins"]
        assert _settings(fake_home)["enabledPlugins"][PLUGIN_ID] is True
        assert SQUATTED_PLUGIN_ID not in _settings(fake_home)["enabledPlugins"]

    def test_writes_its_tree_into_its_own_marketplace_dir(self, fake_home: Path) -> None:
        _run_install(fake_home)

        plugins = fake_home / ".claude" / "plugins"
        manifest = (
            plugins / "marketplaces" / MARKETPLACE_NAME / ".claude-plugin" / "marketplace.json"
        )
        assert manifest.exists()
        assert json.loads(manifest.read_text())["name"] == MARKETPLACE_NAME
        assert not (plugins / "marketplaces" / SQUATTED_NAME).exists()
        assert (plugins / "cache" / MARKETPLACE_NAME / "blog-craft" / "current").is_symlink()
        assert not (plugins / "cache" / SQUATTED_NAME).exists()


# ── We do not disturb super-fr's namespace ────────────────────────────


class TestLeavesSuperFrAlone:
    def test_install_preserves_the_derio_net_marketplace(self, fake_home: Path) -> None:
        _seed_super_fr(fake_home)

        _run_install(fake_home)

        known = _known(fake_home)
        assert known[SQUATTED_NAME]["source"]["repo"] == "derio-net/super-fr"
        settings = _settings(fake_home)
        assert (
            settings["extraKnownMarketplaces"][SQUATTED_NAME]["source"]["repo"]
            == "derio-net/super-fr"
        )
        assert settings["enabledPlugins"]["super-fr@derio-net"] is True
        assert "super-fr@derio-net" in _installed(fake_home)["plugins"]

    def test_install_does_not_touch_super_frs_marketplace_tree(self, fake_home: Path) -> None:
        _seed_super_fr(fake_home)
        manifest = (
            fake_home
            / ".claude"
            / "plugins"
            / "marketplaces"
            / SQUATTED_NAME
            / ".claude-plugin"
            / "marketplace.json"
        )

        _run_install(fake_home)

        data = json.loads(manifest.read_text())
        assert data["name"] == SQUATTED_NAME
        assert [p["name"] for p in data["plugins"]] == ["super-fr"]

    def test_uninstall_removes_only_our_keys(self, fake_home: Path) -> None:
        """The old `--uninstall` ran `del(."derio-net")` on both registries,
        deregistering super-fr along with blog-craft."""
        _seed_super_fr(fake_home)
        _run_install(fake_home)

        _run_install(fake_home, "--uninstall")

        known = _known(fake_home)
        assert SQUATTED_NAME in known, (
            "uninstalling blog-craft must not deregister the derio-net marketplace"
        )
        assert known[SQUATTED_NAME]["source"]["repo"] == "derio-net/super-fr"
        assert MARKETPLACE_NAME not in known

        settings = _settings(fake_home)
        assert SQUATTED_NAME in settings["extraKnownMarketplaces"]
        assert MARKETPLACE_NAME not in settings["extraKnownMarketplaces"]
        assert settings["enabledPlugins"]["super-fr@derio-net"] is True
        assert PLUGIN_ID not in settings["enabledPlugins"]

    def test_uninstall_leaves_super_fr_plugin_registration(self, fake_home: Path) -> None:
        _seed_super_fr(fake_home)
        _run_install(fake_home)

        _run_install(fake_home, "--uninstall")

        installed = _installed(fake_home)["plugins"]
        assert "super-fr@derio-net" in installed
        assert PLUGIN_ID not in installed


# ── Migration off the squat ───────────────────────────────────────────


class TestMigratesOffTheSquat:
    """Machines that ran the old installer carry `blog-craft@derio-net`
    registrations pointing into super-fr's namespace.  Those are OUR litter in
    someone else's yard: we clean them up, and only them."""

    def _seed_squat(self, home: Path) -> None:
        _seed_super_fr(home)
        plugins = home / ".claude" / "plugins"

        installed = _installed(home)
        installed["plugins"][SQUATTED_PLUGIN_ID] = [
            {
                "scope": "user",
                "installPath": str(
                    plugins / "cache" / SQUATTED_NAME / "blog-craft" / "current"
                ),
                "version": "0.10.0",
            }
        ]
        (plugins / "installed_plugins.json").write_text(json.dumps(installed))

        settings = _settings(home)
        settings["enabledPlugins"][SQUATTED_PLUGIN_ID] = True
        (home / ".claude" / "settings.json").write_text(json.dumps(settings))

        stale_cache = plugins / "cache" / SQUATTED_NAME / "blog-craft" / "0.10.0"
        stale_cache.mkdir(parents=True)
        (stale_cache / "marker").write_text("stale")

    def test_drops_the_stale_plugin_registration(self, fake_home: Path) -> None:
        self._seed_squat(fake_home)

        _run_install(fake_home)

        assert SQUATTED_PLUGIN_ID not in _installed(fake_home)["plugins"]
        assert SQUATTED_PLUGIN_ID not in _settings(fake_home)["enabledPlugins"]
        assert PLUGIN_ID in _installed(fake_home)["plugins"]

    def test_drops_the_stale_cache_under_derio_net(self, fake_home: Path) -> None:
        self._seed_squat(fake_home)

        _run_install(fake_home)

        stale = fake_home / ".claude" / "plugins" / "cache" / SQUATTED_NAME / "blog-craft"
        assert not stale.exists(), "our old cache under derio-net must be removed"

    def test_migration_spares_super_frs_own_entries(self, fake_home: Path) -> None:
        self._seed_squat(fake_home)
        super_fr_cache = (
            fake_home / ".claude" / "plugins" / "cache" / SQUATTED_NAME / "super-fr" / "3.12.1"
        )
        super_fr_cache.mkdir(parents=True)

        _run_install(fake_home)

        assert super_fr_cache.exists()
        assert "super-fr@derio-net" in _installed(fake_home)["plugins"]
        assert SQUATTED_NAME in _known(fake_home)

    def test_migration_is_idempotent(self, fake_home: Path) -> None:
        self._seed_squat(fake_home)

        _run_install(fake_home)
        _run_install(fake_home)

        assert SQUATTED_PLUGIN_ID not in _installed(fake_home)["plugins"]
        assert PLUGIN_ID in _installed(fake_home)["plugins"]


# ── Own your key: converge, don't skip ────────────────────────────────


class TestRegistryWriteIsUnconditional:
    """`if ! jq -e '."<key>"'` reads as idempotence but means
    first-writer-wins: a wrong `source.repo` left by anyone else survives every
    reinstall, and `/plugin marketplace update <key>` then re-fetches the wrong
    repo.  Converge on our value instead."""

    def test_corrects_a_wrong_source_on_our_own_key(self, fake_home: Path) -> None:
        plugins = fake_home / ".claude" / "plugins"
        (plugins / "known_marketplaces.json").write_text(
            json.dumps(
                {
                    MARKETPLACE_NAME: {
                        "source": {"source": "directory", "path": "/stale/checkout"},
                        "installLocation": "/stale/checkout",
                    }
                }
            )
        )
        (fake_home / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "extraKnownMarketplaces": {
                        MARKETPLACE_NAME: {
                            "source": {"source": "directory", "path": "/stale/checkout"}
                        }
                    }
                }
            )
        )

        _run_install(fake_home)

        entry = _known(fake_home)[MARKETPLACE_NAME]
        assert entry["source"] == {"source": "github", "repo": "derio-net/blog-craft"}
        assert entry["installLocation"].endswith(f"/marketplaces/{MARKETPLACE_NAME}")
        assert _settings(fake_home)["extraKnownMarketplaces"][MARKETPLACE_NAME]["source"] == {
            "source": "github",
            "repo": "derio-net/blog-craft",
        }
