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

# Seed a reference image so the generator's reference branch is exercised (in
# real use bootstrap-blog Step 7 copies the operator's chosen reference). The
# helper no longer REQUIRES one — B6 below proves a reference-less blog still
# scaffolds (the generator's own precedence decides, #39).
#
# Note: this is a separately-rolled PNG from the one hardcoded in
# templates/hugo-hextra/scripts/generate-images.py's TEST_MODE
# (_ONE_PX_PNG bytes). The two paths never meet — this seeds reference.png
# as a generator input; that one writes the per-post cover —
# so byte-equality is not load-bearing. Don't compare-by-bytes between them.
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

# B2: prompts entry appended — scene-only, with the series selector field
PROMPTS="$TARGET/prompt_for_images.yaml"
grep -q "key: tutorials-01" "$PROMPTS" && pass "B2.a prompts entry key present" || fail "B2.a prompts entry missing"
grep -q "Test prompt for hello-world cover image" "$PROMPTS" && pass "B2.b scene present" || fail "B2.b scene missing"
grep -A2 "key: tutorials-01" "$PROMPTS" | grep -q "series: tutorials" && pass "B2.c series selector emitted" || fail "B2.c series selector missing"
# scene-only: the appended prompt block must be exactly the scene brief (one
# line here), not a pre-composed multi-layer prompt (#39 item 2)
ENTRY_PROMPT_LINES=$(sed -n '/key: tutorials-01/,/^  - key:\|^$/p' "$PROMPTS" | sed -n '/prompt: |/,$p' | sed '1d' | sed '/^[^ ]/q' | grep -c '[^[:space:]]' || true)
[[ "$ENTRY_PROMPT_LINES" -eq 1 ]] && pass "B2.d entry prompt is scene-only (1 line)" || fail "B2.d entry prompt has $ENTRY_PROMPT_LINES lines (expected scene-only)"

# B3: cover PNG generated
COVER="$TARGET/static/images/tutorials-01-cover.png"
if [[ -f "$COVER" ]]; then
  pass "B3.a cover PNG exists"
  # PNG magic bytes (\x89PNG\r\n\x1a\n) — no dependency on file(1), which is
  # absent on minimal images (audit M5).
  if [[ "$(head -c8 "$COVER" | od -An -tx1 | tr -d ' \n')" == "89504e470d0a1a0a" ]]; then
    pass "B3.b cover is a valid PNG"
  else
    fail "B3.b cover not a PNG"
  fi
else
  fail "B3.a cover PNG missing"
fi

# B4: the overview is page-derived — blog-post does NOT touch it; it lists posts
# via the {{< series-index >}} shortcode at build time.
OVERVIEW="$TARGET/content/docs/tutorials/00-overview/index.md"
grep -q '{{< series-index >}}' "$OVERVIEW" && pass "B4.a overview uses the series-index shortcode" || fail "B4.a overview missing series-index shortcode"
grep -q 'Hello World' "$OVERVIEW" && fail "B4.b blog-post wrongly edited the overview" || pass "B4.b overview left untouched by blog-post (page-derived)"

# B5: idempotency — re-running overwrites the bundle and appends a duplicate prompts
# entry (the overview is page-derived, so unaffected). Document rather than assert.
echo "  NOTE: re-running with the same args overwrites the bundle and appends a"
echo "        duplicate prompts entry. Idempotency on prompts is the SKILL's job."

# B6: a blog with NO reference image anywhere still scaffolds — the old helper
# hard-failed (exit 3) without static/images/reference.png (#39 item 1).
rm -f "$REF"
rm -rf "$TARGET/content/docs/tutorials/02-no-ref" "$TARGET/static/images/tutorials-02-cover.png"
if BLOG_CRAFT_TEST_MODE=1 "$REPO_ROOT/tools/blog-post-create.sh" \
  "$TARGET" tutorials 02 no-ref "No Ref" \
  /tmp/test-blog-post-prompt.txt /tmp/test-blog-post-body.md /tmp/test-blog-post-summary.txt >/dev/null; then
  [[ -f "$TARGET/static/images/tutorials-02-cover.png" ]] \
    && pass "B6.a reference-less blog scaffolds + generates" \
    || fail "B6.a cover missing on reference-less blog"
else
  fail "B6.a helper failed on a reference-less blog"
fi

echo
echo "=== Summary ==="
echo "  $PASS_COUNT passed, $FAIL_COUNT failed"
[[ "$FAIL_COUNT" -eq 0 ]] && { echo "ALL OK"; exit 0; } || { echo "FAILED"; exit 1; }
