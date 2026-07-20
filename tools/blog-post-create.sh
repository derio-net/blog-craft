#!/usr/bin/env bash
# Internal helper used by skills/blog-post/SKILL.md.
# Given the post body + the SCENE-ONLY image brief, do the mechanical bits:
#   1. Create the page bundle with frontmatter (under site_dir, spec D3)
#   2. Append a scene-only YAML entry (+ selector fields) to the blog's
#      configured prompts file — the generator composes the layers around it
#   3. Run <site_dir>/scripts/generate-images.py --only <key>
#   (the series overview auto-lists the post via {{< series-index >}})
#
# Usage:
#   blog-post-create.sh [--entry-field k=v]... [--output <path>] \
#                       <blog_root> <series> <number> <slug> <title> \
#                       <scene-file> <body-file> <summary-file> \
#                       [<reader-goal-file>] [<diataxis>]
#
# --entry-field k=v — selector field for the entry (e.g. mood=cautious,
#                  torso_variant=1); repeatable. Integers stay integers.
# --output <path>  — entry output path override (default
#                  <image.output_dir>/<key>-cover.png), config-root-relative.
# <scene-file>   — the per-post SCENE brief only (multi-paragraph OK). Never a
#                  fully composed prompt: the engine composes
#                  image.composition_order around it (#39 item 2).
# <body-file>    — post body (everything under the frontmatter)
# <summary-file> — short summary string for the frontmatter `summary:` field
# <reader-goal-file> — optional; single-line educational-writing `reader_goal:`
# <diataxis>     — optional; comma-separated Diátaxis mode(s)
#
# Reads .blog-craft.yaml (the config it REQUIRES) for site_dir, prompts_file,
# output_dir — a blog whose structure differs from the bootstrap default works
# (#39 items 1+4). No reference is forced: the generator's own precedence
# (--reference > image.reference_image > pool-by-series > generic pool > none)
# decides.
set -euo pipefail

ENTRY_FIELDS=()
OUTPUT_OVERRIDE=""
while [[ $# -gt 0 && "$1" == --* ]]; do
  case "$1" in
    --entry-field) ENTRY_FIELDS+=("${2:?"--entry-field needs k=v"}"); shift 2 ;;
    --output)      OUTPUT_OVERRIDE=${2:?"--output needs a path"}; shift 2 ;;
    *) echo "ERROR: unknown flag $1" >&2; exit 2 ;;
  esac
done

BLOG_ROOT=${1:?"blog_root required"}
SERIES=${2:?"series required"}
NUMBER=${3:?"number (zero-padded) required"}
SLUG=${4:?"slug (kebab-case) required"}
TITLE=${5:?"title required"}
SCENE_FILE=${6:?"scene-file required"}
BODY_FILE=${7:?"body-file required"}
SUMMARY_FILE=${8:?"summary-file required"}
READER_GOAL_FILE=${9:-}
DIATAXIS=${10:-}

CONFIG="$BLOG_ROOT/.blog-craft.yaml"
[[ -f "$CONFIG" ]]       || { echo "ERROR: $CONFIG not found" >&2; exit 2; }
[[ -f "$SCENE_FILE" ]]   || { echo "ERROR: scene file $SCENE_FILE not found"   >&2; exit 2; }
[[ -f "$BODY_FILE" ]]    || { echo "ERROR: body file $BODY_FILE not found"     >&2; exit 2; }
[[ -f "$SUMMARY_FILE" ]] || { echo "ERROR: summary file $SUMMARY_FILE not found" >&2; exit 2; }

# Locate the config reader: sibling in the plugin's tools/, else the blog's copy.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLOG_CONFIG="$HERE/blog_config.py"
if [[ ! -f "$BLOG_CONFIG" ]]; then
  BLOG_CONFIG=$(find "$BLOG_ROOT" -maxdepth 3 -name blog_config.py -not -path '*/.*' | head -1)
  [[ -n "$BLOG_CONFIG" ]] || { echo "ERROR: blog_config.py not found (plugin tools/ or blog scripts/)" >&2; exit 2; }
fi
cfg() { python3 "$BLOG_CONFIG" --config "$CONFIG" get "$@"; }

SITE_DIR=$(cfg site_dir --default ".")
PROMPTS_REL=$(cfg image.prompts_file --default "prompt_for_images.yaml")
OUTPUT_DIR=$(cfg image.output_dir --default "static/images")

# Read summary, trim whitespace, escape double-quotes for safe insertion in
# YAML double-quoted scalar.
SUMMARY=$(tr -d '\n' < "$SUMMARY_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g; s/"/\\"/g')

WEIGHT=$((10#$NUMBER + 1))
TODAY=$(date +%Y-%m-%d)
KEY="$SERIES-$NUMBER"
OUTPUT_IMAGE=${OUTPUT_OVERRIDE:-"$OUTPUT_DIR/$KEY-cover.png"}
SITE_PREFIX=${SITE_DIR%/}; [[ "$SITE_PREFIX" == "." ]] && SITE_PREFIX=""
BUNDLE_DIR="$BLOG_ROOT/${SITE_PREFIX:+$SITE_PREFIX/}content/docs/$SERIES/$NUMBER-$SLUG"
PROMPTS_YAML="$BLOG_ROOT/$PROMPTS_REL"
[[ -f "$PROMPTS_YAML" ]] || { echo "ERROR: prompts file $PROMPTS_YAML (image.prompts_file) not found" >&2; exit 2; }

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

# 2. Append the SCENE-ONLY entry + selector fields. Indent scene lines by 6
#    spaces (under "prompt: |" which sits at 4 spaces). Integer field values
#    stay bare so the engine's int-index selection works; everything else is
#    double-quoted.
INDENTED_SCENE=$(sed 's/^/      /' "$SCENE_FILE")
{
  echo "  - key: $KEY"
  echo "    series: $SERIES"
  echo "    output: $OUTPUT_IMAGE"
  echo "    description: \"Cover for $SERIES post $NUMBER — $TITLE\""
  for kv in ${ENTRY_FIELDS[@]+"${ENTRY_FIELDS[@]}"}; do
    k=${kv%%=*}; v=${kv#*=}
    if [[ "$v" =~ ^-?[0-9]+$ ]]; then
      echo "    $k: $v"
    else
      echo "    $k: \"$(printf '%s' "$v" | sed 's/"/\\"/g')\""
    fi
  done
  echo "    prompt: |"
  echo "$INDENTED_SCENE"
} >> "$PROMPTS_YAML"
echo "  prompts entry: key=$KEY appended to $PROMPTS_YAML (scene-only + selectors)"

# 3. Image generation from the config root — the generator resolves every path
#    (prompts_file, output, reference pool) relative to the config, and its own
#    reference precedence applies (no reference is required).
( cd "$BLOG_ROOT" && python3 "${SITE_PREFIX:+$SITE_PREFIX/}scripts/generate-images.py" --config .blog-craft.yaml --only "$KEY" )

# 4. No overview update — the series overview lists this post automatically via
#    the {{< series-index >}} shortcode (page-derived) on the next build.

echo
echo "POST CREATED."
echo "  Preview: cd $BLOG_ROOT/${SITE_PREFIX:+$SITE_PREFIX/} && bash scripts/hugo-serve.sh --buildDrafts"
echo "  Edit:    \$EDITOR $BUNDLE_DIR/index.md"
