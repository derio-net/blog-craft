"""OpenCode skills/commands are namespaced `blog-craft-<name>`; canonical stays bare.

OpenCode discovers skills into a single FLAT global dir (~/.config/opencode/skills/)
shared with every plugin and third-party skill, and it has no marketplace layer to
namespace them (Claude Code does — it shows these as blog-craft:<name>). OpenCode's
naming rule (`^[a-z0-9]+(-[a-z0-9]+)*$`, no nested dirs) leaves a hyphenated prefix
as the only mechanism, so the .opencode/ mirror carries `blog-craft-<name>` with the
SKILL.md `name:` rewritten to match. The prefix lives ONLY in the OpenCode delivery
layer: canonical skills/<name>/ keep bare names, so Claude Code stays clean.

Two layers pinned here:
  1. the committed .opencode/ mirror obeys the prefix contract (static, fast);
  2. scripts/install.sh delivers the prefixed mirror and migrates off any stale
     bare-named copy a pre-prefix install left — but only when byte-identical to
     our own skill, never a same-named third-party skill.

test_opencode_sync.py (shells `sync-opencode.py --check`) separately guarantees the
committed mirror matches what the generator would produce.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CANON_SKILLS = REPO_ROOT / "skills"
MIRROR_SKILLS = REPO_ROOT / ".opencode" / "skills"
MIRROR_COMMANDS = REPO_ROOT / ".opencode" / "commands"
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
PREFIX = "blog-craft-"


def _frontmatter_name(skill_md: Path) -> str | None:
    text = skill_md.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    for line in parts[1].splitlines():
        if line.startswith("name:"):
            return line.partition(":")[2].strip()
    return None


def _canonical_names() -> list[str]:
    return sorted(p.parent.name for p in CANON_SKILLS.glob("*/SKILL.md"))


# ── The committed mirror obeys the prefix contract ────────────────────


class TestMirrorContract:
    def test_every_canonical_skill_has_a_prefixed_mirror(self) -> None:
        for name in _canonical_names():
            skill = MIRROR_SKILLS / f"{PREFIX}{name}" / "SKILL.md"
            cmd = MIRROR_COMMANDS / f"{PREFIX}{name}.md"
            assert skill.exists(), f"missing mirror skill for {name}"
            assert cmd.exists(), f"missing mirror command for {name}"

    def test_mirror_skill_dirs_are_all_prefixed(self) -> None:
        dirs = [p.name for p in MIRROR_SKILLS.iterdir() if p.is_dir()]
        assert dirs, "no mirror skill dirs found"
        for d in dirs:
            assert d.startswith(PREFIX), f"mirror skill dir {d!r} is not prefixed"

    def test_mirror_command_files_are_all_prefixed(self) -> None:
        cmds = [p.name for p in MIRROR_COMMANDS.glob("*.md")]
        assert cmds, "no mirror command files found"
        for c in cmds:
            assert c.startswith(PREFIX), f"mirror command {c!r} is not prefixed"

    def test_mirror_frontmatter_name_matches_directory(self) -> None:
        # OpenCode requires the SKILL.md `name:` to equal its directory.
        for skill_md in MIRROR_SKILLS.glob("*/SKILL.md"):
            assert _frontmatter_name(skill_md) == skill_md.parent.name

    def test_mirror_command_body_invokes_the_prefixed_skill(self) -> None:
        for name in _canonical_names():
            body = (MIRROR_COMMANDS / f"{PREFIX}{name}.md").read_text()
            assert f"Use the `{PREFIX}{name}` skill to handle this request." in body

    def test_mirror_body_is_canonical_verbatim_apart_from_the_name_line(self) -> None:
        # Proves the prefix is OpenCode-only: only the frontmatter name line
        # changed; the body is a verbatim copy of the canonical skill.
        for name in _canonical_names():
            canon = (CANON_SKILLS / name / "SKILL.md").read_text().splitlines()
            mirror = (MIRROR_SKILLS / f"{PREFIX}{name}" / "SKILL.md").read_text().splitlines()
            strip = lambda lines: [ln for ln in lines if not ln.startswith("name:")]  # noqa: E731
            assert strip(canon) == strip(mirror), f"{name}: mirror body diverged from canonical"


class TestCanonicalStaysBare:
    def test_canonical_skill_dirs_are_not_prefixed(self) -> None:
        for name in _canonical_names():
            assert not name.startswith(PREFIX), (
                f"canonical skill {name!r} must stay bare — the prefix is OpenCode-only"
            )

    def test_canonical_frontmatter_name_matches_bare_dir(self) -> None:
        for name in _canonical_names():
            assert _frontmatter_name(CANON_SKILLS / name / "SKILL.md") == name


# ── install.sh delivers the prefixed mirror and migrates off bare names ──


pytestmark_install = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("uv") is None,
    reason="install.sh needs jq + uv",
)


@pytest.fixture()
def fake_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    plugins = home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "installed_plugins.json").write_text('{"plugins": {}, "version": 2}')
    (plugins / "known_marketplaces.json").write_text("{}")
    (home / ".claude" / "settings.json").write_text("{}")
    (home / ".config" / "opencode").mkdir(parents=True)
    return home


def _run_install(home: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    r = subprocess.run(
        ["bash", str(INSTALL_SH)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, f"install.sh failed:\n{r.stdout}\n{r.stderr}"
    return r


@pytestmark_install
class TestInstallDelivery:
    def _oc(self, home: Path) -> Path:
        return home / ".config" / "opencode"

    def test_delivers_prefixed_skills_and_commands(self, fake_home: Path) -> None:
        _run_install(fake_home)
        oc = self._oc(fake_home)
        for name in _canonical_names():
            assert (oc / "skills" / f"{PREFIX}{name}" / "SKILL.md").exists()
            assert (oc / "commands" / f"{PREFIX}{name}.md").exists()
            # never the bare name
            assert not (oc / "skills" / name).exists()
            assert not (oc / "commands" / f"{name}.md").exists()

    def test_migrates_off_a_stale_bare_copy(self, fake_home: Path) -> None:
        oc = self._oc(fake_home)
        # A pre-prefix install left a bare `media` byte-identical to ours.
        stale = oc / "skills" / "media"
        stale.mkdir(parents=True)
        shutil.copy(CANON_SKILLS / "media" / "SKILL.md", stale / "SKILL.md")
        stale_cmd = oc / "commands" / "media.md"
        stale_cmd.parent.mkdir(parents=True, exist_ok=True)
        stale_cmd.write_text(
            "---\ndescription: x\n---\nUse the `media` skill to handle this request.\n\n$ARGUMENTS\n"
        )

        _run_install(fake_home)

        assert not stale.exists(), "stale bare skill must be migrated away"
        assert not stale_cmd.exists(), "stale bare command must be migrated away"
        assert (oc / "skills" / f"{PREFIX}media" / "SKILL.md").exists()
        assert (oc / "commands" / f"{PREFIX}media.md").exists()

    def test_preserves_a_third_party_bare_skill(self, fake_home: Path) -> None:
        oc = self._oc(fake_home)
        # Someone else's `media` skill — NOT ours. Must survive.
        third = oc / "skills" / "media"
        third.mkdir(parents=True)
        (third / "SKILL.md").write_text("---\nname: media\n---\nSomebody else's skill.\n")
        third_cmd = oc / "commands" / "media.md"
        third_cmd.parent.mkdir(parents=True, exist_ok=True)
        third_cmd.write_text("---\ndescription: theirs\n---\nSomething unrelated.\n")

        _run_install(fake_home)

        assert third.exists(), "a same-named third-party skill must not be deleted"
        assert "Somebody else's skill." in (third / "SKILL.md").read_text()
        assert third_cmd.exists(), "a same-named third-party command must not be deleted"
        assert (oc / "skills" / f"{PREFIX}media" / "SKILL.md").exists()
