#!/usr/bin/env bash
# Internal helper used by skills/blog-post/SKILL.md.
# Given the user's pre-composed image prompt, do the mechanical bits:
#   1. Create the page bundle with frontmatter
#   2. Append a YAML entry to <blog>/prompt_for_images.yaml
#   3. Run scripts/generate-images.py --only <key>
#   4. If features.series_overview_posts: update <series>/00-overview/index.md
#
# Usage:
#   blog-post-create.sh <blog_root> <series> <number> <slug> <title> \
#                       <prompt-file> <body-file> <summary-file>
#
# <prompt-file>  — full composed image prompt (multi-paragraph)
# <body-file>    — post body (everything that goes under the frontmatter)
# <summary-file> — short summary string for the frontmatter `summary:` field
#                  (single line; whitespace-trimmed; shell quoting handled here)
#
# All three are passed as files to avoid shell-quoting multi-paragraph or
# special-character content.
set -euo pipefail

BLOG_ROOT=${1:?"blog_root required"}
SERIES=${2:?"series required"}
NUMBER=${3:?"number (zero-padded) required"}
SLUG=${4:?"slug (kebab-case) required"}
TITLE=${5:?"title required"}
PROMPT_FILE=${6:?"prompt-file required"}
BODY_FILE=${7:?"body-file required"}
SUMMARY_FILE=${8:?"summary-file required"}

PLUGIN_ROOT=$(cd "$(dirname "$0")/.." && pwd)
INSERTER="$PLUGIN_ROOT/tools/insert-before-marker.py"
RENDERER_DIR="$PLUGIN_ROOT/tools/render-template"
# Only the go invocation needs brew PATH; don't shadow caller's PATH globally,
# so a venv-on-PATH python3 (e.g. with PyYAML) wins for the image-gen step.
GO_PATH="/usr/local/bin:$PATH"

[[ -f "$BLOG_ROOT/.blog-craft.yaml" ]] || { echo "ERROR: $BLOG_ROOT/.blog-craft.yaml not found" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]]  || { echo "ERROR: prompt file $PROMPT_FILE not found"   >&2; exit 2; }
[[ -f "$BODY_FILE" ]]    || { echo "ERROR: body file $BODY_FILE not found"     >&2; exit 2; }
[[ -f "$SUMMARY_FILE" ]] || { echo "ERROR: summary file $SUMMARY_FILE not found" >&2; exit 2; }

# Read summary, trim whitespace, escape double-quotes for safe insertion in
# YAML double-quoted scalar.
SUMMARY=$(tr -d '\n' < "$SUMMARY_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g; s/"/\\"/g')

# Read overview-posts feature flag from .blog-craft.yaml via the Go renderer
OVERVIEW_ENABLED=$(cd "$RENDERER_DIR" && PATH="$GO_PATH" go run . --answers "$BLOG_ROOT/.blog-craft.yaml" --get-bool features.series_overview_posts 2>/dev/null || echo "true")

WEIGHT=$((10#$NUMBER + 1))
TODAY=$(date +%Y-%m-%d)
KEY="$SERIES-$NUMBER"
OUTPUT_IMAGE="static/images/$KEY-cover.png"
BUNDLE_DIR="$BLOG_ROOT/content/docs/$SERIES/$NUMBER-$SLUG"
PROMPTS_YAML="$BLOG_ROOT/prompt_for_images.yaml"

# 1. Page bundle: frontmatter + composed body
mkdir -p "$BUNDLE_DIR"
{
  cat <<EOF
---
title: "$TITLE"
date: $TODAY
draft: false
tags: []
summary: "$SUMMARY"
weight: $WEIGHT
---

EOF
  cat "$BODY_FILE"
} > "$BUNDLE_DIR/index.md"
echo "  page bundle: $BUNDLE_DIR/index.md (body from $BODY_FILE, summary from $SUMMARY_FILE)"

# 2. Append YAML entry to prompt_for_images.yaml. Indent each prompt line
#    by 6 spaces (under "prompt: |" which sits at 4 spaces).
INDENTED_PROMPT=$(sed 's/^/      /' "$PROMPT_FILE")
cat >> "$PROMPTS_YAML" <<EOF
  - key: $KEY
    output: $OUTPUT_IMAGE
    description: "Cover for $SERIES post $NUMBER — $TITLE"
    prompt: |
$INDENTED_PROMPT
EOF
echo "  prompts entry: key=$KEY appended to $PROMPTS_YAML"

# 3. Image generation. The script requires --reference; bootstrap always copies
# the user's reference image to static/images/reference.png, so use that.
REFERENCE_PATH="static/images/reference.png"
if [[ ! -f "$BLOG_ROOT/$REFERENCE_PATH" ]]; then
  echo "ERROR: reference image not found at $BLOG_ROOT/$REFERENCE_PATH" >&2
  echo "       bootstrap-blog should have placed one there. Add a reference image" >&2
  echo "       and re-run image-gen with: python scripts/generate-images.py --reference $REFERENCE_PATH --only $KEY" >&2
  exit 3
fi
( cd "$BLOG_ROOT" && python3 scripts/generate-images.py --reference "$REFERENCE_PATH" --only "$KEY" )

# 4. Overview update (only if enabled)
if [[ "$OVERVIEW_ENABLED" == "true" ]]; then
  OVERVIEW="$BLOG_ROOT/content/docs/$SERIES/00-overview/index.md"
  if [[ ! -f "$OVERVIEW" ]]; then
    echo "  WARN: overview enabled but $OVERVIEW does not exist — skipping" >&2
  else
    INDEX_MARKER='<!-- /blog-post auto-appends entries here as posts are created. -->'
    MAP_MARKER='<!-- /blog-post auto-appends rows here. -->'
    INDEX_ENTRY="${NUMBER}. [${TITLE}]({{< relref \"${NUMBER}-${SLUG}\" >}})"
    MAP_ROW="| ${NUMBER} | ${TITLE} | (TODO) |"
    python3 "$INSERTER" "$OVERVIEW" "$INDEX_MARKER" "$INDEX_ENTRY" >/dev/null
    python3 "$INSERTER" "$OVERVIEW" "$MAP_MARKER" "$MAP_ROW" >/dev/null
    echo "  overview updated: $OVERVIEW"
  fi
else
  echo "  overview update: SKIPPED (features.series_overview_posts=false)"
fi

echo
echo "POST CREATED."
echo "  Preview: cd $BLOG_ROOT && hugo server --buildDrafts"
echo "  Edit:    \$EDITOR $BUNDLE_DIR/index.md"
