#!/usr/bin/env bash
# Internal helper used by skills/bootstrap-blog/SKILL.md.
# Given a wizard-answers YAML and a target directory:
#   1. Refuse if <target>/.blog-craft.yaml already exists
#   2. Render templates/hugo-hextra/ → <target>/                  (one-pass)
#   3. Render templates/per-series-always/ → <target>/content/docs/<key>/
#   4. If features.series_overview_posts: also render per-series-overview/
#   5. Run `hugo --buildDrafts` once to fail fast on template errors
#
# Usage: bootstrap-render.sh <answers.yaml> <target-dir>
set -euo pipefail

ANSWERS=${1:?"answers YAML required"}
TARGET=${2:?"target directory required"}

PLUGIN_ROOT=$(cd "$(dirname "$0")/.." && pwd)
RENDERER_DIR="$PLUGIN_ROOT/tools/render-template"
export PATH="/usr/local/bin:$PATH"   # ensure brew Go (≥1.22) wins over /usr/local/go

# Preflight
if [[ -f "$TARGET/.blog-craft.yaml" ]]; then
  echo "ERROR: $TARGET/.blog-craft.yaml already exists." >&2
  echo "       Refusing to overwrite. Remove the file manually if you really want to re-bootstrap." >&2
  exit 2
fi
mkdir -p "$TARGET"

# Read features.series_overview_posts from the answers YAML using a small Python one-liner.
# Avoids adding yq as a dependency.
overview_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool features.series_overview_posts 2>/dev/null || echo "true")
[[ "$overview_value" == "true" ]] && overview_enabled=1 || overview_enabled=0

echo "[bootstrap] target:                $TARGET"
echo "[bootstrap] series_overview_posts: $overview_enabled"

echo "[1] one-pass: hugo-hextra/"
( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/hugo-hextra" --dst "$TARGET" --answers "$ANSWERS" )

echo "[2] per-series-always: per-series-always/"
( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/per-series-always" --dst "$TARGET/content/docs" --answers "$ANSWERS" --per-series )

if [[ "$overview_enabled" == "1" ]]; then
  echo "[3] per-series-overview: per-series-overview/"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/per-series-overview" --dst "$TARGET/content/docs" --answers "$ANSWERS" --per-series )
else
  echo "[3] per-series-overview: SKIPPED (features.series_overview_posts=false)"
fi

# Hugo smoke build — fails fast on template/config errors before the user sees them.
echo "[4] hugo build smoke check"
( cd "$TARGET" && hugo --buildDrafts --quiet 2>&1 | grep -v "^WARN" || true )
echo
echo "BOOTSTRAPPED OK -> $TARGET"
echo "  Next: cd $TARGET && hugo server --buildDrafts"
