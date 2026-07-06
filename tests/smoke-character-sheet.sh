#!/usr/bin/env bash
# Smoke test for scripts/gen-character-sheet.py + scripts/build-gallery.py.
#
# Bootstraps a blog fixture, then (in BLOG_CRAFT_TEST_MODE, no API calls) asserts
# gen-character-sheet.py archives candidates + a contact sheet under
# .regen-archive/reference/, and build-gallery.py renders a self-contained
# gallery.html from them. Skips cleanly if PyYAML/Pillow aren't available.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ANSWERS=${1:-"$REPO_ROOT/tests/fixtures/answers-frank-like.yaml"}
TARGET=${2:-"/tmp/test-bootstrap-fixture"}
PYBIN="${PYTHON:-python3}"

if ! "$PYBIN" -c 'import yaml, PIL' 2>/dev/null; then
  echo "SKIP: smoke-character-sheet needs PyYAML + Pillow ($PYBIN -c 'import yaml, PIL' failed)"
  exit 0
fi

# Bootstrap fixture if needed (rendered blog carries scripts/ + .blog-craft.yaml).
if [[ ! -f "$TARGET/.blog-craft.yaml" ]]; then
  rm -rf "$TARGET"
  "$REPO_ROOT/tools/bootstrap-render.sh" "$ANSWERS" "$TARGET" >/dev/null
fi

for f in scripts/gen-character-sheet.py scripts/build-gallery.py; do
  [[ -f "$TARGET/$f" ]] || { echo "FAIL: rendered blog missing $f"; exit 1; }
done

rm -rf "$TARGET/.regen-archive/reference"

# 1. Generate 3 candidates (1x1 PNGs in test mode → may collapse to one archived
#    file by content hash; we assert the pipeline + contact sheet, not a count).
( cd "$TARGET" && BLOG_CRAFT_TEST_MODE=1 "$PYBIN" scripts/gen-character-sheet.py 3 >/dev/null )

ADIR="$TARGET/.regen-archive/reference"
compgen -G "$ADIR/reference-*.png" >/dev/null || { echo "FAIL: no archived candidate at $ADIR"; exit 1; }
[[ -f "$ADIR/contact-sheet.png" ]] || { echo "FAIL: no contact-sheet.png"; exit 1; }

# 2. Build the selection gallery from the candidates.
( cd "$TARGET" && "$PYBIN" scripts/build-gallery.py >/dev/null )
[[ -f "$ADIR/gallery.html" ]] || { echo "FAIL: build-gallery.py produced no gallery.html"; exit 1; }
grep -q "Choose a character sheet" "$ADIR/gallery.html" || { echo "FAIL: gallery.html missing expected heading"; exit 1; }

echo "PASS: smoke-character-sheet (candidates + contact sheet + gallery.html)"
