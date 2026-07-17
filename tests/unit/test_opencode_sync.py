"""Enforce that committed .opencode/ mirrors match canonical skills/.

sync-opencode.py generates .opencode/skills|commands|instructions from
canonical sources; the committed copies must not drift (they rotted silently
before this test — broadsheet #22 and archetype-modes #35 never got re-synced).
The script's filename is hyphenated, so it can't be imported — shell it.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNC = os.path.join(ROOT, "scripts", "sync-opencode.py")


def test_opencode_mirrors_in_sync():
    r = subprocess.run(
        [sys.executable, SYNC, "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 0, (
        "committed .opencode/ mirrors drifted from canonical skills/ — run "
        "`python scripts/sync-opencode.py` and commit.\n" + r.stdout + r.stderr
    )
