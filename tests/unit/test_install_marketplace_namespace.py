"""A marketplace name is `<org>--<repo>`, and bare names are retired.

Root cause (super-fr PR #392, and
docs/superpowers/journals/debug/2026-07-23-marketplace-namespace-collision.md):
a Claude Code marketplace name is a 1:1 namespace over ONE source repo.  Its
manifest at `~/.claude/plugins/marketplaces/<name>/.claude-plugin/marketplace.json`
is a single file listing every plugin of that marketplace, and every installer
populates it with `rsync -a --delete <own repo root>/` — replace, never merge.

blog-craft's installer claimed the bare org name `derio-net`, which the sibling
super-fr repo also claimed.  Both rsync'd into the same directory, so whichever
ran last evicted the other's plugins from the manifest while their
`enabledPlugins` / `installed_plugins.json` entries survived as dangling
references.

The bare name is retired rather than awarded to a winner: blog-craft installs
as `derio-net--blog-craft`, super-fr as `derio-net--super-fr`, and both
installers purge `derio-net` on sight.  With no owner left, every `*@derio-net`
id is dangling by definition — so purging the whole key is safe by
construction, not one repo reaching into another's install state.

Pinned here: installing under our own `<org>--<repo>` name, unconditional
convergence of the keys we own, the bare-name purge (including our own older
`blog-craft` marketplace), and an `--uninstall` that removes only our plugin
ids and our marketplace — never a sibling's.
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

MARKETPLACE_NAME = "derio-net--blog-craft"
PLUGIN_ID = f"blog-craft@{MARKETPLACE_NAME}"
RETIRED_NAMES = ("derio-net", "blog-craft")

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


def _seed_legacy(home: Path) -> None:
    """Pre-seed a machine as the old installers left it: our squat inside the
    shared `derio-net` namespace, our older bare `blog-craft` marketplace, a
    sibling's registrations, and an unrelated third-party marketplace."""
    plugins = home / ".claude" / "plugins"
    (plugins / "known_marketplaces.json").write_text(
        json.dumps(
            {
                "derio-net": {
                    "source": {"source": "github", "repo": "derio-net/super-fr"},
                    "installLocation": str(plugins / "marketplaces" / "derio-net"),
                },
                "blog-craft": {
                    "source": {"source": "directory", "path": "/checkouts/blog-craft"},
                    "installLocation": "/checkouts/blog-craft",
                },
                "thedotmack": {
                    "source": {"source": "github", "repo": "thedotmack/claude-mem"},
                    "installLocation": "/elsewhere/thedotmack",
                },
            }
        )
    )
    (home / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "extraKnownMarketplaces": {
                    "derio-net": {"source": {"source": "github", "repo": "derio-net/super-fr"}},
                    "blog-craft": {
                        "source": {"source": "directory", "path": "/checkouts/blog-craft"}
                    },
                    "thedotmack": {
                        "source": {"source": "github", "repo": "thedotmack/claude-mem"}
                    },
                },
                "enabledPlugins": {
                    "blog-craft@derio-net": True,
                    "blog-craft@blog-craft": True,
                    "super-fr@derio-net": True,
                    "claude-mem@thedotmack": True,
                },
            }
        )
    )
    (plugins / "installed_plugins.json").write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "blog-craft@derio-net": [{"scope": "user", "version": "0.10.0"}],
                    "blog-craft@blog-craft": [{"scope": "user", "version": "0.1.0"}],
                    "super-fr@derio-net": [{"scope": "user", "version": "3.12.0"}],
                    "claude-mem@thedotmack": [{"scope": "user", "version": "10.6.3"}],
                },
            }
        )
    )
    for name in RETIRED_NAMES:
        (plugins / "cache" / name / "blog-craft" / "0.1.0").mkdir(parents=True)
    manifest = plugins / "marketplaces" / "derio-net" / ".claude-plugin" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "blog-craft", "plugins": []}))


# ── The name encodes org AND repo ─────────────────────────────────────


def test_manifest_name_encodes_org_and_repo() -> None:
    """A bare name — org OR repo — is a namespace another repo can also claim,
    which is exactly how the eviction happened."""
    assert _manifest()["name"] == MARKETPLACE_NAME
    script = INSTALL_SH.read_text()
    assert f'MARKETPLACE_NAME="{MARKETPLACE_NAME}"' in script


class TestInstallsUnderOwnName:
    def test_registers_its_own_marketplace_key(self, fake_home: Path) -> None:
        _run_install(fake_home)

        entry = _known(fake_home)[MARKETPLACE_NAME]
        assert entry["source"] == {"source": "github", "repo": "derio-net/blog-craft"}
        assert entry["installLocation"].endswith(f"/marketplaces/{MARKETPLACE_NAME}")

        source = _settings(fake_home)["extraKnownMarketplaces"][MARKETPLACE_NAME]["source"]
        assert source == {"source": "github", "repo": "derio-net/blog-craft"}

    def test_plugin_id_is_namespaced_to_our_marketplace(self, fake_home: Path) -> None:
        _run_install(fake_home)

        assert PLUGIN_ID in _installed(fake_home)["plugins"]
        assert _settings(fake_home)["enabledPlugins"][PLUGIN_ID] is True

    def test_writes_its_tree_into_its_own_marketplace_dir(self, fake_home: Path) -> None:
        _run_install(fake_home)

        plugins = fake_home / ".claude" / "plugins"
        manifest = (
            plugins / "marketplaces" / MARKETPLACE_NAME / ".claude-plugin" / "marketplace.json"
        )
        assert json.loads(manifest.read_text())["name"] == MARKETPLACE_NAME
        assert (plugins / "cache" / MARKETPLACE_NAME / "blog-craft" / "current").is_symlink()

    def test_never_writes_a_bare_marketplace_name(self, fake_home: Path) -> None:
        _run_install(fake_home)

        plugins = fake_home / ".claude" / "plugins"
        known = _known(fake_home)
        extra = _settings(fake_home)["extraKnownMarketplaces"]
        for name in RETIRED_NAMES:
            assert name not in known
            assert name not in extra
            assert not (plugins / "marketplaces" / name).exists()
            assert not (plugins / "cache" / name).exists()


class TestRegistryWriteIsUnconditional:
    """`if ! jq -e '."<key>"'` reads as idempotence but means first-writer-wins:
    a wrong `source.repo` on our own key survives every reinstall."""

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

        _run_install(fake_home)

        entry = _known(fake_home)[MARKETPLACE_NAME]
        assert entry["source"] == {"source": "github", "repo": "derio-net/blog-craft"}
        assert entry["installLocation"].endswith(f"/marketplaces/{MARKETPLACE_NAME}")


# ── The retired bare names are purged on sight ────────────────────────


class TestRetiresBareMarketplaceNames:
    def test_removes_both_retired_marketplaces(self, fake_home: Path) -> None:
        _seed_legacy(fake_home)

        _run_install(fake_home)

        known = _known(fake_home)
        extra = _settings(fake_home)["extraKnownMarketplaces"]
        for name in RETIRED_NAMES:
            assert name not in known, f"{name} marketplace must be retired"
            assert name not in extra

    def test_removes_the_retired_directories_and_caches(self, fake_home: Path) -> None:
        _seed_legacy(fake_home)
        plugins = fake_home / ".claude" / "plugins"

        _run_install(fake_home)

        for name in RETIRED_NAMES:
            assert not (plugins / "marketplaces" / name).exists()
            assert not (plugins / "cache" / name).exists()

    def test_drops_every_retired_plugin_id_including_a_siblings(
        self, fake_home: Path
    ) -> None:
        _seed_legacy(fake_home)

        _run_install(fake_home)

        installed = _installed(fake_home)["plugins"]
        enabled = _settings(fake_home)["enabledPlugins"]
        for stale in ("blog-craft@derio-net", "blog-craft@blog-craft", "super-fr@derio-net"):
            assert stale not in installed, f"{stale} must be purged from installed_plugins"
            assert stale not in enabled, f"{stale} must be purged from enabledPlugins"
        assert PLUGIN_ID in installed

    def test_reports_what_it_purged_and_flags_the_sibling(self, fake_home: Path) -> None:
        _seed_legacy(fake_home)

        result = _run_install(fake_home)

        combined = result.stdout + result.stderr
        assert "super-fr@derio-net" in combined, (
            f"a sibling's dropped registration must be named, not silent:\n{combined}"
        )
        assert "Re-run their installers" in combined

    def test_no_sibling_note_when_only_our_ids_were_purged(self, fake_home: Path) -> None:
        plugins = fake_home / ".claude" / "plugins"
        (plugins / "installed_plugins.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "plugins": {"blog-craft@derio-net": [{"scope": "user", "version": "0.10.0"}]},
                }
            )
        )

        result = _run_install(fake_home)

        assert "Re-run their installers" not in (result.stdout + result.stderr)

    def test_leaves_unrelated_marketplaces_alone(self, fake_home: Path) -> None:
        _seed_legacy(fake_home)

        _run_install(fake_home)

        known = _known(fake_home)
        assert known["thedotmack"]["installLocation"] == "/elsewhere/thedotmack"
        settings = _settings(fake_home)
        assert settings["extraKnownMarketplaces"]["thedotmack"]["source"]["repo"] == (
            "thedotmack/claude-mem"
        )
        assert settings["enabledPlugins"]["claude-mem@thedotmack"] is True
        assert "claude-mem@thedotmack" in _installed(fake_home)["plugins"]

    def test_quiet_on_a_clean_machine(self, fake_home: Path) -> None:
        result = _run_install(fake_home)

        assert "Retired the bare-name" not in result.stdout + result.stderr

    def test_idempotent_across_reinstalls(self, fake_home: Path) -> None:
        _seed_legacy(fake_home)

        _run_install(fake_home)
        _run_install(fake_home)

        for name in RETIRED_NAMES:
            assert name not in _known(fake_home)
        assert PLUGIN_ID in _installed(fake_home)["plugins"]


# ── Uninstall removes only what is ours ───────────────────────────────


class TestUninstallScope:
    """The old `--uninstall` ran `del(."derio-net")` on both registries, which
    deregistered super-fr along with blog-craft."""

    def test_removes_our_marketplace_and_ids(self, fake_home: Path) -> None:
        _run_install(fake_home)

        _run_install(fake_home, "--uninstall")

        assert MARKETPLACE_NAME not in _known(fake_home)
        assert MARKETPLACE_NAME not in _settings(fake_home)["extraKnownMarketplaces"]
        assert PLUGIN_ID not in _installed(fake_home)["plugins"]
        assert PLUGIN_ID not in _settings(fake_home)["enabledPlugins"]

    def test_leaves_a_siblings_marketplace_registered(self, fake_home: Path) -> None:
        plugins = fake_home / ".claude" / "plugins"
        (plugins / "known_marketplaces.json").write_text(
            json.dumps(
                {
                    "derio-net--super-fr": {
                        "source": {"source": "github", "repo": "derio-net/super-fr"},
                        "installLocation": str(plugins / "marketplaces" / "derio-net--super-fr"),
                    }
                }
            )
        )
        (fake_home / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "extraKnownMarketplaces": {
                        "derio-net--super-fr": {
                            "source": {"source": "github", "repo": "derio-net/super-fr"}
                        }
                    },
                    "enabledPlugins": {"super-fr@derio-net--super-fr": True},
                }
            )
        )
        (plugins / "installed_plugins.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "plugins": {
                        "super-fr@derio-net--super-fr": [{"scope": "user", "version": "3.13.0"}]
                    },
                }
            )
        )

        _run_install(fake_home)
        _run_install(fake_home, "--uninstall")

        assert "derio-net--super-fr" in _known(fake_home)
        settings = _settings(fake_home)
        assert "derio-net--super-fr" in settings["extraKnownMarketplaces"]
        assert settings["enabledPlugins"]["super-fr@derio-net--super-fr"] is True
        assert "super-fr@derio-net--super-fr" in _installed(fake_home)["plugins"]

    def test_uninstall_is_idempotent(self, fake_home: Path) -> None:
        _run_install(fake_home)
        _run_install(fake_home, "--uninstall")
        _run_install(fake_home, "--uninstall")


# ── The validator wrapper delegates to super-fr's renamed marketplace ──


def test_validate_plans_wrapper_points_at_super_frs_new_marketplace() -> None:
    """`scripts/validate-plans.sh` execs the canonical validator out of
    super-fr's marketplace directory, which moved in the same rename."""
    text = (REPO_ROOT / "scripts" / "validate-plans.sh").read_text()
    assert "marketplaces/derio-net--super-fr/scripts/validate-plans.sh" in text
    assert "marketplaces/derio-net/scripts" not in text
