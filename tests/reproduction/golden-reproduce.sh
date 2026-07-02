#!/usr/bin/env bash
# golden-reproduce.sh — run the reproduction harness for a blog against its real tree.
#
# Used in the MIGRATION PRs (frank P7 / a stoa migration), where the blog's real
# tree is the working copy: it asserts ZERO structural drift between
# blog-craft + <config> and the blog's actual framework/merged paths (spec §12.1–2).
# In blog-craft's own CI the real trees aren't present, so this is invoked with a
# vendored/checked-out reference, not run by default.
#
# Usage: golden-reproduce.sh <config.blog-craft.yaml> <reference-blog-tree>
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONFIG="${1:?config path required}"
REFERENCE="${2:?reference blog tree required}"
PY="${PYTHON:-python3}"
"$PY" -c "import yaml" 2>/dev/null || PY="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}/bin/python"

SCRATCH="$(mktemp -d)/gen"
trap 'rm -rf "$(dirname "$SCRATCH")"' EXIT
exec "$PY" "$REPO_ROOT/tools/reproduce.py" --config "$CONFIG" --reference "$REFERENCE" --scratch "$SCRATCH"
