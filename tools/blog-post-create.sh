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
#                       [--layer <code>] [--tag <t>]... \
#                       <blog_root> <series> <number> <slug> <title> \
#                       <scene-file> <body-file> <summary-file> \
#                       [<reader-goal-file>] [<diataxis>]
#
# --entry-field k=v — selector field for the entry (e.g. mood=cautious,
#                  torso_variant=1); repeatable. Integers stay integers.
# --key <key>      — the entry's key (default <series>-<number>); also the
#                  `--only` argument and, where covers live in image.output_dir,
#                  the cover filename `<key>-cover.png` (under the bundle
#                  convention the cover is always `cover.png`). A blog
#                  keyed `<abbrev>-NN-slug` needs an abbreviation that lives in no
#                  config field, so this is an explicit override, never detected
#                  (#65 item 3, spec D6). Read an existing entry and match it.
# --output <path>  — entry output path override, config-root-relative. The default
#                  follows the prompts file's OWN convention (spec D7): covers
#                  inside page bundles → <site_dir>/content/docs/<series>/<NN>-<slug>/
#                  cover.png, otherwise <image.output_dir>/<key>-cover.png.
# --layer <code>   — frontmatter `layer:`, validated against the blog's
#                  series_index.layers registry. Omitted on a blog that declares
#                  layers → `layer: TODO` + a warning; on one that declares none
#                  → no `layer` key at all (#65 item 2, spec D4).
# --tag <t>        — frontmatter tag; repeatable. None → `tags: []` with a TODO
#                  comment (a literal TODO tag would publish a bogus taxonomy
#                  term, since this scaffolder emits draft: false — spec D5).
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
KEY_OVERRIDE=""
LAYER=""
TAGS=()
NO_GENERATE=0
while [[ $# -gt 0 && "$1" == --* ]]; do
  case "$1" in
    --entry-field) ENTRY_FIELDS+=("${2:?"--entry-field needs k=v"}"); shift 2 ;;
    --key)         KEY_OVERRIDE=${2:?"--key needs a value"}; shift 2 ;;
    --output)      OUTPUT_OVERRIDE=${2:?"--output needs a path"}; shift 2 ;;
    --layer)       LAYER=${2:?"--layer needs a code"}; shift 2 ;;
    --tag)         TAGS+=("${2:?"--tag needs a value"}"); shift 2 ;;
    --no-generate) NO_GENERATE=1; shift ;;
    *) echo "ERROR: unknown flag $1" >&2; exit 2 ;;
  esac
done

# Validate selector keys early: plain identifiers only, and never a standard
# entry field (which would inject/duplicate generator-consumed fields).
for kv in ${ENTRY_FIELDS[@]+"${ENTRY_FIELDS[@]}"}; do
  k=${kv%%=*}
  if ! [[ "$k" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "ERROR: --entry-field key '$k' is not a plain identifier" >&2; exit 2
  fi
  case "$k" in
    key|series|output|description|prompt|references|operator_generated|post_process|aspect_ratio|image_size|count)
      echo "ERROR: --entry-field key '$k' is a standard entry field — set it via the dedicated argument" >&2; exit 2 ;;
  esac
done

# The key is guarded like an --entry-field key above, and for the same reason: it
# becomes a `--only <key>` CLI argument, a cover filename and the {{< ... >}}-side
# identifier the generator matches on. Same plain-token shape the `layer:` emitter
# uses, so `ops-30-silent-failure` passes and a space/quote/slash never reaches a
# downstream argument.
#
# Called on the RESOLVED key, not on the flag: `KEY=${KEY_OVERRIDE:-"$SERIES-$NUMBER"}`
# means the positionals reach the entry unvalidated too, so `<series> <number>` of
# `2026-07 27` produced the key `2026-07-27` — retyped by YAML to a date — and the
# append then failed with a message about the prompts file, blaming the file for the
# caller's arguments, with the page bundle already written (V5). $2 names the source
# so the error points at the argument that actually carried the value.
guard_key() {   # $1 = resolved key, $2 = how to name where it came from
  local key=$1 src=$2 lc retyped=""
  if [[ ! "$key" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    echo "ERROR: $src '$key' is not a plain slug (letters, digits, - _ .; must start alphanumeric)" >&2
    exit 2
  fi
  # A plain slug is not yet a plain STRING: the key is emitted bare, so a value
  # YAML retypes comes back as a float/int/bool/null/date and the append verification
  # then fails with a message about the prompts file — blaming the file for the
  # caller's value. So `1.5`, `123`, `0x1f`, `no`, `on`, `y`, `2026-07-27` and friends
  # are rejected HERE, naming their source. Rule: at least one letter, and not one of
  # the YAML 1.1 boolean/null words. `ops-1.5-silent`, `0o17` and `1e5` still pass —
  # PyYAML's int resolver has no `0o` form and its float resolver needs a dot and a
  # signed exponent, so those round-trip as strings.
  lc=$(printf '%s' "$key" | tr '[:upper:]' '[:lower:]')
  [[ "$key" =~ [A-Za-z] ]] || retyped="a number to YAML"
  [[ "$key" =~ ^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$ ]] && retyped="a date to YAML"
  case "$lc" in
    y|yes|n|no|true|false|on|off) retyped="a boolean to YAML" ;;
    null|nan|inf)                 retyped="null/not-a-number to YAML" ;;
    0x*|0b*)                      retyped="a number to YAML" ;;
  esac
  if [[ -n "$retyped" ]]; then
    echo "ERROR: $src '$key' is $retyped, not a string — it would not survive" >&2
    echo "       a round-trip through the entries file. Use a key with at least one letter" >&2
    echo "       that is not y/yes/n/no/on/off/true/false/null (e.g. 'ops-30-silent-failure')." >&2
    [[ "$src" == "--key" ]] || echo "       An explicit --key <key> overrides the derived one." >&2
    exit 2
  fi
}

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

# <number> is `weight: $((10#$NUMBER + 1))` further down, and under `set -u` a
# non-numeric one used to fail as `line 278: WEIGHT: unbound variable` — exit 1, no
# useful message, page bundle already on disk (V6). The shape is the one
# skills/blog-post/SKILL.md Step 3 already documents, checked before anything exists.
if [[ ! "$NUMBER" =~ ^[0-9]{2,3}$ ]]; then
  echo "ERROR: <number> '$NUMBER' must be 2-3 digits, zero-padded (e.g. 07) — it becomes the" >&2
  echo "       page bundle's <NN>-<slug> directory and its frontmatter 'weight'." >&2
  exit 2
fi

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

# YAML double-quoted-scalar escaping: backslashes first, then double quotes.
yaml_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

# The blog's own layer registry (series_index.layers[].code, docs/CONFIG.md §5) —
# read with an inline PyYAML heredoc, the pattern at scaffold-paper.sh:26-34 and
# scaffold-explainer.sh:220-227. blog_config.py get cannot serve it: it flow-dumps
# non-scalars (blog_config.py:52), which is not shell-parseable.
LAYER_CODES=$(python3 - "$CONFIG" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])) or {}
codes = [str(e["code"]) for e in ((c.get("series_index") or {}).get("layers") or [])
         if isinstance(e, dict) and e.get("code")]
print(" ".join(codes))
PY
)

# --layer validation (spec D4). An unknown code is an error that lists the valid
# ones; omitted-on-a-layered-blog is a WARNING plus a greppable `layer: TODO`
# (scaffold-paper.sh:59's convention), never a hard failure — the helper must stay
# usable on a blog mid-setup. `TODO` is inert in the rendered site:
# series-index.html:79-80 looks the code up in data/layer_palette.yaml behind a
# `with` guard, so an unmatched code renders exactly like no layer at all.
if [[ -n "$LAYER" ]]; then
  # No registry → accept verbatim; there is nothing to validate against, and a
  # blog may declare series_index.layers later.
  if [[ -n "$LAYER_CODES" && " $LAYER_CODES " != *" $LAYER "* ]]; then
    echo "ERROR: --layer '$LAYER' is not in this blog's series_index.layers registry." >&2
    echo "       Valid codes: ${LAYER_CODES// /, }" >&2
    exit 2
  fi
elif [[ -n "$LAYER_CODES" ]]; then
  LAYER="TODO"
  echo "WARNING: no --layer given and this blog declares layers (${LAYER_CODES// /, })." >&2
  echo "         Wrote 'layer: TODO' — grep it and set the real code." >&2
fi

# Read summary, trim whitespace, escape for safe insertion.
SUMMARY=$(yaml_escape "$(tr -d '\n' < "$SUMMARY_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')")
TITLE_ESC=$(yaml_escape "$TITLE")
SERIES_ESC=$(yaml_escape "$SERIES")

# tags (spec D5). With none supplied the list stays EMPTY and carries a TODO
# comment — deliberately NOT the sibling scaffolders' `tags: ["TODO"]`:
# scaffold-paper.sh:63 / scaffold-explainer.sh emit `draft: true` alongside it,
# whereas this scaffolder emits `draft: false`, so a literal TODO tag would
# publish a bogus taxonomy term on the next build. A comment cannot.
TAGS_YAML=""
for t in ${TAGS[@]+"${TAGS[@]}"}; do
  TAGS_YAML+="${TAGS_YAML:+, }\"$(yaml_escape "$t")\""
done
if [[ -n "$TAGS_YAML" ]]; then
  TAGS_LINE="tags: [$TAGS_YAML]"
else
  TAGS_LINE="tags: []  # TODO: add tags"
fi

WEIGHT=$((10#$NUMBER + 1))
TODAY=$(date +%Y-%m-%d)
# The key NAMES the entry, and its convention is not derivable: the reporting
# blog's `ops-30-silent-failure` needs an `operating` → `ops` abbreviation that
# appears in no config field (`series[]` is {key, title, description,
# content_type}). So no detection here — an explicit --key or the historical
# default, byte-for-byte (spec D6).
KEY=${KEY_OVERRIDE:-"$SERIES-$NUMBER"}
if [[ -n "$KEY_OVERRIDE" ]]; then guard_key "$KEY" "--key"; else guard_key "$KEY" "<series>-<number>"; fi
SITE_PREFIX=${SITE_DIR%/}; [[ "$SITE_PREFIX" == "." ]] && SITE_PREFIX=""
BUNDLE_REL="${SITE_PREFIX:+$SITE_PREFIX/}content/docs/$SERIES/$NUMBER-$SLUG"
BUNDLE_DIR="$BLOG_ROOT/$BUNDLE_REL"
PROMPTS_YAML="$BLOG_ROOT/$PROMPTS_REL"
[[ -f "$PROMPTS_YAML" ]] || { echo "ERROR: prompts file $PROMPTS_YAML (image.prompts_file) not found" >&2; exit 2; }
PROMPTS_APPEND="$HERE/prompts_append.py"
[[ -f "$PROMPTS_APPEND" ]] || { echo "ERROR: prompts_append.py not found beside blog-post-create.sh ($HERE)" >&2; exit 2; }

# The entry's `output:` — where THIS blog keeps its covers, asked of the file that
# knows (spec D7). Covers inside the page bundle and covers in image.output_dir are
# both legitimate: the reporting blog's 88 entries put them in the bundle
# (blog/content/docs/operating/30-silent-failure/cover.png, resolved by Hugo's page
# resources), a bootstrapped blog puts them in static/images. Detection is honest
# here, unlike for the key (D6): the answer is stated in the file, not abbreviated
# out of it. output-style counts and never fails a scaffold — a tie, no entries or
# an unparseable file all answer output_dir, i.e. today's behaviour, and the append
# step below is where a broken file is reported.
if [[ -n "$OUTPUT_OVERRIDE" ]]; then
  OUTPUT_IMAGE=$OUTPUT_OVERRIDE
else
  OUTPUT_STYLE=$(python3 "$PROMPTS_APPEND" output-style --file "$PROMPTS_YAML" --site-prefix "$SITE_PREFIX")
  if [[ "$OUTPUT_STYLE" == "bundle" ]]; then
    OUTPUT_IMAGE="$BUNDLE_REL/cover.png"   # inside the bundle this run creates below
  else
    OUTPUT_IMAGE="$OUTPUT_DIR/$KEY-cover.png"
  fi
fi

# 0. Compose the v5 composition-block entry: SCENE-ONLY text + selector fields
#    under composition.modifiers (docs/CONFIG.md §4.1, schema v5). Integer
#    values stay bare; everything else is double-quoted. v5 references are
#    explicit — when the config declares image.reference_image, freeze it into
#    reference_images.primary (the operator will point at named character
#    sheets over time).
#    The block is composed at a 2-space indent and PLACED by prompts_append.py,
#    never appended with `>>`: a literal `  - key:` corrupts every prompts file
#    whose `images:` sequence sits at column 0 — valid YAML, and what bootstrap
#    plus 88 hand-written entries produced in the reporting blog (#65 item 1).
#    The helper reads the file's own indent (spec D1) and re-parses what it wrote
#    (D2), so a bad append is loud here instead of surfacing as a ParserError in
#    the next generate-images.py run. Plugin-side only — a blog's scripts/ never
#    invokes it, so there is no mirrored copy to keep in step.
#    Composed BEFORE the page bundle exists so the pre-flight below can be handed
#    the real bytes (V2) — nothing here writes to the blog.
INDENTED_SCENE=$(sed 's/^/        /' "$SCENE_FILE")
PRIMARY_REF=$(cfg image.reference_image --default "")
ENTRY_BLOCK=$(mktemp)
trap 'rm -f "$ENTRY_BLOCK"' EXIT
{
  echo "  - key: $KEY"
  # Plain paths stay bare — that is what the 88 hand-written entries look like and
  # what every previous run of this scaffolder emitted. `--output` and the <slug>/
  # <series> the bundle path is built from are unguarded input, so anything that is
  # not a plain path goes out as a quoted, escaped scalar rather than broken YAML.
  if [[ "$OUTPUT_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9_./-]*$ ]]; then
    echo "    output: $OUTPUT_IMAGE"
  else
    echo "    output: \"$(yaml_escape "$OUTPUT_IMAGE")\""
  fi
  echo "    description: \"Cover for $SERIES post $NUMBER — $TITLE_ESC\""
  echo "    composition:"
  if [[ -n "$PRIMARY_REF" ]]; then
    echo "      reference_images:"
    echo "        primary: $PRIMARY_REF"
  fi
  echo "      modifiers:"
  echo "        series: $SERIES"
  for kv in ${ENTRY_FIELDS[@]+"${ENTRY_FIELDS[@]}"}; do
    k=${kv%%=*}; v=${kv#*=}    # value may itself contain '=' — split on the first only
    if [[ "$v" =~ ^-?[0-9]+$ ]]; then
      echo "        $k: $v"
    else
      echo "        $k: \"$(yaml_escape "$v")\""
    fi
  done
  echo "      scene: |"
  echo "$INDENTED_SCENE"
} > "$ENTRY_BLOCK"

# Refuse a doomed append BEFORE creating anything, so the scaffold is
# all-or-nothing. The append itself (step 2) is what writes and verifies, but it
# runs after the page bundle exists, so a refusal there used to exit 2 with
# content/docs/<series>/<NN>-<slug>/index.md already on disk and no matching entry
# — an operator had to know to go and delete it. `check` performs the WHOLE append
# in memory over THESE bytes — the same indent resolution, the same concatenation,
# the same parse verification — and does not write, so it cannot pass where the
# append will fail (V2). `set -e` carries its exit 2.
python3 "$PROMPTS_APPEND" check --file "$PROMPTS_YAML" --key "$KEY" --entry-file "$ENTRY_BLOCK"

# 1. Page bundle: frontmatter + composed body, in the blog's convention order:
#    title, series, layer?, date, draft, tags, summary, weight, reader_goal?,
#    diataxis? — an author reviews a scaffold by diffing it against a sibling
#    post, so the order is part of the output, not an accident (#65 item 2).
#    reader_goal/diataxis are emitted only when supplied (educational-writing
#    methodology; see docs/CONFIG.md).
#    `series` is ALWAYS emitted (spec D3): {{< series-index >}} is page-derived
#    from it, so a post without it silently never appears in its own series
#    overview — which is exactly what skills/blog-post/SKILL.md Step 8 promises
#    happens automatically. Quoted, unlike the sibling scaffolders' bare
#    `series: [key]`: equivalent after parsing, and safe for any key.
mkdir -p "$BUNDLE_DIR"
{
  echo '---'
  echo "title: \"$TITLE_ESC\""
  echo "series: [\"$SERIES_ESC\"]"
  if [[ -n "$LAYER" ]]; then
    # Plain codes stay bare so `layer: TODO` and `layer: obs` stay greppable
    # (scaffold-paper.sh:59); anything else is quoted+escaped, because "accepted
    # verbatim" means not REJECTING an unregistered code, not emitting bytes the
    # YAML parser chokes on.
    if [[ "$LAYER" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
      echo "layer: $LAYER"
    else
      echo "layer: \"$(yaml_escape "$LAYER")\""
    fi
  fi
  echo "date: $TODAY"
  echo "draft: false"
  echo "$TAGS_LINE"
  echo "summary: \"$SUMMARY\""
  echo "weight: $WEIGHT"
  if [[ -n "$READER_GOAL_FILE" && -f "$READER_GOAL_FILE" ]]; then
    RG=$(yaml_escape "$(tr -d '\n' < "$READER_GOAL_FILE" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')")
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

# 2. Append the v5 composition-block entry, composed at step 0 above.
#    Its exit 2 already names what is wrong on stderr and guarantees the file was
#    left as it was found; `set -e` propagates it rather than reporting a success
#    the operator would only discover was a lie at generate time.
python3 "$PROMPTS_APPEND" append --file "$PROMPTS_YAML" --key "$KEY" --entry-file "$ENTRY_BLOCK"
# The output path is worth printing now that the default follows the blog (D7) and
# the key can be overridden (D6): both are what the operator would otherwise have
# to open the file to learn.
echo "  prompts entry: key=$KEY output=$OUTPUT_IMAGE appended to $PROMPTS_YAML (v5 composition block)"

# 3. Image generation from the config root — the generator resolves every path
#    (prompts_file, output, reference pool) relative to the config, and its own
#    reference precedence applies (no reference is required). --no-generate
#    stops here so the skill can preview --print-prompt before spending a call.
if [[ "$NO_GENERATE" -eq 1 ]]; then
  echo "  image generation skipped (--no-generate). Preview with:"
  echo "    ( cd $BLOG_ROOT && python3 ${SITE_PREFIX:+$SITE_PREFIX/}scripts/generate-images.py --config .blog-craft.yaml --print-prompt $KEY )"
else
  ( cd "$BLOG_ROOT" && python3 "${SITE_PREFIX:+$SITE_PREFIX/}scripts/generate-images.py" --config .blog-craft.yaml --only "$KEY" )
fi

# 4. No overview update — the series overview lists this post automatically via
#    the {{< series-index >}} shortcode (page-derived) on the next build.

echo
echo "POST CREATED."
echo "  Preview: cd $BLOG_ROOT/${SITE_PREFIX:+$SITE_PREFIX/} && bash scripts/hugo-serve.sh --buildDrafts"
echo "  Edit:    \$EDITOR $BUNDLE_DIR/index.md"
