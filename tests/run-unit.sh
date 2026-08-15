#!/usr/bin/env bash
# Unit-test runner: ensures a cached venv with pytest + pyyaml + pillow, then
# runs pytest. Portable — uses `uv` when present (devcontainer), else falls back
# to `python -m venv` + pip (CI runners without uv).
# Usage: tests/run-unit.sh [pytest args...]   (default: tests/unit)
#
# Two invocations MAY OVERLAP — a reviewer re-running one selection while the
# full suite goes, two agents in one workspace, a CI matrix sharing a runner —
# so everything this script touches outside its own process is either
# per-run-private (the pytest basetemp) or locked (the venv). Both were shared
# before; see the two blocks below.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}"
PYBIN="${PYTHON:-python3}"
LOCK="$VENV.lock"
HELD_LOCK=0
BASETEMP=""

# One cleanup path for both resources. It has to be a trap rather than a tail of
# the script: pytest used to be `exec`ed, which ends the script and would leave
# a temp tree per run behind. `$?` must be read first, and nothing in here may
# change it.
_cleanup() {
  local rc=$?
  if [ "$HELD_LOCK" = "1" ]; then rm -rf "$LOCK" 2>/dev/null || :; fi
  if [ -n "$BASETEMP" ] && [ -d "$BASETEMP" ]; then
    if [ "$rc" -eq 0 ]; then
      rm -rf "$BASETEMP" 2>/dev/null || :
    else
      # A red run is the one whose tmp_path trees you want to look at, so keep
      # them and say where. They are under TMPDIR, not a shared pool, so the
      # next run neither trips over them nor deletes them.
      echo "run-unit.sh: exit $rc — keeping this run's tmp_path tree:" >&2
      echo "  $BASETEMP" >&2
    fi
  fi
}
trap _cleanup EXIT

_pip_install() {  # install into the venv; prefer uv, else the venv's pip
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$VENV/bin/python" "$@" >/dev/null 2>&1
  else
    "$VENV/bin/pip" install -q "$@" >/dev/null 2>&1
  fi
}

# --- the venv is shared; creating it is not concurrency-safe ------------------
# Two runs that both find no venv will both create and both install into the
# same path, and the loser can observe a half-built venv (pytest present,
# pillow not). `mkdir` is atomic on POSIX — unlike `flock`, which macOS does not
# ship — so a lock DIRECTORY is the lock. Only the setup is locked, so the warm
# case (the overwhelmingly common one) takes no lock at all and runs never
# serialize behind each other.
_lock_is_stale() {   # a run killed mid-setup must not wedge the next one forever
  local pid
  pid="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
    return 0                      # holder is gone
  fi
  # No pid yet (a racing writer) or a live pid — which may be a coincidence in
  # another PID namespace — so fall back to age.
  [ -n "$(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ]
}

_acquire_lock() {
  local waited=0
  until mkdir "$LOCK" 2>/dev/null; do
    if _lock_is_stale; then
      echo "run-unit.sh: removing stale venv lock $LOCK" >&2
      rm -rf "$LOCK" 2>/dev/null || :
      continue
    fi
    if [ "$waited" -ge 600 ]; then
      echo "run-unit.sh: gave up waiting ${waited}s for the venv lock $LOCK" >&2
      exit 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
  HELD_LOCK=1
  echo "$$" >"$LOCK/pid" 2>/dev/null || :
}

_release_lock() { rm -rf "$LOCK" 2>/dev/null || :; HELD_LOCK=0; }

if [ ! -x "$VENV/bin/pytest" ] || ! "$VENV/bin/python" -c "import PIL" >/dev/null 2>&1; then
  _acquire_lock
  if [ ! -x "$VENV/bin/pytest" ]; then      # re-check: a waiter may have built it
    if command -v uv >/dev/null 2>&1; then
      uv venv "$VENV" >/dev/null 2>&1
    else
      "$PYBIN" -m venv "$VENV" >/dev/null 2>&1
    fi
    _pip_install pytest pyyaml pillow markdown
  fi
  # ensure pillow even on a pre-existing venv (contact sheet / post-process need it)
  "$VENV/bin/python" -c "import PIL" >/dev/null 2>&1 || _pip_install pillow
  _release_lock
fi

cd "$HERE"
if [ "$#" -eq 0 ]; then set -- tests/unit; fi

# --- one private pytest basetemp per run -------------------------------------
# pytest's default pool is /tmp/pytest-of-<user>, ONE user-global directory that
# every run of every selection shares. That caused two bugs, and this one
# --basetemp fixes both:
#
#   * the numbered-dir pool exhausts across repeated full-suite runs (OSError:
#     could not create numbered dir with prefix pytest- after 10 tries, ~40-165
#     collection ERRORs on tmp_path tests). A fresh pool per run cannot exhaust.
#   * clearing that pool up front — the previous fix for the above — deleted the
#     in-flight tmp_path directories of any CONCURRENT run. Verified, not
#     theorised: run A failed with `FileNotFoundError: [Errno 2] ...
#     '/tmp/pytest-of-vscode/pytest-0'` raised inside _pytest/pathlib.py at test
#     SETUP, at the moment run B started 15s later; the same selection alone is
#     green. A private basetemp cannot be deleted out from under another run.
#
# A caller-supplied --basetemp wins (they know where they want it).
_caller_basetemp=0
for _a in "$@"; do
  case "$_a" in --basetemp|--basetemp=*) _caller_basetemp=1 ;; esac
done
if [ "$_caller_basetemp" -eq 0 ]; then
  BASETEMP="$(mktemp -d "${TMPDIR:-/tmp}/blog-craft-pytest-XXXXXX")"
  set -- --basetemp="$BASETEMP" "$@"
fi

# Not `exec` — the trap above has to run, and the exit code has to survive it.
rc=0
"$VENV/bin/pytest" -q "$@" || rc=$?
exit "$rc"
