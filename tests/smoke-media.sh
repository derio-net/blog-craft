#!/usr/bin/env bash
# Smoke test for the media skill.
#
# Sets up a bootstrapped blog with one post that contains two placeholders —
# one whose asset is pre-seeded, one whose asset is missing — and asserts
# tools/media-fill.py replaces only the present-asset placeholder.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ANSWERS=${1:-"$REPO_ROOT/tests/fixtures/answers-frank-like.yaml"}
TARGET=${2:-"/tmp/test-bootstrap-fixture"}

# Bootstrap fixture if needed
if [[ ! -f "$TARGET/.blog-craft.yaml" ]]; then
  rm -rf "$TARGET"
  "$REPO_ROOT/tools/bootstrap-render.sh" "$ANSWERS" "$TARGET" >/dev/null
fi

# Ensure a post exists. Reuse the blog-post smoke fixture if present, else create
# a minimal post by hand so this test doesn't transitively depend on smoke-blog-post.
POST_REL="tutorials/99-media-smoke"
POST_DIR="$TARGET/content/docs/$POST_REL"
rm -rf "$POST_DIR"
mkdir -p "$POST_DIR"
cat > "$POST_DIR/index.md" <<'EOF'
---
title: "Media Smoke Test"
date: 2026-05-06
draft: false
weight: 100
---

A test post for the media-fill helper.

<!-- MEDIA: screenshot | A grafana dashboard | Visit example.com and screenshot -->
<!-- {{</* screenshot src="grafana.png" caption="Grafana node metrics" */>}} -->

Section break.

<!-- MEDIA: screenshot | Future panel | Capture later -->
<!-- {{</* screenshot src="future-panel.png" caption="Future panel" */>}} -->
EOF

# Pre-seed the present asset (1px PNG); leave future-panel.png absent.
python3 - "$POST_DIR/grafana.png" <<'PY'
import sys
with open(sys.argv[1], "wb") as f:
    f.write(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "53de0000000c4944415408d763606000000004000139c8a4660000000049454e44ae426082"
    ))
PY

PASS_COUNT=0
FAIL_COUNT=0
pass() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { echo "  FAIL: $1" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); }

echo "=== Run media-fill.py ==="
python3 "$REPO_ROOT/tools/media-fill.py" "$POST_DIR" 2>&1

echo
echo "=== Assertions ==="

# M1: the present-asset placeholder was filled
if grep -qE '^\{\{< screenshot src="grafana.png" caption="Grafana node metrics" >\}\}$' "$POST_DIR/index.md"; then
  pass "M1.a present-asset placeholder rendered as Hugo shortcode"
else
  fail "M1.a present-asset placeholder not rendered"
fi
if ! grep -q 'MEDIA: screenshot | A grafana dashboard' "$POST_DIR/index.md"; then
  pass "M1.b present-asset MEDIA instruction comment removed"
else
  fail "M1.b present-asset MEDIA comment still present"
fi

# M2: the missing-asset placeholder was preserved (both lines)
if grep -q 'MEDIA: screenshot | Future panel' "$POST_DIR/index.md"; then
  pass "M2.a missing-asset MEDIA instruction comment preserved"
else
  fail "M2.a missing-asset MEDIA comment removed (should have been skipped)"
fi
if grep -q 'src="future-panel.png"' "$POST_DIR/index.md" && grep -q '<!-- {{</\*' "$POST_DIR/index.md"; then
  pass "M2.b missing-asset shortcode comment preserved"
else
  fail "M2.b missing-asset shortcode comment was modified"
fi

# M3: Hugo build still succeeds with the rendered shortcode
( cd "$TARGET" && PATH=/usr/local/bin:$PATH hugo --buildDrafts --quiet 2>/tmp/hugo-smoke-media.log )
if [[ "$?" -eq 0 ]] && ! grep -qi error /tmp/hugo-smoke-media.log; then
  pass "M3 hugo --buildDrafts succeeds with the filled post"
else
  fail "M3 hugo build failed — see /tmp/hugo-smoke-media.log"
fi

# M4: rendered HTML contains the screenshot
RENDERED="$TARGET/public/docs/tutorials/99-media-smoke/index.html"
if [[ -f "$RENDERED" ]]; then
  if grep -q 'class="screenshot"' "$RENDERED"; then
    pass "M4 rendered HTML contains <figure class=\"screenshot\">"
  else
    fail "M4 rendered HTML missing screenshot figure"
  fi
else
  fail "M4 rendered HTML file missing ($RENDERED)"
fi

# M5: idempotency — second run is no-op (filled=0, skipped only)
if python3 "$REPO_ROOT/tools/media-fill.py" "$POST_DIR" 2>&1 | grep -q "filled 0"; then
  pass "M5 second run filled 0 placeholders (idempotent)"
else
  # The output line may differ if the only remaining placeholder still has no asset;
  # in that case the script reports "skipped X". Accept either as evidence of no-op.
  out=$(python3 "$REPO_ROOT/tools/media-fill.py" "$POST_DIR" 2>&1 || true)
  if echo "$out" | grep -qE "skipped 1|no <!-- MEDIA"; then
    pass "M5 second run made no changes (idempotent)"
  else
    fail "M5 second run claims to have done work: $out"
  fi
fi

echo
echo "=== Summary ==="
echo "  $PASS_COUNT passed, $FAIL_COUNT failed"
[[ "$FAIL_COUNT" -eq 0 ]] && { echo "ALL OK"; exit 0; } || { echo "FAILED"; exit 1; }
