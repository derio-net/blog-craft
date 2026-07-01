#!/usr/bin/env bash
# Unit-test runner: ensures a cached venv with pytest + pyyaml, then runs pytest.
# Usage: tests/run-unit.sh [pytest args...]   (default: tests/unit)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}"
if [ ! -x "$VENV/bin/pytest" ]; then
  uv venv "$VENV" >/dev/null 2>&1
  uv pip install --python "$VENV/bin/python" pytest pyyaml >/dev/null 2>&1
fi
cd "$HERE"
exec "$VENV/bin/pytest" -q "${@:-tests/unit}"
