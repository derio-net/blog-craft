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

# Absolutize BOTH arguments before anything cds (blog-craft#59).
#
# Every renderer invocation below runs inside `( cd "$RENDERER_DIR" && … )`, so
# a RELATIVE --answers or --dst would be resolved against tools/render-template/
# rather than the caller's directory. That is why the documented
# `--config .blog-craft.yaml` always failed while `--config "$PWD/…"` worked.
# Fixing it here — at the `cd` — fixes every caller at once, including a human
# running this script by hand to diagnose a render.
if [[ ! -f "$ANSWERS" ]]; then
  echo "ERROR: answers YAML not found: $ANSWERS" >&2
  echo "       (resolved from $PWD)" >&2
  exit 2
fi
ANSWERS=$(cd "$(dirname "$ANSWERS")" && pwd)/$(basename "$ANSWERS")

# Preflight — runs against the same location, before TARGET exists.
if [[ -f "$TARGET/.blog-craft.yaml" ]]; then
  echo "ERROR: $TARGET/.blog-craft.yaml already exists." >&2
  echo "       Refusing to overwrite. Remove the file manually if you really want to re-bootstrap." >&2
  exit 2
fi
mkdir -p "$TARGET"
TARGET=$(cd "$TARGET" && pwd)   # now that it exists, absolutize it too

# Stamp blog_craft_version = the current release tag (#18) so tools/update.py
# can always resolve a real git ref (`git archive <ref>`). Skip if the operator
# already set one. The version is canonical in pyproject.toml.
VERSION=$(grep -E '^version[[:space:]]*=' "$PLUGIN_ROOT/pyproject.toml" | head -1 \
  | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')
if [[ -n "$VERSION" ]] && ! grep -qE '^blog_craft_version:' "$ANSWERS"; then
  AUGMENTED=$(mktemp)
  cat "$ANSWERS" >"$AUGMENTED"
  printf '\nblog_craft_version: "v%s"\n' "$VERSION" >>"$AUGMENTED"
  ANSWERS="$AUGMENTED"
  echo "[bootstrap] stamped blog_craft_version: v$VERSION"
fi

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

# Abbreviation glossary: the {{< abbr >}} / {{< glossary-index >}} shortcodes and
# their stylesheet. The registry itself (data/glossary.yaml) is operator-owned
# and written by /glossary, never by bootstrap.
gl_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool features.glossary.enabled 2>/dev/null || echo "false")
if [[ "$gl_value" == "true" ]]; then
  echo "[3f] glossary"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/features/glossary" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3f] glossary: SKIPPED (features.glossary.enabled != true)"
fi

# Mermaid initialiser for CSP-hardened sites. The theme's own init is an inline
# <script> that `script-src 'self'` drops, leaving diagrams stuck in the light
# theme. OPT-IN on purpose: without a CSP the theme's block still runs, and
# materializing this too would race two MutationObservers. See the asset header.
mm_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool features.mermaid_csp_init 2>/dev/null || echo "false")
if [[ "$mm_value" == "true" ]]; then
  echo "[3g] mermaid-csp-init"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/features/mermaid-csp" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3g] mermaid-csp-init: SKIPPED (features.mermaid_csp_init != true)"
fi

# Natural-size mermaid rendering: the framed, horizontally scrollable diagram
# container (assets/css/mermaid-view.css + the render-codeblock-mermaid.html
# hook). DEFAULT ON — unlike every other features.* gate above, absence of the
# key means true, not false. `--get-bool` returns "false" (via its stderr/exit
# path, caught by `|| echo`) for a key that is simply ABSENT from the config,
# which is exactly the case for every blog that has not yet run
# migrations/005_to_006.py — copying the mermaid-csp-init pattern verbatim here
# would silently deny the fix to every existing blog until it updates. So the
# key's PRESENCE is checked first (`--has`, which is true for an explicit
# `false` too, since false is non-nil) and only an explicit value overrides the
# true default.
if ( cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --has features.mermaid_view ) 2>/dev/null; then
  mv_value=$(cd "$RENDERER_DIR" && go run . --answers "$ANSWERS" --get-bool features.mermaid_view 2>/dev/null || echo "false")
else
  mv_value="true"
fi
if [[ "$mv_value" == "true" ]]; then
  echo "[3h] mermaid-view"
  ( cd "$RENDERER_DIR" && go run . --src "$PLUGIN_ROOT/templates/features/mermaid-view" --dst "$TARGET" --answers "$ANSWERS" )
else
  echo "[3h] mermaid-view: SKIPPED (features.mermaid_view == false)"
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

# Record what was rendered. A bootstrap IS this blog's first sync, so the
# snapshot has to be written here too — otherwise the first `/update` after a
# fresh bootstrap (the run that most often enables a feature) falls back to the
# current config and drops the feature's contribution to merged paths (#60).
# Snapshot the EFFECTIVE answers — $ANSWERS after the blog_craft_version stamp,
# not the operator's pre-stamp input — because that is what was actually
# rendered. Non-fatal, like the layer-palette step: a bootstrap must not die
# over its own bookkeeping, and update.py's fallback covers a missing snapshot.
echo "[3g] sync snapshot"
if "${PYTHON:-python3}" "$PLUGIN_ROOT/tools/sync_state.py" --config "$ANSWERS" --blog "$TARGET"; then
  :
else
  echo "[3g] sync-snapshot: SKIPPED — could not write .blog-craft.sync.yaml." >&2
  echo "     Updates will fall back to the current config (see blog-craft#60)." >&2
fi

# Hugo smoke build — fails fast on template/config errors before the user sees them.
echo "[4] hugo build smoke check"
( cd "$TARGET" && hugo --buildDrafts --quiet 2>&1 | grep -v "^WARN" || true )
echo
echo "BOOTSTRAPPED OK -> $TARGET"
echo "  Next: cd $TARGET && bash scripts/hugo-serve.sh --buildDrafts"
