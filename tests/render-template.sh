#!/usr/bin/env bash
# Wrapper around tools/render-template that runs the three template subdirs
# in the order bootstrap-blog will use at runtime.
#
# Usage: tests/render-template.sh <answers.yaml> <dst-dir>
set -euo pipefail

ANSWERS=${1:?"answers YAML required"}
DST=${2:?"destination directory required"}

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
RENDERER="$REPO_ROOT/tools/render-template"
export PATH="/usr/local/bin:$PATH"   # ensure brew Go (1.26.x), not the older /usr/local/go

mkdir -p "$DST"

echo "[1/3] one-pass: hugo-hextra/ -> $DST"
( cd "$RENDERER" && go run . --src "$REPO_ROOT/templates/hugo-hextra" --dst "$DST" --answers "$ANSWERS" )

echo "[2/3] per-series-always: per-series-always/ -> $DST/content/docs"
( cd "$RENDERER" && go run . --src "$REPO_ROOT/templates/per-series-always" --dst "$DST/content/docs" --answers "$ANSWERS" --per-series )

# Phase 3's bootstrap-blog skill checks features.series_overview_posts here.
# For the test harness we always render the overview so the smoke test exercises both.
echo "[3/3] per-series-overview: per-series-overview/ -> $DST/content/docs"
( cd "$RENDERER" && go run . --src "$REPO_ROOT/templates/per-series-overview" --dst "$DST/content/docs" --answers "$ANSWERS" --per-series )

echo "RENDERED OK -> $DST"
