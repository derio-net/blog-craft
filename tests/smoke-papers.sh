#!/usr/bin/env bash
# smoke-papers.sh — end-to-end papers content-type: bootstrap a papers blog,
# scaffold a paper, prove the dossier gate (pass + fail), validate frontmatter,
# Hugo-build clean, and confirm a non-papers blog materializes none of it.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX="$REPO_ROOT/tests/fixtures"
pass_n=0; fail_n=0
pass() { echo "  PASS: $1"; pass_n=$((pass_n+1)); }
fail() { echo "  FAIL: $1"; fail_n=$((fail_n+1)); }

# Python with pyyaml (blogs use their venv; fall back to the unit-test venv).
PY="${PYTHON:-python3}"
"$PY" -c "import yaml" 2>/dev/null || PY="${BLOG_CRAFT_TEST_VENV:-/tmp/blog-craft-unit-venv}/bin/python"
export PYTHON="$PY"

WORK="$(mktemp -d)"; TARGET="$WORK/blog"
trap 'rm -rf "$WORK"' EXIT
CFG="$TARGET/.blog-craft.yaml"

echo "=== bootstrap papers blog ==="
bash "$REPO_ROOT/tools/bootstrap-render.sh" "$FIX/answers-papers-v2.yaml" "$TARGET" >/dev/null

echo "=== scaffold + dossier gate ==="
bash "$REPO_ROOT/tools/scaffold-paper.sh" --config "$CFG" 1 test-paper >/dev/null
BUNDLE="$TARGET/content/docs/papers/01-test-paper/index.md"
DOSSIER="$TARGET/docs/papers-dossiers/01-test-paper/dossier.md"
[[ -f "$BUNDLE" && -f "$DOSSIER" ]] && pass "P1 scaffold created bundle + dossier" || fail "P1 scaffold outputs missing"

# Short (default) dossier fails the gate.
if "$PY" "$REPO_ROOT/tools/validate_dossier.py" --config "$CFG" "$DOSSIER" >/dev/null 2>&1; then
  fail "P3 short dossier unexpectedly PASSED the gate"
else
  pass "P3 short dossier FAILS the gate (as expected)"
fi

# A filled dossier passes.
cat > "$DOSSIER" <<'D'
---
paper: 01-test-paper
status: ready
vendors:
  - {name: A}
  - {name: B}
  - {name: C}
primary_sources:
  - {title: s1, type: vendor-docs, url: "http://e/1"}
  - {title: s2, type: paper, url: "http://e/2"}
  - {title: s3, type: postmortem, url: "http://e/3"}
  - {title: s4, type: talk, url: "http://e/4"}
  - {title: s5, type: benchmark, url: "http://e/5"}
artefacts:
  - {kind: yaml}
  - {kind: commit}
  - {kind: incident}
gaps: ["a gap"]
counter_arguments: ["a counter"]
---
# filled
D
if "$PY" "$REPO_ROOT/tools/validate_dossier.py" --config "$CFG" "$DOSSIER" >/dev/null 2>&1; then
  pass "P2 filled dossier PASSES the gate"
else
  fail "P2 filled dossier failed the gate"
fi

# Frontmatter validator accepts the fresh bundle (weight invariant + presence).
if "$PY" "$REPO_ROOT/tools/validate_papers.py" --config "$CFG" "$BUNDLE" >/dev/null 2>&1; then
  pass "P4 paper frontmatter valid"
else
  fail "P4 paper frontmatter invalid"
fi

echo "=== hugo build ==="
if ( cd "$TARGET" && hugo --buildDrafts --quiet ) >/dev/null 2>&1; then
  pass "P5 hugo build clean with a papers post"
else
  fail "P5 hugo build failed"
fi

echo "=== non-papers blog materializes no papers assets ==="
STOA="$WORK/stoa"
"$PY" -c "import yaml,sys; yaml.safe_dump(yaml.safe_load(open('$FIX/stoa-v2.expected.yaml')), open('$WORK/stoa.yaml','w'))"
bash "$REPO_ROOT/tools/bootstrap-render.sh" "$WORK/stoa.yaml" "$STOA" >/dev/null
if [[ -e "$STOA/layouts/shortcodes/papers" ]]; then
  fail "P6 papers assets leaked into a non-papers blog"
else
  pass "P6 non-papers blog has no papers assets"
fi

echo
echo "=== Summary: $pass_n passed, $fail_n failed ==="
[[ "$fail_n" -eq 0 ]] && echo "ALL OK" || { echo "FAILED"; exit 1; }
