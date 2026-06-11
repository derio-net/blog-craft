# Repo Audit & Improvement Plan — blog-craft (2026-06-11)

Auditor: Clawdia (principal-engineer audit pass, read-only).
Scope: full repo at commit `2eadff4`. All claims cite `file:line`. Smoke tests were
executed on a foreign Linux machine (not the author's Mac) as an empirical probe of
the portability claim; results are cited where relevant.

---

## Executive Summary

**Overall health grade: B.** For a small personal plugin repo this is unusually
disciplined: three executable smoke-test suites, an honest ARCHITECTURE.md with
dated schema verification, a clean Go renderer, and an idempotent media-fill helper
with a deliberate placeholder contract. Two of the three smoke suites pass unmodified
on a non-author Linux box — the portability claim is mostly real. The grade is held
back by a handful of genuine correctness bugs: the bootstrap "Hugo smoke check"
unconditionally swallows build failures (`tools/bootstrap-render.sh:51`, empirically
confirmed); the bootstrap skill's Step 8 instructs the agent to edit a prompts key
(`overview-<series>`) that the template never generates (`skills/bootstrap-blog/SKILL.md:134`
vs `templates/hugo-hextra/prompt_for_images.yaml.tmpl`); and the fourth skill
(`media-screenshots`) hard-depends on author-machine tooling that the plugin does not
ship, while README still claims the plugin "ships three skills" (`README.md:7`).
**Top 3 risks:** (1) silent scaffold breakage behind the swallowed smoke check,
(2) the phantom `overview-*` prompts key breaking the first image-gen flow a new user
encounters, (3) undocumented prerequisites (Hugo extended, Go ≥1.22 + network, python3,
`file(1)`) undermining the portability promise — one observed test failure
(`tests/smoke-blog-post.sh:93`, `file: command not found`).
**Top 3 opportunities:** (1) ~six one-line quick wins close most correctness findings,
(2) a tiny GitHub Actions job running the three existing smoke suites would lock in the
repo's best asset (its tests), (3) a "Prerequisites" section in both READMEs converts
the portability claim from implicit to verifiable.

---

## Repo Map

**Purpose.** A Claude Code plugin + template source ("plugin/template duality",
`docs/ARCHITECTURE.md:24-31`) that scaffolds Hugo + Hextra teaching blogs and ships
authoring skills that operate on any directory containing `.blog-craft.yaml`.

**Stack.** Bash helpers, one Go CLI (`text/template` renderer, only dep `gopkg.in/yaml.v3`
— `tools/render-template/go.mod`), two small Python utilities, Go-templated Hugo/Hextra
site templates, Markdown SKILL.md prompt files.

**Architecture sketch.** Wizard (SKILL.md, conversational) → answers YAML →
`tools/bootstrap-render.sh` → `tools/render-template/main.go` (3-pass render) →
target blog with `.blog-craft.yaml`. Later skills walk up from CWD to find that file
(`docs/ARCHITECTURE.md:44-65`). Zero runtime state in this repo.

**Key directories.**

| Path | Role |
|---|---|
| `.claude-plugin/` | plugin + marketplace manifests (v0.1.0) |
| `skills/{bootstrap-blog,blog-post,media,media-screenshots}/` | the four SKILL.md prompt files (+ one bundled script) |
| `templates/hugo-hextra/` | one-pass site template (`.tmpl` rendered, rest verbatim) |
| `templates/per-series-{always,overview}/` | per-series render passes |
| `tools/` | bash orchestrators, Go renderer, Python helpers |
| `tests/` | 3 smoke suites + fixture + render wrapper |
| `docs/ARCHITECTURE.md` | maintainer notes (schema provenance, design rationale) |

**Surprises.**
- The repo ships **four** skills; README and ARCHITECTURE both say three
  (`README.md:7`, `docs/ARCHITECTURE.md:28`).
- `tools/media-fill.py` and `skills/media-screenshots/scripts/media-fill.py` are
  byte-identical duplicates (verified by diff), acknowledged as a deliberate "mirror"
  (`skills/media-screenshots/SKILL.md:150-152`) but with no sync mechanism.
- There is no CI at all, despite three ready-to-run smoke suites.

---

## Audit Report

Severity legend: **C**ritical / **H**igh / **M**edium / **L**ow.
Each finding marked **[fact]** or **[judgment]**.

### Correctness / code quality

**H1 — Bootstrap's Hugo smoke check can never fail. [fact, empirically confirmed]**
`tools/bootstrap-render.sh:51`:
```bash
( cd "$TARGET" && hugo --buildDrafts --quiet 2>&1 | grep -v "^WARN" || true )
```
Under `set -euo pipefail` the trailing `|| true` masks any Hugo failure; the script
then prints `BOOTSTRAPPED OK` and exits 0. Verified: appending invalid TOML to a
scaffold's `hugo.toml` and running the same pipeline yields exit 0. This directly
contradicts the script's own header ("fail fast on template errors",
`tools/bootstrap-render.sh:8`) and the skill contract ("other non-zero = render or
Hugo error", `skills/bootstrap-blog/SKILL.md:114`). Consequence: a user can receive a
broken scaffold reported as success; the error text scrolls by but the exit-code
contract the agent relies on is dead. Severity: **High**.

**H2 — bootstrap-blog Step 8 targets a prompts key that does not exist. [fact]**
`skills/bootstrap-blog/SKILL.md:134` instructs: "replace the empty `prompt: ""` value
on the `overview-<first-series-key>` entry", and `:138` runs
`generate-images.py --only overview-<first-series-key>`. The rendered prompts file
contains only `tile-landing`, `tile-<key>`, `banner-landing`, `banner-<key>` keys
(`templates/hugo-hextra/prompt_for_images.yaml.tmpl:12-29`). `--only` with an unknown
key exits 1 with "Unknown keys"
(`templates/hugo-hextra/scripts/generate-images.py.tmpl`, `main()` `--only` validation).
The first optional image-gen flow a new user hits is guaranteed to fail. The overview
post template actually displays `tile-<key>.png`
(`templates/per-series-overview/00-overview/index.md.tmpl:9`), confirming `tile-*` is
the intended key. Severity: **High**.

**M1 — `title` is interpolated into YAML frontmatter unescaped. [fact]**
`tools/blog-post-create.sh:62` writes `title: "$TITLE"` and `:81` writes
`description: "Cover for $SERIES post $NUMBER — $TITLE"`. A title containing a double
quote (e.g. `Deploying "Frank" to prod`) produces invalid frontmatter and a Hugo build
error. The summary field gets quote-escaping two lines up (`:45`) — the asymmetry shows
the gap is an oversight, not a decision. Severity: **Medium**.

**M2 — Reference image is optional at bootstrap but a hard requirement at first post. [fact]**
The wizard offers `skip` for the reference image (`skills/bootstrap-blog/SKILL.md:62`),
but `tools/blog-post-create.sh:90-95` exits 3 if `static/images/reference.png` is
missing — *after* the user has already drafted/approved a body, summary, brief, and
prompt (Steps 4–7 of `skills/blog-post/SKILL.md`). The page bundle and prompts entry
are written before the failure (steps 1–2 of the helper precede the image-gen check),
leaving a half-created post plus an appended prompts entry that a retry will duplicate.
The blog-post SKILL.md never mentions the requirement. Severity: **Medium**.

**M3 — `generate-images.py` with no `--only` runs entries that are documented to fail. [fact]**
The prompts template marks all `banner-*` entries "do NOT run them through
generate-images.py — the API call will fail" (panoramic ratio unsupported,
`templates/hugo-hextra/prompt_for_images.yaml.tmpl:31-37`), yet the script's default
target set is *all* images and it has no skip mechanism for operator-generated or
empty-prompt entries (`generate-images.py.tmpl`, `targets = images` branch). A bare
`./scripts/generate-images.py --reference …` — the first usage line in its own
docstring — burns API calls on empty prompts and guaranteed-failing banner ratios.
Severity: **Medium**.

**M4 — Fresh scaffolds reference images that don't exist yet. [fact + judgment]**
`templates/hugo-hextra/layouts/partials/site-banner.html:1-19` unconditionally emits
`<img src=".../banner-landing.png">` on the homepage and `banner-<track>.png` on every
docs page, with no `fileExists`/resources check; `content/_index.md.tmpl:6` similarly
hardcodes `tile-landing.png`. Empirically, a fresh scaffold's homepage requests
`/test/images/banner-landing.png` and three `tile-*.png` files, none of which exist
until the operator generates them. [judgment] Acceptable as a "fill in your art"
workflow, but a silent 404 per page is a poor first-run experience and there's no
mention of it in the post-bootstrap recap (`skills/bootstrap-blog/SKILL.md:165-170`).
Severity: **Medium**.

**L1 — Stale/incorrect comments.** `tools/bootstrap-render.sh:28` claims the feature
flag is read "using a small Python one-liner" — it's `go run` (`:30`).
`tests/render-template.sh:14` says "brew Go (1.26.x)" while `bootstrap-render.sh:18`
says "≥1.22". `tests/smoke-blog-post.sh:58` is a dead line invoking a nonexistent
binary and ignoring the result. [facts] Severity: **Low**.

**L2 — Rendered files lose their mode bits. [fact]** `renderFile` uses `os.Create`
(default 0666 & umask) with no chmod (`tools/render-template/main.go:145-163`), while
`copyFile` preserves mode (`:179-182`). So `scripts/generate-images.py` lands non-
executable despite its shebang. Harmless today because all docs invoke it via
`python …`, but the shebang+usage line in its own docstring (`./scripts/generate-images.py`)
won't work. Severity: **Low**.

### Shell script quality & portability

**H3 — `media-screenshots` depends on tooling the plugin does not ship. [fact]**
`skills/media-screenshots/SKILL.md:89-99` requires the `browser-screenshot` skill at
`~/.agents/skills/browser-screenshot/scripts/capture.py`, the `browser-harness`
binary, and (on Mac) `brave-clawdia`/`brave-clawdia-stop`. None exist in this repo or
its manifests; they are the author's private environment. Any third-party install of
the plugin gets a skill whose core step cannot run, with no preflight check or
graceful "this skill requires X" gate. This is the largest single hole in the
"portable" claim (`README.md:3`). Severity: **High** (relative to the repo's stated
purpose).

**M5 — Hidden host-tool prerequisites; one observed failure. [fact]**
`tests/smoke-blog-post.sh:93` and `tests/smoke-media.sh` (M-asset checks), plus both
media SKILL.md flows (`skills/media/SKILL.md:104`,
`skills/media-screenshots/SKILL.md:135`) shell out to `file(1)`, which is absent on
minimal Linux images — observed: `tests/smoke-blog-post.sh: line 93: file: command not
found → FAIL: B3.b` on this audit machine, the suite's only failure. More broadly,
neither `README.md` nor the skills declare the real prerequisite set: Hugo (extended),
Go ≥1.22 **plus network access on first `go run`** (yaml.v3 module download,
`tools/bootstrap-render.sh:30,37`), `python3`, `curl`. Severity: **Medium**.

**L3 — macOS-flavored PATH pinning in shared scripts. [fact + judgment]**
`tools/bootstrap-render.sh:18` and `tests/render-template.sh:14` blindly prepend
`/usr/local/bin` ("ensure brew Go wins"). Harmless on Linux, but it's the authoring
machine leaking into portable tooling — and it's the *weaker* version of the
multi-location probe already done right in
`templates/hugo-hextra/scripts/hugo-serve.sh:15-27`. Severity: **Low**.

**L4 — `smoke-media.sh` M3's failure branch is unreachable. [fact]**
`tests/smoke-media.sh:99-104`: the Hugo build runs as a plain command under
`set -e`; if it fails the script aborts before the `if [[ "$?" -eq 0 ]]` check, so
"FAIL: M3" can never print. The test still *detects* failure (by dying), but the
pass/fail accounting and summary are skipped. Severity: **Low**.

### Skill prompt quality

**M6 — bootstrap-blog Step 8's skip condition is logically garbled. [fact]**
`skills/bootstrap-blog/SKILL.md:123`: "Skip silently if either of these is false:
`features.series_overview_posts` is `true`, OR a reference image was supplied." Read
literally ("if either is false … A-is-true OR B") this is unparseable — it mixes a
conjunction-of-preconditions with an OR. The intent is plainly "proceed only if
overview posts are enabled AND a reference image exists" (image-gen needs the
reference, `blog-post-create.sh:89-95`). An agent following the letter could attempt
Step 8 without a reference image and crash at generation. Severity: **Medium**.

**M7 — README/ARCHITECTURE say three skills; the plugin ships four. [fact]**
`README.md:7` ("ships three skills"), `docs/ARCHITECTURE.md:28` ("registers three
skills") vs `skills/media-screenshots/` (added in `15c7dda`/`3b982f0`). Since skills
are auto-discovered from `skills/<name>/SKILL.md` (`docs/ARCHITECTURE.md:19`),
media-screenshots *is* installed and model-invocable — its trigger description
(`skills/media-screenshots/SKILL.md:3`) is actually one of the best in the repo —
but the user-facing docs never mention it or its un-shipped dependencies. Severity:
**Medium** (docs accuracy).

**L5 — Frontmatter inconsistency across skills. [fact]** Three skills declare
`user-invocable`, `disable-model-invocation`, and `arguments`
(`skills/bootstrap-blog/SKILL.md:4-12`, `blog-post:4-19`, `media:4-10`);
`media-screenshots` declares none (`skills/media-screenshots/SKILL.md:1-4`). Works
(all fields optional) but the asymmetry invites copy-paste drift. Severity: **Low**.

**L6 — Minor doc drift inside blog-post SKILL. [fact]** Step 8's helper summary says
it runs `generate-images.py --only <key>` (`skills/blog-post/SKILL.md:126`) but the
helper actually adds `--reference static/images/reference.png`
(`tools/blog-post-create.sh:96`) — the omission hides the M2 requirement. The regen
snippet at `:139` uses `python` while the helper uses `python3`. Severity: **Low**.

### Template / scaffold correctness (Hugo + Hextra)

Verified empirically: a scaffold from the fixture builds and serves 200 under Hugo
v0.157.0 / Hextra v0.12.1 on Linux; the homepage card image written as absolute
`/images/tile-<key>.png` (`templates/hugo-hextra/content/_index.md.tmpl:26`) is
correctly rewritten to the `/test/` base path by Hextra's card shortcode — not a bug,
though it's stylistically inconsistent with `{{ .project.base_path }}images/…` used
six lines earlier (`:6`). The `[security]` URL-allowlist override is documented with
its rationale (`templates/hugo-hextra/hugo.toml.tmpl:53-58`) — mildly permissive but
reasonable. [judgment] The full `baseof.html` override
(`templates/hugo-hextra/layouts/baseof.html`) is copied from a specific Hextra version
to inject `site-banner.html`; a future `hugo mod get -u` can silently diverge from
upstream's baseof. Pinning is currently honest (`go.mod.tmpl` requires hextra
v0.12.1) so this is **Low** — worth a one-line comment in the file noting which Hextra
version it was copied from.

### Security

Healthy. No secrets in-repo; API keys come from env with an explicit "I will not
write it to disk" contract (`skills/blog-post/SKILL.md:107-111`); the
media-screenshots privacy review step (private names, masked values,
`skills/media-screenshots/SKILL.md:104-122`) is genuinely above the bar for this
class of tooling. The only note: `unsafe = true` Goldmark rendering
(`hugo.toml.tmpl:43`) is required for the HTML-in-Markdown patterns the templates use
— fine for a single-author blog. **No findings above Low.**

### Testing

The three smoke suites assert real behavior (file presence, frontmatter values, HTTP
200, idempotency, refusal exit codes) rather than mere execution — good. Gaps:
no CI runs them (no `.github/` at all) [fact]; the conversational wizard layer is
explicitly untested ("manually verified in Phase 6", `tests/smoke-bootstrap.sh:4-5`)
[fact, acceptable]; `media-fill.py` has no test for the documented ">" inside comment
body case that commit `30744ab` fixed — the regex now handles it
(`tools/media-fill.py:44-47`) but nothing pins the regression [fact]. Severity of the
CI gap: **Medium** for this maturity (the tests exist; running them is cheap).

### Dependencies

Minimal and healthy: one Go dep (yaml.v3, stable), Python stdlib + optional
pyyaml/pillow/google-genai documented in the scaffold README
(`templates/hugo-hextra/README.md.tmpl:18-26`), asciinema-player pinned at 3.9.0 via
CDN (`templates/hugo-hextra/layouts/partials/custom/head-end.html:8-9`). One sentence:
this dimension is fine.

### Strengths (preserve these)

- **Real executable tests in a prompt/skill repo** — rare and valuable; 21/22
  assertions passed on a foreign machine.
- **ARCHITECTURE.md provenance discipline** — dated schema verification with sample
  sources and a re-verification trigger (`docs/ARCHITECTURE.md:5-22`).
- **The `.tmpl`-vs-verbatim convention** and its rationale (Go templates matching
  Hugo's semantics, `docs/ARCHITECTURE.md:33-40`).
- **Idempotency as a designed property** — `insert-before-marker.py:29-33`,
  `media-fill.py` skip-if-missing semantics, bootstrap re-run refusal with a distinct
  exit code 2.
- **Honest scope cuts** — "what blog-craft does not ship" stated up front
  (`README.md:27`, `docs/ARCHITECTURE.md:71-76`).
- **hugo-serve.sh** is a model of the right way to handle environment variance
  (probe list + actionable warning), unlike the hardcoded PATH exports elsewhere.

---

## Improvement Strategy

**Theme 1 — Exit codes lie in two places (H1, M2-partial-state).**
Target state: every helper's exit code means what its header says; failures abort
before partial writes where feasible. Principle: agents *act on* exit codes — for an
agent-driven repo, a wrong exit code is worse than a crash.

**Theme 2 — Skill prose has drifted from the templates it drives (H2, M6, M7, L6).**
Target state: every key name, command, and precondition in a SKILL.md is mechanically
true of the current templates; the four-skill reality is documented. Principle: SKILL.md
files are executed by a literal-minded reader — treat them like code, and re-grep them
whenever a template key or helper signature changes.

**Theme 3 — Portability is claimed but not specified (H3, M5, L3).**
Target state: a Prerequisites section listing the exact host requirements (Hugo
extended ≥0.1xx, Go ≥1.22 + first-run network, python3, optional pngquant/asciinema),
and media-screenshots either gates on its private dependencies with a clear refusal or
is documented as author-environment-only. Principle: "portable" means a stranger can
predict failure modes before running, not that nothing ever fails.

**Theme 4 — The tests exist but nothing runs them (CI gap).**
Target state: a single GitHub Actions workflow (setup-go, setup-hugo, run the three
suites) failing the PR on regression. Principle: lock in the repo's best asset at the
cost of ~40 lines of YAML.

**Explicitly NOT recommending:** multi-SSG abstraction, theme wizard, deploy pipeline
(all correctly cut, `README.md:27`); a config-validation framework or JSON schema for
`.blog-craft.yaml` (the Go renderer's parse errors are adequate at this scale);
unit tests for the Go renderer (smoke coverage through it is sufficient);
de-duplicating the two `media-fill.py` copies via packaging machinery (a 2-line
"sync check" in CI is enough — the duplication is deliberate and documented).

**Definition of done:** all High findings closed; smoke suites green in CI on
ubuntu-latest; README lists prerequisites and four skills; zero contradictions between
SKILL.md instructions and rendered template contents (spot-check: every `--only` key
named in a skill exists in `prompt_for_images.yaml.tmpl`).

---

## Task Plan

### Quick wins (do immediately — all S, all low-risk)

| # | Task | Files |
|---|------|-------|
| QW1 | Fix the swallowed smoke check: drop `|| true`, keep WARN filtering without masking exit (`hugo … 2>&1 | { grep -v '^WARN' || true; }; exit "${PIPESTATUS[0]}"` or capture output and test `$?`) | `tools/bootstrap-render.sh:51` |
| QW2 | Fix Step 8's phantom key: `overview-<first-series-key>` → `tile-<first-series-key>` (both occurrences), and rewrite the skip-condition sentence as "Run only if series_overview_posts is true AND a reference image was supplied; otherwise skip silently." | `skills/bootstrap-blog/SKILL.md:123,134,138` |
| QW3 | Escape `$TITLE` like `$SUMMARY` before frontmatter/description interpolation | `tools/blog-post-create.sh:62,81` (escape near `:45`) |
| QW4 | README: add Prerequisites section (hugo extended, go ≥1.22 + network on first run, python3, optional pngquant/optipng/asciinema/file) and document the fourth skill incl. its external deps; bump the "three skills" sentence in ARCHITECTURE.md | `README.md`, `docs/ARCHITECTURE.md:28` |
| QW5 | Guard `file(1)` usage: `command -v file >/dev/null && file … || echo "skip: file(1) not installed"` in the test; same pattern in the two SKILL.md snippets | `tests/smoke-blog-post.sh:93`, `skills/media/SKILL.md:104`, `skills/media-screenshots/SKILL.md:135` |
| QW6 | Delete the dead line and fix the two stale comments ("Python one-liner", "1.26.x") | `tests/smoke-blog-post.sh:58`, `tools/bootstrap-render.sh:28`, `tests/render-template.sh:14` |

### Milestone 0 — Safety net

**T0.1 — CI workflow running the three smoke suites.** (M, low risk, no deps)
`.github/workflows/smoke.yml`: checkout, `actions/setup-go`, install hugo extended
(e.g. `peaceiris/actions-hugo`), `sudo apt-get install -y file`, run
`tests/smoke-bootstrap.sh && tests/smoke-blog-post.sh && tests/smoke-media.sh`.
Add a 4th step: `diff tools/media-fill.py skills/media-screenshots/scripts/media-fill.py`
(the mirror-sync check). Acceptance: workflow green on main; a deliberate template
breakage on a branch turns it red. *Do QW1 first or the bootstrap suite can't catch
Hugo regressions.*

### Milestone 1 — Critical fixes (correctness)

**T1.1 — QW1 + QW2 + QW3** (see above). Acceptance: corrupting a rendered
`hugo.toml` makes `bootstrap-render.sh` exit non-zero; `--only tile-<key>` path works
end-to-end in TEST_MODE; a title containing `"` round-trips through
`blog-post-create.sh` to a Hugo-buildable bundle (add one assertion to
`tests/smoke-blog-post.sh`).

**T1.2 — Move the reference-image check to the front of blog-post.** (S, low risk)
Two changes: in `tools/blog-post-create.sh`, hoist the `reference.png` existence check
(`:89-95`) above the page-bundle write (`:57`) so failure leaves no partial state; in
`skills/blog-post/SKILL.md`, add the check to Step 1 ("validate the blog") so the
agent refuses before the user invests in drafting. Acceptance: running the helper
without a reference image writes nothing and exits 3; SKILL Step 1 names the
requirement. Depends on: nothing.

**T1.3 — Make `generate-images.py` skip empty-prompt and operator-generated entries.**
(S–M, low risk) Skip any entry with empty `prompt` (warn, don't fail) and support an
explicit `operator_generated: true` flag emitted by
`prompt_for_images.yaml.tmpl` for `banner-*` entries; default run then matches the
file's own "do NOT run" comments. Acceptance: bare
`generate-images.py --reference …` in TEST_MODE generates tiles only.
Files: `templates/hugo-hextra/scripts/generate-images.py.tmpl`,
`templates/hugo-hextra/prompt_for_images.yaml.tmpl`.

### Milestone 2 — High-leverage improvements

**T2.1 — Gate media-screenshots on its dependencies.** (S, no risk) Add a "Step 0 —
preflight" to `skills/media-screenshots/SKILL.md`: check `browser-harness` on PATH and
the browser-screenshot skill dir exist; if not, refuse with install pointers and
offer the manual `/media` flow instead. Also add the missing frontmatter fields (L5)
for consistency. Acceptance: on a machine without the harness, the skill produces a
one-paragraph refusal, not a mid-flow crash.

**T2.2 — Missing-art grace.** (M, low template risk) Wrap `site-banner.html`'s `<img>`
and the homepage `tile-landing.png` in `{{ if fileExists … }}` (or
`resources.Get`) so a fresh scaffold renders clean with zero 404s; mention pending
art in the bootstrap recap (`skills/bootstrap-blog/SKILL.md:165-170`). Acceptance:
fresh-scaffold homepage HTML contains no references to nonexistent images
(extend `tests/smoke-bootstrap.sh` with a grep on `public/index.html`).

**T2.3 — Generalize the brew-PATH pin.** (S, low risk) Replace the
`export PATH="/usr/local/bin:$PATH"` lines in `tools/bootstrap-render.sh:18` and
`tests/render-template.sh:14` with the `GO_LOCATIONS` probe already proven in
`templates/hugo-hextra/scripts/hugo-serve.sh:15-27` (extract to a tiny sourced
`tools/lib/go-path.sh` or duplicate the 10 lines). Acceptance: smoke suites pass on a
Linux box whose Go is not in `/usr/local/bin` (this audit machine qualifies).

### Milestone 3 — Quality & polish

| Task | Effort | Notes |
|---|---|---|
| T3.1 Fix unreachable M3 fail branch (`tests/smoke-media.sh:99-104`) — run build with `if ! (…)` | S | test-only |
| T3.2 Preserve mode bits in `renderFile` (chmod from source info, `main.go:145-163`) | S | or drop the shebang/`./` usage line from generate-images docstring |
| T3.3 Note the Hextra version `baseof.html` was copied from, in a comment | S | upgrade aid |
| T3.4 Pin a regression test for the `>`-in-comment-body media-fill case (commit `30744ab`) | S | add a third placeholder to `tests/smoke-media.sh` |
| T3.5 Align `python` vs `python3` across SKILL.md / helper / scaffold README | S | cosmetic |

### Top-3 implementation sketches

**QW1/T1.1 (swallowed smoke check).** Replace `bootstrap-render.sh:51` with:
```bash
set +e
out=$(cd "$TARGET" && hugo --buildDrafts --quiet 2>&1)
rc=$?
set -e
printf '%s\n' "$out" | grep -v '^WARN' || true
if [[ $rc -ne 0 ]]; then echo "ERROR: hugo smoke build failed (exit $rc)" >&2; exit 1; fi
```
Gotcha: keep exit code 2 reserved for the preflight refusal (`:24`) — use 1 here so
the SKILL.md contract (`skills/bootstrap-blog/SKILL.md:114`) stays true. Add a
negative test to `tests/smoke-bootstrap.sh` (corrupt `hugo.toml` in a throwaway copy,
assert non-zero).

**QW2/M6 (Step 8 rewrite).** Single-file edit to `skills/bootstrap-blog/SKILL.md`.
Replace line 123 with: "Run this step only if **both** hold: `features.series_overview_posts`
is `true` **and** a reference image was supplied in Step 2. Otherwise skip silently."
Replace `overview-<first-series-key>` with `tile-<first-series-key>` at `:134` and
`:138`. Gotcha: the tile is shared between homepage card and overview cover
(`prompt_for_images.yaml.tmpl:8-10` comment) — the user prompt text at `:127-129`
should say "series tile (used as the overview cover and homepage card)" so the scene
brief fits both uses.

**T0.1 (CI).** ~40-line workflow; matrix not needed. Steps: checkout → setup-go
(1.22.x) → install hugo extended ≥0.157 → `apt-get install file` → run three suites →
mirror-diff check. Gotcha: `smoke-bootstrap.sh` binds an ephemeral port and polls
localhost — works on hosted runners, but give the A3 poll loop headroom (it already
allows 15 s; first `go run` downloads modules, so warm the module cache with
`go run . --check --answers tests/fixtures/answers-frank-like.yaml` before timing-
sensitive steps). Do QW1 first so the suite can actually catch Hugo failures.

---

## Open Questions

1. **Is `media-screenshots` meant to be public?** It is the only skill that cannot
   work outside the author's environment (H3). Options: gate it (T2.1), move it to a
   private overlay repo, or ship/point to the `browser-screenshot` dependency. Owner
   intent decides which.
2. **Banner workflow ergonomics:** banners are operator-generated by API limitation
   (`prompt_for_images.yaml.tmpl:31-37`). Is the long-term plan to wait for panoramic
   API support, or should the scaffold default to *no* site-banner partial until art
   exists (stronger version of T2.2)?
3. **Hextra upgrade policy:** `baseof.html` is a full-theme override copied at
   v0.12.1. Should scaffolds pin Hextra (current behavior, safe) or is `hugo mod get -u`
   in the scaffold README (`README.md.tmpl:10`) an invitation to drift? Recommend
   removing `-u` from the first-time instruction if pinning is the policy.
4. **Marketplace versioning:** `plugin.json`/`marketplace.json` both say 0.1.0 while
   features (media-screenshots, banners) have landed since. Is there a release/bump
   convention you want enforced (e.g. CI check that version changed when `skills/`
   changed)?
