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
  _pip_install pytest pyyaml pillow
fi
# ensure pillow even on a pre-existing venv (contact sheet / post-process need it)
"$VENV/bin/python" -c "import PIL" >/dev/null 2>&1 || _pip_install pillow
cd "$HERE"
exec "$VENV/bin/pytest" -q "${@:-tests/unit}"
