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

# Operator edit to a merged file (README line 1). (-i.bak: portable across
# GNU and BSD/macOS sed — bare -i is GNU-only and silently no-ops the edit
# path on macOS.)
sed -i.bak '1s/.*/# OPERATOR RENAMED BLOG/' "$LOCAL/README.md" && rm -f "$LOCAL/README.md.bak"
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

echo "=== frank-shaped blog: site_dir mapping + --only scoping (spec D6) ==="
# A blog with config at the root and the Hugo site under blog/ (frank's shape,
# #39 item 4): scoped update replaces the vendored scripts under blog/scripts/
# and touches nothing else.
FR="$W/frank"
mkdir -p "$FR/blog/scripts" "$FR/blog/content/docs"
cp -r "$BASE/." "$FR/blog/"
rm -f "$FR/blog/.blog-craft.yaml"
"$PY" - "$BASE" "$FR" <<'PY'
import sys, yaml
base, fr = sys.argv[1], sys.argv[2]
cfg = yaml.safe_load(open(base + "/.blog-craft.yaml"))
cfg["site_dir"] = "blog"
cfg["image"]["prompts_file"] = "blog/prompt_for_images.yaml"
yaml.safe_dump(cfg, open(fr + "/.blog-craft.yaml", "w"))
PY
echo "STALE VENDORED COPY" > "$FR/blog/scripts/generate-images.py"
SENTINEL_CONTENT="$FR/blog/content/docs/keep.md"; echo "operator content" > "$SENTINEL_CONTENT"

FR_ACTIONS=$("$PY" - "$REPO_ROOT" "$FR" "$STG" <<'PY'
import sys, yaml
sys.path.insert(0, sys.argv[1] + "/tools")
from update import plan_update, apply_plan, default_manifest
fr, stg = sys.argv[2], sys.argv[3]
cfg = yaml.safe_load(open(fr + "/.blog-craft.yaml"))
plan = plan_update(fr, stg, None, default_manifest(), cfg=cfg, only=["scripts/**"])
apply_plan(fr, stg, plan)
print(";".join(f"{e['dest']}={e['action']}" for e in plan))
PY
)
echo "  actions: $FR_ACTIONS"
grep -q "blog/scripts/generate-images.py=replace" <<<"$FR_ACTIONS" && pass "site_dir: vendored script replaced under blog/" || fail "site_dir mapping missed blog/scripts"
grep -vq "layouts" <<<"$FR_ACTIONS" && pass "--only scoped the plan to scripts/**" || fail "--only leaked non-script paths"
grep -q "STALE VENDORED COPY" "$FR/blog/scripts/generate-images.py" && fail "vendored script not actually replaced" || pass "vendored script content updated on disk"
grep -q "operator content" "$SENTINEL_CONTENT" && pass "content untouched by scoped update" || fail "scoped update touched content"
[[ -e "$FR/scripts/generate-images.py" ]] && fail "wrote outside site_dir" || pass "nothing written outside site_dir"

echo
echo "=== Summary: $pass_n passed, $fail_n failed ==="
[[ "$fail_n" -eq 0 ]] && echo "ALL OK" || { echo "FAILED"; exit 1; }
