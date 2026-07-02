#!/usr/bin/env bash
# Unit-test runner: ensures a cached venv with pytest + pyyaml, then runs pytest.
# Usage: tests/run-unit.sh [pytest args...]   (default: tests/unit)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}"
if [ ! -x "$VENV/bin/pytest" ]; then
  uv venv "$VENV" >/dev/null 2>&1
  uv pip install --python "$VENV/bin/python" pytest pyyaml pillow >/dev/null 2>&1
fi
# ensure pillow even on a pre-existing venv (contact sheet / post-process need it)
"$VENV/bin/python" -c "import PIL" >/dev/null 2>&1 || \
  uv pip install --python "$VENV/bin/python" pillow >/dev/null 2>&1
cd "$HERE"
exec "$VENV/bin/pytest" -q "${@:-tests/unit}"
