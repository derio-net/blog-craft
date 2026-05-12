#!/usr/bin/env bash
# Smoke test for the blog-post skill.
#
# Bypasses the conversational layer (manually verified in Phase 6) and drives
# tools/blog-post-create.sh with a fixed brief in TEST_MODE (writes 1px PNG
# instead of calling Gemini).
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ANSWERS=${1:-"$REPO_ROOT/tests/fixtures/answers-frank-like.yaml"}
TARGET=${2:-"/tmp/test-bootstrap-fixture"}

# Bootstrap fixture if needed
if [[ ! -f "$TARGET/.blog-craft.yaml" ]]; then
  rm -rf "$TARGET"
  "$REPO_ROOT/tools/bootstrap-render.sh" "$ANSWERS" "$TARGET" >/dev/null
fi

# Seed a reference image. In real use the bootstrap-blog SKILL.md (Step 7) copies
# the operator's chosen reference image; the bootstrap helper itself doesn't, so
# the smoke test has to place a stub. Use a 1px PNG written via stdlib only.
REF="$TARGET/static/images/reference.png"
if [[ ! -f "$REF" ]]; then
  python3 - "$REF" <<'PY'
import struct, zlib, sys
sig = b'\x89PNG\r\n\x1a\n'
def chunk(t, d):
    return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
idat = chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00'))
iend = chunk(b'IEND', b'')
open(sys.argv[1], 'wb').write(sig + ihdr + idat + iend)
PY
fi

# Set up test venv with PyYAML (cached across runs)
TEST_VENV=/tmp/blog-craft-test-venv
if [[ ! -d "$TEST_VENV" ]]; then
  python3 -m venv "$TEST_VENV"
  "$TEST_VENV/bin/pip" install -q pyyaml
fi
export PATH="$TEST_VENV/bin:$PATH"

PASS_COUNT=0
FAIL_COUNT=0
pass() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { echo "  FAIL: $1" >&2; FAIL_COUNT=$((FAIL_COUNT+1)); }

# Clean any prior post artifacts so the test is deterministic
rm -rf "$TARGET/content/docs/tutorials/01-hello-world" "$TARGET/static/images/tutorials-01-cover.png"
# Reset prompts file + overview to their bootstrap state
"$REPO_ROOT/tools/render-template/render-template" 2>/dev/null || true   # ignore — not needed
( cd "$REPO_ROOT/tools/render-template" && PATH=/usr/local/bin:$PATH go run . --src "$REPO_ROOT/templates/hugo-hextra" --dst "$TARGET" --answers "$ANSWERS" >/dev/null 2>&1 )
( cd "$REPO_ROOT/tools/render-template" && PATH=/usr/local/bin:$PATH go run . --src "$REPO_ROOT/templates/per-series-overview" --dst "$TARGET/content/docs" --answers "$ANSWERS" --per-series >/dev/null 2>&1 )

echo "=== Run blog-post-create ==="
echo "Test prompt for hello-world cover image" > /tmp/test-blog-post-prompt.txt
echo "Test body for hello-world. The body is composed by the agent in real use; here we provide a fixture file to drive the helper non-interactively." > /tmp/test-blog-post-body.md
echo -n "Test summary for hello-world." > /tmp/test-blog-post-summary.txt
BLOG_CRAFT_TEST_MODE=1 "$REPO_ROOT/tools/blog-post-create.sh" \
  "$TARGET" tutorials 01 hello-world "Hello World" \
  /tmp/test-blog-post-prompt.txt /tmp/test-blog-post-body.md /tmp/test-blog-post-summary.txt >/dev/null

echo
echo "=== Assertions ==="

# B1: page bundle exists with correct frontmatter
BUNDLE="$TARGET/content/docs/tutorials/01-hello-world/index.md"
if [[ -f "$BUNDLE" ]]; then
  pass "B1.a page bundle exists"
  grep -q '^title: "Hello World"$' "$BUNDLE" && pass "B1.b title set" || fail "B1.b title missing"
  grep -q '^weight: 2$' "$BUNDLE" && pass "B1.c weight = number+1 (2)" || fail "B1.c weight wrong"
  grep -q '^draft: false$' "$BUNDLE" && pass "B1.d draft: false" || fail "B1.d draft missing"
else
  fail "B1.a $BUNDLE missing"
fi

# B2: prompts entry appended
PROMPTS="$TARGET/prompt_for_images.yaml"
grep -q "key: tutorials-01" "$PROMPTS" && pass "B2.a prompts entry key present" || fail "B2.a prompts entry missing"
grep -q "Test prompt for hello-world cover image" "$PROMPTS" && pass "B2.b prompt body present" || fail "B2.b prompt body missing"

# B3: cover PNG generated
COVER="$TARGET/static/images/tutorials-01-cover.png"
if [[ -f "$COVER" ]]; then
  pass "B3.a cover PNG exists"
  file "$COVER" | grep -q "PNG image data" && pass "B3.b cover is a valid PNG" || fail "B3.b cover not a PNG"
else
  fail "B3.a cover PNG missing"
fi

# B4: overview updated
OVERVIEW="$TARGET/content/docs/tutorials/00-overview/index.md"
grep -q '^01\. \[Hello World\]' "$OVERVIEW" && pass "B4.a overview index has post 01 line" || fail "B4.a overview index entry missing"
grep -q '^| 01 | Hello World |' "$OVERVIEW" && pass "B4.b overview map row present" || fail "B4.b overview map row missing"

# B5: idempotency — re-running should be safe (the inserter is idempotent on overview;
# the page bundle would be overwritten; the prompts file would get a duplicate entry).
# Document this rather than assert on it.
echo "  NOTE: re-running with the same args overwrites the bundle and appends a"
echo "        duplicate prompts entry. Idempotency on prompts is the SKILL's job."

echo
echo "=== Summary ==="
echo "  $PASS_COUNT passed, $FAIL_COUNT failed"
[[ "$FAIL_COUNT" -eq 0 ]] && { echo "ALL OK"; exit 0; } || { echo "FAILED"; exit 1; }
