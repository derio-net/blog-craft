#!/usr/bin/env bash
# Smoke test for the bootstrap-blog skill.
#
# Bypasses the conversational wizard layer (manually verified in Phase 6) and
# drives the rendering pipeline directly via tools/bootstrap-render.sh against
# the canned answers fixture.
#
# Usage: tests/smoke-bootstrap.sh [<answers.yaml> [<target-dir>]]
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ANSWERS=${1:-"$REPO_ROOT/tests/fixtures/answers-frank-like.yaml"}
TARGET=${2:-"/tmp/test-bootstrap-fixture"}
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1])")

PASS_COUNT=0
FAIL_COUNT=0
pass() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { echo "  FAIL: $1" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); }

# Always start from a clean slate so re-runs are deterministic
rm -rf "$TARGET"

echo "=== Bootstrap ==="
"$REPO_ROOT/tools/bootstrap-render.sh" "$ANSWERS" "$TARGET" >/dev/null

echo
echo "=== Assertions ==="

# A1: .blog-craft.yaml exists and parses
if [[ -f "$TARGET/.blog-craft.yaml" ]]; then
  pass "A1.a .blog-craft.yaml exists"
  if ( cd "$REPO_ROOT/tools/render-template" && go run . --check --answers "$TARGET/.blog-craft.yaml" ) 2>/dev/null; then
    pass "A1.b .blog-craft.yaml parses as YAML"
  else
    fail "A1.b .blog-craft.yaml does not parse"
  fi
else
  fail "A1.a .blog-craft.yaml missing"
fi

# A2: every expected file is present
expected=(
  "hugo.toml"
  "go.mod"
  "README.md"
  "MEDIA-GUIDE.md"
  ".gitignore"
  "scripts/generate-images.py"
  "prompt_for_images.yaml"
  "static/images/.gitkeep"
  "layouts/partials/custom/head-end.html"
  "layouts/shortcodes/screenshot.html"
  "layouts/shortcodes/asciinema.html"
  "layouts/shortcodes/roadmap.html"
  "content/docs/_index.md"
  "content/docs/tutorials/_index.md"
  "content/docs/recipes/_index.md"
  "content/docs/tutorials/00-overview/index.md"
  "content/docs/recipes/00-overview/index.md"
)
missing=()
for f in "${expected[@]}"; do
  [[ -f "$TARGET/$f" ]] || missing+=("$f")
done
if [[ ${#missing[@]} -eq 0 ]]; then
  pass "A2 all ${#expected[@]} expected files present"
else
  fail "A2 missing: ${missing[*]}"
fi

# A3: hugo server returns 200 on configured baseURL path
( cd "$TARGET" && PATH=/usr/local/bin:$PATH hugo server --port "$PORT" --buildDrafts > /tmp/hugo-smoke-bootstrap.log 2>&1 ) &
HUGO_PID=$!
# poll for up to 15s
for i in {1..15}; do
  code=$(curl -sf -o /dev/null -w '%{http_code}' "http://localhost:$PORT/test/" 2>/dev/null || echo "000")
  [[ "$code" == "200" ]] && break
  sleep 1
done
kill "$HUGO_PID" 2>/dev/null || true
wait "$HUGO_PID" 2>/dev/null || true
if [[ "$code" == "200" ]]; then
  pass "A3 hugo server returned 200 on /test/ (port $PORT)"
else
  fail "A3 hugo server did not return 200 (last code: $code). See /tmp/hugo-smoke-bootstrap.log"
fi

# A4: re-running the wizard refuses
echo
echo "=== Re-run refusal ==="
if "$REPO_ROOT/tools/bootstrap-render.sh" "$ANSWERS" "$TARGET" 2>/dev/null; then
  fail "A4 re-run unexpectedly succeeded — should have refused"
else
  rc=$?
  if [[ "$rc" == "2" ]]; then
    pass "A4 re-run refused with exit code 2 (as expected)"
  else
    fail "A4 re-run failed with exit $rc, expected 2"
  fi
fi

echo
echo "=== Summary ==="
echo "  $PASS_COUNT passed, $FAIL_COUNT failed"
[[ "$FAIL_COUNT" -eq 0 ]] && { echo "ALL OK"; exit 0; } || { echo "FAILED"; exit 1; }
