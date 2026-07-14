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

# Opt-in content type: papers shared assets (shortcodes + cross-link partials),
# gated on content_types.papers.enabled. The per-paper bundle + dossier come from
# scaffold-paper.sh, not bootstrap.
papers_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool content_types.papers.enabled 2>/dev/null || echo "false")
if [[ "$papers_value" == "true" ]]; then
  echo "[3b] content-type-papers: shared/"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/content-type-papers/shared" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3b] content-type-papers: SKIPPED (content_types.papers.enabled != true)"
fi

# Opt-in content type: explainers shared assets (scaffold + validate scripts),
# gated on content_types.explainers.enabled. The per-post bundle comes from
# scaffold-explainer.sh, not bootstrap.
explainers_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool content_types.explainers.enabled 2>/dev/null || echo "false")
if [[ "$explainers_value" == "true" ]]; then
  echo "[3b2] content-type-explainers: shared/"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/content-type-explainers/shared" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3b2] content-type-explainers: SKIPPED (content_types.explainers.enabled != true)"
fi

# Optional feature assets, gated on features.*
rt_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool features.read_tracker 2>/dev/null || echo "false")
if [[ "$rt_value" == "true" ]]; then
  echo "[3c] read-tracker"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/features/read-tracker" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3c] read-tracker: SKIPPED (features.read_tracker != true)"
fi
if ( cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --has features.analytics ) 2>/dev/null; then
  echo "[3d] analytics"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/features/analytics" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3d] analytics: SKIPPED (no features.analytics)"
fi

# Opt-in layer palette: when the config declares series_index.layers, generate
# data/layer_palette.yaml (colours the series-index cards + roadmap). Non-fatal —
# a machine without PyYAML gets a warning; the author runs the generator manually.
if ( cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --has series_index.layers ) 2>/dev/null; then
  PYBIN="${PYTHON:-python3}"
  if "$PYBIN" -c 'import yaml' 2>/dev/null; then
    mkdir -p "$TARGET/data"
    "$PYBIN" "$PLUGIN_ROOT/tools/gen-layer-palette.py" --config "$ANSWERS" > "$TARGET/data/layer_palette.yaml"
    echo "[3e] layer-palette: generated data/layer_palette.yaml"
  else
    echo "[3e] layer-palette: SKIPPED — '$PYBIN' has no PyYAML." >&2
    echo "     ACTION NEEDED: cards will render NEUTRAL until you generate the palette:" >&2
    echo "       python tools/gen-layer-palette.py --config <.blog-craft.yaml> > $TARGET/data/layer_palette.yaml" >&2
    echo "     (or set PYTHON=<a python with pyyaml> and re-run bootstrap)" >&2
  fi
else
  echo "[3e] layer-palette: SKIPPED (no series_index.layers)"
fi

# Hugo smoke build — fails fast on template/config errors before the user sees them.
echo "[4] hugo build smoke check"
( cd "$TARGET" && hugo --buildDrafts --quiet 2>&1 | grep -v "^WARN" || true )
echo
echo "BOOTSTRAPPED OK -> $TARGET"
echo "  Next: cd $TARGET && bash scripts/hugo-serve.sh --buildDrafts"
