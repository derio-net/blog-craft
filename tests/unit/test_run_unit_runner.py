"""tests/run-unit.sh must not use — or clear — a SHARED temp pool.

Two runs of the runner overlap all the time (a reviewer re-running one selection
while the full suite goes, two agents in one workspace). pytest's default pool is
`/tmp/pytest-of-<user>`, ONE user-global directory, and the runner used to
`rm -rf` it at startup to stop the numbered-dir pool exhausting across repeated
full-suite runs. That fix made a second bug: the `rm -rf` deleted the in-flight
`tmp_path` directories of any concurrent run. Reproduced before the fix, with
the same selection 15s apart: run A `1 failed, 312 passed, 4 errors`
(`FileNotFoundError: [Errno 2] … '/tmp/pytest-of-vscode/pytest-0'` raised inside
`_pytest/pathlib.py` at test setup) while run B was `317 passed`; both `317
passed` after.

The invariants are cheap to pin because the runner's only real output is the
pytest argv, so these tests run against a STUB venv — a fake `bin/python` that
satisfies the pillow probe and a fake `bin/pytest` that records its arguments and
exits with a chosen code. No venv building, no test collection, milliseconds.
"""
import os
import subprocess
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER = os.path.join(ROOT, "tests", "run-unit.sh")

STUB_PYTEST = """#!/bin/sh
: >"$STUB_ARGS"
for a in "$@"; do printf '%s\\n' "$a" >>"$STUB_ARGS"; done
for a in "$@"; do
  case "$a" in
    --basetemp=*) d=${a#--basetemp=}; [ -d "$d" ] && echo "BASETEMP_EXISTED" >>"$STUB_ARGS" ;;
  esac
done
exit "${STUB_RC:-0}"
"""

# the pillow probe is `$VENV/bin/python -c "import PIL"`; exiting 0 keeps the
# runner out of its setup/lock branch entirely
STUB_PYTHON = "#!/bin/sh\nexit 0\n"


def _stub_venv(tmp_path):
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    for name, body in (("pytest", STUB_PYTEST), ("python", STUB_PYTHON)):
        p = bin_dir / name
        p.write_text(body)
        p.chmod(0o755)
    return tmp_path / "venv"


def _run(tmp_path, args, rc=0):
    venv = _stub_venv(tmp_path)
    argsfile = tmp_path / "argv"
    env = dict(os.environ,
               BLOG_CRAFT_TEST_VENV=str(venv),
               STUB_ARGS=str(argsfile),
               STUB_RC=str(rc))
    r = subprocess.run(["bash", RUNNER, *args], capture_output=True, text=True, env=env)
    recorded = argsfile.read_text().splitlines() if argsfile.exists() else []
    return r, recorded


def _basetemps(recorded):
    return [a.split("=", 1)[1] for a in recorded if a.startswith("--basetemp=")]


def test_the_runner_gives_pytest_a_private_basetemp(tmp_path):
    r, recorded = _run(tmp_path, ["-k", "nothing"])
    assert r.returncode == 0, r.stdout + r.stderr
    bts = _basetemps(recorded)
    assert len(bts) == 1, f"expected exactly one --basetemp, got {bts}"
    assert "pytest-of-" not in bts[0], (
        f"{bts[0]} is inside pytest's user-global pool; the point is to be private")
    assert "BASETEMP_EXISTED" in recorded, "the basetemp must exist when pytest starts"


def test_the_runner_does_not_touch_the_user_global_pytest_pool(tmp_path):
    """The regression guard for the deletion itself: a canary in the shared pool
    must survive a run. This is what took out a concurrent run's tmp_path dirs."""
    pool = os.path.join(tempfile.gettempdir(), "pytest-of-%s" % os.environ.get(
        "USER", os.environ.get("LOGNAME", "unknown")))
    pool_existed = os.path.isdir(pool)
    os.makedirs(pool, exist_ok=True)
    canary = os.path.join(pool, "CANARY-run-unit-runner-test")
    with open(canary, "w") as fh:
        fh.write("do not delete me\n")
    try:
        r, _ = _run(tmp_path, ["-k", "nothing"])
        assert r.returncode == 0, r.stdout + r.stderr
        assert os.path.exists(canary), (
            f"the runner deleted {pool} — that is a CONCURRENT run's in-flight "
            "tmp_path pool, not scratch space it owns")
    finally:
        if os.path.exists(canary):
            os.unlink(canary)
        if not pool_existed:
            try:
                os.rmdir(pool)
            except OSError:
                pass


def test_a_caller_supplied_basetemp_wins(tmp_path):
    mine = tmp_path / "mine"
    mine.mkdir()
    r, recorded = _run(tmp_path, ["--basetemp=%s" % mine, "-k", "nothing"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _basetemps(recorded) == [str(mine)], (
        "the runner must not override a --basetemp the caller passed: "
        + repr(recorded))


def test_a_caller_supplied_basetemp_as_two_words_also_wins(tmp_path):
    mine = tmp_path / "mine2"
    mine.mkdir()
    r, recorded = _run(tmp_path, ["--basetemp", str(mine)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _basetemps(recorded) == [], (
        "`--basetemp <dir>` is two argv entries; the runner must still defer: "
        + repr(recorded))


@pytest.mark.parametrize("rc", [0, 1, 4, 5, 7])
def test_pytests_exit_code_survives_the_cleanup_trap(tmp_path, rc):
    """pytest used to be `exec`ed, which is why cleanup needs a trap — and a
    trap is exactly where an exit code gets clobbered. pytest's codes are
    meaningful (5 = nothing collected, 4 = usage), so all of them must pass
    through unchanged."""
    r, _ = _run(tmp_path, ["-k", "nothing"], rc=rc)
    assert r.returncode == rc, r.stdout + r.stderr


def test_a_green_run_leaves_no_temp_tree_behind(tmp_path):
    r, recorded = _run(tmp_path, ["-k", "nothing"], rc=0)
    bt = _basetemps(recorded)[0]
    assert not os.path.exists(bt), f"{bt} leaked; one temp tree per run adds up"
    assert r.returncode == 0


def test_a_red_run_keeps_its_temp_tree_and_says_where(tmp_path):
    """The tree of a failing run is the one worth looking at. Keeping it is only
    safe because it is private — the old shared pool got wiped by the next run."""
    r, recorded = _run(tmp_path, ["-k", "nothing"], rc=1)
    bt = _basetemps(recorded)[0]
    try:
        assert os.path.isdir(bt), f"{bt} was deleted despite the run being red"
        assert bt in r.stderr, f"the kept tree's path must be reported:\n{r.stderr}"
    finally:
        subprocess.run(["rm", "-rf", bt], check=False)
