#!/usr/bin/env bash
# scaffold-explainer.sh — create an explainer page-bundle (blog mode) or a
# standalone markdown file (standalone mode).
#
# Blog mode (default):
#   scaffold-explainer.sh --config <.blog-craft.yaml> <NN> <slug>
#
# Standalone mode:
#   scaffold-explainer.sh --standalone [--output <dir>] [--target <path>]
#                          [--weight-offset <n>] <NN> <slug>
set -euo pipefail

PYTHON="${PYTHON:-python3}"

STANDALONE=""
CONFIG=""
OUTPUT=""
TARGET=""
WEIGHT_OFFSET_ARG=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --standalone) STANDALONE=1; shift;;
    --config) CONFIG="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    --target) TARGET="$2"; shift 2;;
    --weight-offset) WEIGHT_OFFSET_ARG="$2"; shift 2;;
    *) ARGS+=("$1"); shift;;
  esac
done
NN="${ARGS[0]:?Usage: scaffold-explainer.sh [--standalone] --config <cfg>|<flags> <NN> <slug>}"
SLUG="${ARGS[1]:?Usage: scaffold-explainer.sh [--standalone] --config <cfg>|<flags> <NN> <slug>}"

TODAY="$(date +%Y-%m-%d)"
PADDED="$(printf '%02d' "$((10#$NN))")"

if [[ -n "$STANDALONE" ]]; then
  # ---- standalone mode ----
  OUTPUT="${OUTPUT:-.}"
  TARGET="${TARGET:-}"
  WEIGHT_OFFSET="${WEIGHT_OFFSET_ARG:-1}"
  EXPLAINERS_KEY="explainers"
  TAG="#explainers"
  SERIES_LINE="series: [${EXPLAINERS_KEY}]"
  WEIGHT="$(( 10#$NN + WEIGHT_OFFSET ))"

  mkdir -p "$OUTPUT"
  OUTFILE="$OUTPUT/${PADDED}-${SLUG}.md"

  if [[ -e "$OUTFILE" ]]; then
    echo "ERROR: ${OUTFILE} already exists" >&2
    exit 1
  fi
else
  # ---- blog mode ----
  CONFIG="${CONFIG:?--config <.blog-craft.yaml> required}"

  read -r WEIGHT_OFFSET EXPLAINERS_KEY < <("$PYTHON" - "$CONFIG" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])) or {}
e = (c.get("content_types") or {}).get("explainers") or {}
ek = next((s["key"] for s in (c.get("series") or []) if s.get("content_type") == "explainers"), "explainers")
print(e.get("weight_offset", 1), ek)
PY
)

  ROOT="$(cd "$(dirname "$CONFIG")" && pwd)"
  DIR="${PADDED}-${SLUG}"
  BUNDLE="$ROOT/content/docs/${EXPLAINERS_KEY}/${DIR}"
  WEIGHT="$(( 10#$NN + WEIGHT_OFFSET ))"

  if [[ -e "$BUNDLE" ]]; then
    echo "ERROR: ${DIR} already exists" >&2
    exit 1
  fi
  mkdir -p "$BUNDLE"
  OUTFILE="$BUNDLE/index.md"
  SERIES_LINE="series: [${EXPLAINERS_KEY}]"
  TAG=""
fi

# Write the explainer file (standalone .md or Hugo bundle index.md)
cat > "$OUTFILE" <<FM
---
title: "TODO: Explainer title"
date: ${TODAY}
draft: true
weight: ${WEIGHT}
${SERIES_LINE}
post_number: $(( 10#$NN ))
archetype: feature-deep-dive
tldr: |
  TODO: exec summary, <=150 words. Write last.
tags: ["TODO"]
${TARGET:+target: "$TARGET"}
${STANDALONE:+standalone: true}
---

## Overview

*200-350 words. What the feature does and why it exists.*

## Why it exists

*150-300 words. The problem it solves, who benefits.*

## How it works

*400-800 words. Architecture, data flow, key abstractions.*

## Code walkthrough

*300-600 words. Entry points, core logic, extension points.*

## Tradeoffs & alternatives

*200-400 words. What was considered, why this shape won.*

## Try it yourself

*150-300 words. Steps to reproduce or experiment.*
FM

if [[ -n "$STANDALONE" ]]; then
  echo "Scaffolded explainer ${NN}:"
  echo "  file: ${OUTFILE}"
else
  echo "Scaffolded explainer ${NN}:"
  echo "  bundle: content/docs/${EXPLAINERS_KEY}/${DIR}/"
fi
