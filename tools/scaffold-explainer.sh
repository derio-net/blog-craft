#!/usr/bin/env bash
# scaffold-explainer.sh — create an explainer page-bundle (blog mode) or a
# standalone markdown file (standalone mode).
#
# Blog mode (default):
#   scaffold-explainer.sh --config <.blog-craft.yaml> [--archetype <id>] <NN> <slug>
#
# Standalone mode:
#   scaffold-explainer.sh --standalone [--output <dir>] [--target <path>]
#                          [--archetype <id>] [--weight-offset <n>] <NN> <slug>
#
# --archetype selects one of the six explainer modes (default feature-deep-dive):
#   feature-deep-dive skill-presentation skill-comparison
#   testing-pyramid deployment-strategy security-posture
# Each emits that mode's section structure (enforced by validate_explainers.py).
set -euo pipefail

PYTHON="${PYTHON:-python3}"

STANDALONE=""
CONFIG=""
OUTPUT=""
TARGET=""
WEIGHT_OFFSET_ARG=""
ARCHETYPE=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --standalone) STANDALONE=1; shift;;
    --config) CONFIG="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    --target) TARGET="$2"; shift 2;;
    --archetype) ARCHETYPE="$2"; shift 2;;
    --weight-offset) WEIGHT_OFFSET_ARG="$2"; shift 2;;
    *) ARGS+=("$1"); shift;;
  esac
done
NN="${ARGS[0]:?Usage: scaffold-explainer.sh [--standalone] --config <cfg>|<flags> <NN> <slug>}"
SLUG="${ARGS[1]:?Usage: scaffold-explainer.sh [--standalone] --config <cfg>|<flags> <NN> <slug>}"

ARCHETYPE="${ARCHETYPE:-feature-deep-dive}"
case "$ARCHETYPE" in
  feature-deep-dive|skill-presentation|skill-comparison|testing-pyramid|deployment-strategy|security-posture) ;;
  *) echo "ERROR: unknown --archetype '$ARCHETYPE' (known: feature-deep-dive skill-presentation skill-comparison testing-pyramid deployment-strategy security-posture)" >&2; exit 1;;
esac

# Emit the section skeleton for the selected archetype: canonical `##` headings
# + a one-line budget/guidance comment each (validate_explainers.py enforces the
# heading set + order). Quoted heredocs keep backticks / $ / ✓ literal.
sections_for() {
  case "$ARCHETYPE" in
    feature-deep-dive) cat <<'S'
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
S
      ;;
    skill-presentation) cat <<'S'
## Overview

*One paragraph: what the skill does and the problem it solves.*

## When it triggers

*The conditions that activate it (user phrases, repo context, config gates). Include a concrete invocation example.*

## Workflow

*Step-by-step lifecycle. A Mermaid sequence diagram or flowchart if the flow branches.*

## Configuration

*What the operator configures (arguments, config knobs, env vars). A table or `cards` if comparing options.*

## Try it yourself

*Minimal reproducible invocation with expected output.*
S
      ;;
    skill-comparison) cat <<'S'
## Overview

*What both skills do, why a comparison matters.*

## Side-by-side

*A capability matrix (feature rows, skill columns); each cell ✓/✗/partial with a one-line note.*

## When to choose which

*Decision criteria: context size, autonomy, output format, cost. A Mermaid decision flowchart with ≤4 leaves.*

## Concrete divergence

*One scenario where the two produce different results; show both outputs.*

## Try it yourself

*Invoke both on the same input, compare outputs.*
S
      ;;
    testing-pyramid) cat <<'S'
## Overview

*What the testing strategy is and why this shape.*

## The pyramid

*A Mermaid pyramid/flowchart of the repo's actual layers with real counts. Label each layer with its test dir or runner.*

## One example per layer

*A minimal test from each layer with a `file:line` ref and one sentence on what it covers.*

## Gaps and tradeoffs

*What's missing or under-tested; deliberate choices.*

## Try it yourself

*How to run the full suite, how to run one layer.*
S
      ;;
    deployment-strategy) cat <<'S'
## Overview

*One paragraph: the deployment model (CI/CD, manual, hybrid).*

## The pipeline

*A Mermaid flowchart of the actual CI/CD flow: triggers, jobs, gates, environments. Label each node with the workflow file and job.*

## Environments

*A table of environments (staging, production, canary), what deploys to each, how promotion works.*

## Rollback path

*How to revert: the command, the trigger, the expected time-to-recover.*

## Try it yourself

*How to trigger a deploy manually (if possible), how to verify it landed.*
S
      ;;
    security-posture) cat <<'S'
## Threat surface

*What's exposed (endpoints, file access, secrets, CI inputs). One sentence per surface, rated high/medium/low.*

## What's enforced in CI

*Automated checks: secret scanning, dependency audit, SAST, permission boundaries. Name the workflow and tool.*

## What's manual

*Things requiring human review: privilege escalation, credential rotation, infra changes. Why they can't be automated.*

## One concrete control

*Deep-dive on one control: what it enforces, where it's defined (file:line), how it's tested.*

## Try it yourself

*How to run the security checks locally.*
S
      ;;
  esac
}

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

SECTIONS="$(sections_for)"

# Write the explainer file (standalone .md or Hugo bundle index.md)
cat > "$OUTFILE" <<FM
---
title: "TODO: Explainer title"
date: ${TODAY}
draft: true
weight: ${WEIGHT}
${SERIES_LINE}
post_number: $(( 10#$NN ))
archetype: ${ARCHETYPE}
tldr: |
  TODO: exec summary, <=150 words. Write last.
tags: ["TODO"]
${TARGET:+target: "$TARGET"}
${STANDALONE:+standalone: true}
---

${SECTIONS}
FM

if [[ -n "$STANDALONE" ]]; then
  echo "Scaffolded explainer ${NN} (${ARCHETYPE}):"
  echo "  file: ${OUTFILE}"
else
  echo "Scaffolded explainer ${NN} (${ARCHETYPE}):"
  echo "  bundle: content/docs/${EXPLAINERS_KEY}/${DIR}/"
fi
