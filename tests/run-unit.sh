#!/usr/bin/env bash
# Unit-test runner: ensures a cached venv with pytest + pyyaml + pillow, then
# runs pytest. Portable — uses `uv` when present (devcontainer), else falls back
# to `python -m venv` + pip (CI runners without uv).
# Usage: tests/run-unit.sh [pytest args...]   (default: tests/unit)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}"
PYBIN="${PYTHON:-python3}"

_pip_install() {  # install into the venv; prefer uv, else the venv's pip
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$VENV/bin/python" "$@" >/dev/null 2>&1
  else
    "$VENV/bin/pip" install -q "$@" >/dev/null 2>&1
  fi
}

if [ ! -x "$VENV/bin/pytest" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV" >/dev/null 2>&1
  else
    "$PYBIN" -m venv "$VENV" >/dev/null 2>&1
  fi
  _pip_install pytest pyyaml pillow markdown
fi
# ensure pillow even on a pre-existing venv (contact sheet / post-process need it)
"$VENV/bin/python" -c "import PIL" >/dev/null 2>&1 || _pip_install pillow
cd "$HERE"
# pytest's numbered-dir pool under /tmp/pytest-of-<user> exhausts across
# repeated full-suite runs (OSError: could not create numbered dir with prefix
# pytest- after 10 tries, ~40-165 collection ERRORs on tmp_path tests).
# Clearing it up front deterministically restores green; pytest recreates it.
rm -rf "/tmp/pytest-of-$(id -un)" 2>/dev/null || true
exec "$VENV/bin/pytest" -q "${@:-tests/unit}"
