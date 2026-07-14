#!/usr/bin/env bash
# scaffold-explainer.sh — create an explainer page-bundle in a blog-craft blog.
# Config-driven: reads content_types.explainers (weight_offset) and the
# explainers series key from .blog-craft.yaml.
#
# Usage: scaffold-explainer.sh --config <.blog-craft.yaml> <NN> <slug>
set -euo pipefail

PYTHON="${PYTHON:-python3}"

CONFIG=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    *) ARGS+=("$1"); shift;;
  esac
done
NN="${ARGS[0]:?Usage: scaffold-explainer.sh --config <cfg> <NN> <slug>}"
SLUG="${ARGS[1]:?Usage: scaffold-explainer.sh --config <cfg> <NN> <slug>}"
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
TODAY="$(date +%Y-%m-%d)"
PADDED="$(printf '%02d' "$((10#$NN))")"
DIR="${PADDED}-${SLUG}"
BUNDLE="$ROOT/content/docs/${EXPLAINERS_KEY}/${DIR}"
WEIGHT="$(( 10#$NN + WEIGHT_OFFSET ))"

if [[ -e "$BUNDLE" ]]; then
  echo "ERROR: ${DIR} already exists" >&2
  exit 1
fi
mkdir -p "$BUNDLE"

cat > "$BUNDLE/index.md" <<FM
---
title: "TODO: Explainer title"
date: ${TODAY}
draft: true
weight: ${WEIGHT}
series: [${EXPLAINERS_KEY}]
post_number: $(( 10#$NN ))
archetype: feature-deep-dive
tldr: |
  TODO: exec summary, <=150 words. Write last.
tags: ["TODO"]
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

echo "Scaffolded explainer ${NN}:"
echo "  bundle: content/docs/${EXPLAINERS_KEY}/${DIR}/"
