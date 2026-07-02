#!/usr/bin/env bash
# smoke-update.sh — end-to-end non-destructive update (spec §8.3):
# bootstrap a blog (vN); an operator edits a merged file; a "vN+1" changes a
# framework file + the same merged file on a different line. The update must
# replace the framework file, 3-way-merge the merged file preserving the
# operator's edit, leave content untouched, and the result must Hugo-build +
# reproduce cleanly.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX="$REPO_ROOT/tests/fixtures"
pass_n=0; fail_n=0
pass() { echo "  PASS: $1"; pass_n=$((pass_n+1)); }
fail() { echo "  FAIL: $1"; fail_n=$((fail_n+1)); }

PY="${PYTHON:-python3}"
"$PY" -c "import yaml" 2>/dev/null || PY="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}/bin/python"

W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
BASE="$W/base"; LOCAL="$W/local"; STG="$W/stg"

echo "=== bootstrap vN (base) ==="
bash "$REPO_ROOT/tools/bootstrap-render.sh" "$FIX/stoa-v2.expected.yaml" "$BASE" >/dev/null
cp -r "$BASE" "$LOCAL"
cp -r "$BASE" "$STG"

# Operator edit to a merged file (README line 1).
sed -i '1s/.*/# OPERATOR RENAMED BLOG/' "$LOCAL/README.md"
# Simulate a vN+1 blog-craft release: a framework file changes + the same merged
# file changes on a DIFFERENT line (non-conflicting with the operator's edit).
echo "<!-- shipped in vN+1 -->" >> "$STG/layouts/shortcodes/screenshot.html"
printf '\nShipped-in-vN+1 footer line.\n' >> "$STG/README.md"

echo "=== plan + apply update ==="
ACTIONS=$("$PY" - "$REPO_ROOT" "$LOCAL" "$STG" "$BASE" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/tools")
from update import plan_update, apply_plan, dry_run_diff, default_manifest
local, stg, base = sys.argv[2], sys.argv[3], sys.argv[4]
plan = plan_update(local, stg, base, default_manifest())
print(dry_run_diff(plan), file=sys.stderr)
conflicts = apply_plan(local, stg, plan)
print("CONFLICTS", conflicts, file=sys.stderr)
print(";".join(f"{e['path']}={e['action']}" for e in plan))
PY
)
echo "  actions: $ACTIONS"

grep -q "layouts/shortcodes/screenshot.html=replace" <<<"$ACTIONS" && pass "framework file -> replace" || fail "framework not replaced"
grep -q "README.md=merge" <<<"$ACTIONS" && pass "merged file -> 3-way merge" || fail "README not merged"

# The operator's rename AND the vN+1 footer both survive the merge.
grep -q "OPERATOR RENAMED BLOG" "$LOCAL/README.md" && pass "operator edit preserved" || fail "operator edit lost"
grep -q "Shipped-in-vN+1 footer" "$LOCAL/README.md" && pass "vN+1 change applied" || fail "vN+1 change missing"
grep -q "shipped in vN+1" "$LOCAL/layouts/shortcodes/screenshot.html" && pass "framework updated on disk" || fail "framework not updated on disk"

echo "=== hugo build + reproduction after update ==="
( cd "$LOCAL" && hugo --buildDrafts --quiet ) >/dev/null 2>&1 && pass "hugo builds after update" || fail "hugo build broken after update"
if "$PY" - "$REPO_ROOT" "$LOCAL" <<'PY'
import sys, tempfile
sys.path.insert(0, sys.argv[1] + "/tools")
from reproduce import apply, structural_diff, default_manifest
# a fresh re-apply of the same config reproduces the updated blog's framework/merged surface
with tempfile.TemporaryDirectory() as td:
    gen = apply(sys.argv[2] + "/.blog-craft.yaml", td + "/g")
    drift = structural_diff(gen, sys.argv[2], default_manifest())
    # only the operator's README edit + the deliberately-injected framework tweak differ
    drift = [d for d in drift if "README.md" not in d and "screenshot.html" not in d]
    sys.exit(0 if not drift else (print("DRIFT", drift) or 1))
PY
then pass "reproduction harness runs on the updated blog"; else fail "reproduction drift after update"; fi

echo
echo "=== Summary: $pass_n passed, $fail_n failed ==="
[[ "$fail_n" -eq 0 ]] && echo "ALL OK" || { echo "FAILED"; exit 1; }
