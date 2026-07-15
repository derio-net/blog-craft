#!/usr/bin/env bash
# Internal helper used by skills/blog-post/SKILL.md.
# Given the user's pre-composed image prompt, do the mechanical bits:
#   1. Create the page bundle with frontmatter
#   2. Append a YAML entry to <blog>/prompt_for_images.yaml
#   3. Run scripts/generate-images.py --only <key>
#   (the series overview auto-lists the post via the {{< series-index >}} shortcode — no update needed)
#
# Usage:
#   blog-post-create.sh <blog_root> <series> <number> <slug> <title> \
#                       <prompt-file> <body-file> <summary-file> \
#                       [<reader-goal-file>] [<diataxis>]
#
# <prompt-file>  — full composed image prompt (multi-paragraph)
# <body-file>    — post body (everything that goes under the frontmatter)
# <summary-file> — short summary string for the frontmatter `summary:` field
#                  (single line; whitespace-trimmed; shell quoting handled here)
# <reader-goal-file> — optional; single-line educational-writing `reader_goal:`
#                  (what the reader can DO after reading). Emitted only if given.
# <diataxis>     — optional; comma-separated Diátaxis mode(s) for `diataxis:`
#                  (e.g. "how-to,reference"). Emitted only if given.
#
# The file args avoid shell-quoting multi-paragraph or special-character content.
set -euo pipefail

BLOG_ROOT=${1:?"blog_root required"}
SERIES=${2:?"series required"}
NUMBER=${3:?"number (zero-padded) required"}
SLUG=${4:?"slug (kebab-case) required"}
TITLE=${5:?"title required"}
PROMPT_FILE=${6:?"prompt-file required"}
BODY_FILE=${7:?"body-file required"}
SUMMARY_FILE=${8:?"summary-file required"}
READER_GOAL_FILE=${9:-}
DIATAXIS=${10:-}

[[ -f "$BLOG_ROOT/.blog-craft.yaml" ]] || { echo "ERROR: $BLOG_ROOT/.blog-craft.yaml not found" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]]  || { echo "ERROR: prompt file $PROMPT_FILE not found"   >&2; exit 2; }
[[ -f "$BODY_FILE" ]]    || { echo "ERROR: body file $BODY_FILE not found"     >&2; exit 2; }
[[ -f "$SUMMARY_FILE" ]] || { echo "ERROR: summary file $SUMMARY_FILE not found" >&2; exit 2; }

# Read summary, trim whitespace, escape double-quotes for safe insertion in
# YAML double-quoted scalar.
SUMMARY=$(tr -d '\n' < "$SUMMARY_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g; s/"/\\"/g')

WEIGHT=$((10#$NUMBER + 1))
TODAY=$(date +%Y-%m-%d)
KEY="$SERIES-$NUMBER"
OUTPUT_IMAGE="static/images/$KEY-cover.png"
BUNDLE_DIR="$BLOG_ROOT/content/docs/$SERIES/$NUMBER-$SLUG"
PROMPTS_YAML="$BLOG_ROOT/prompt_for_images.yaml"

# 1. Page bundle: frontmatter + composed body. reader_goal/diataxis are emitted
#    only when supplied (educational-writing methodology; see docs/CONFIG.md).
mkdir -p "$BUNDLE_DIR"
{
  echo '---'
  echo "title: \"$TITLE\""
  echo "date: $TODAY"
  echo "draft: false"
  echo "tags: []"
  echo "summary: \"$SUMMARY\""
  echo "weight: $WEIGHT"
  if [[ -n "$READER_GOAL_FILE" && -f "$READER_GOAL_FILE" ]]; then
    RG=$(tr -d '\n' < "$READER_GOAL_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g; s/"/\\"/g')
    echo "reader_goal: \"$RG\""
  fi
  if [[ -n "$DIATAXIS" ]]; then
    MODES=$(echo "$DIATAXIS" | tr ',' '\n' | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' | grep -v '^$' | paste -sd, - | sed 's/,/, /g')
    echo "diataxis: [$MODES]"
  fi
  echo '---'
  echo
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

# 4. No overview update — the series overview lists this post automatically via
#    the {{< series-index >}} shortcode (page-derived) on the next build.

echo
echo "POST CREATED."
echo "  Preview: cd $BLOG_ROOT && bash scripts/hugo-serve.sh --buildDrafts"
echo "  Edit:    \$EDITOR $BUNDLE_DIR/index.md"
