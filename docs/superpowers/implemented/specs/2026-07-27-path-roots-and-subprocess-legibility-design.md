# Materialized-path roots + legible renderer failures

- **Issues:** derio-net/blog-craft#59, derio-net/blog-craft#61
- **Branch:** `vk/e653-fix-blog-raft-59`
- **Date:** 2026-07-27
- **Type:** fix (path model + relocation machinery + subprocess legibility + CI
  template + docs + tests)

## Goal

Two bugs, both of the same family: **a path is resolved against the wrong root,
and nothing says so.**

- **#59** — `/update`'s *documented* invocation (`--config .blog-craft.yaml
  --blog .`) always fails, because the relative config path is threaded verbatim
  into `bootstrap-render.sh`, which resolves it after an internal `cd`. The
  renderer prints the reason to stderr; `reproduce.py` captures the stream and
  never surfaces it, so the operator gets a bare stdlib `CalledProcessError`.
- **#61** — for a blog whose `site_dir` is not the repo root, `map_dest`
  relocates `.github/**` under `<site_dir>/`, where GitHub Actions never looks.
  The shipped CI file is an inert YAML document that looks exactly like a
  workflow. No error, no skipped run, no empty check.

The operator asked for **the more general fix in each case** — fix the root
cause where it lives, and audit for the rest of the family rather than patching
the two reported instances.

## Operator decisions (assumed — see §"Decisions taken without a Q&A")

fr-goal's batched Q&A could not run: this session is a headless runner with no
interactive channel. Blocking would have delivered nothing, and the largest
question was pre-answered in the goal text. The four operator-owned calls are
taken as stated defaults and surfaced in the PR body for review:

1. **Relocate + prune**, not report-only (D2 below).
2. **Ship the hookify rule at hookify's real discovery path** (D3).
3. **Minor version bump**, 0.13.1 → 0.14.0 (D4).
4. **Post-merge Test Plan runs against `derio-net/frank`** (D5).

---

## Part A — #59: paths and legibility

### A1. The `cd` is the bug; fix it where it lives

`bootstrap-render.sh` runs the Go renderer inside ten
`( cd "$RENDERER_DIR" && … )` subshells (the one-pass render, per-series ×2, the
two content-type gates, the three feature gates, and the two `--get-bool`/`--has`
probes). Every `--answers "$ANSWERS"` and `--dst "$TARGET"` inside those
subshells is resolved against `tools/render-template/`, not the caller's CWD.
That is why
`--config .blog-craft.yaml` fails and `--config "$PWD/.blog-craft.yaml"` works.

**Fix at the source:** `bootstrap-render.sh` resolves `$ANSWERS` and `$TARGET`
to absolute paths immediately after argument parsing, before anything `cd`s.
This is the most general form — it fixes every caller at once, including a human
running the renderer by hand (which #59 notes is exactly what diagnosing it
requires today).

Ordering constraints, verified against the current script:

- `$ANSWERS` is read (`grep -qE '^blog_craft_version:'`) and possibly replaced
  by an absolute `mktemp` copy *before* the first `cd` — resolving first is safe
  and keeps the stamping path unchanged.
- `$TARGET` is `mkdir -p`'d before the first `cd`; resolving it must therefore
  happen *after* the directory exists, or use a resolver that does not require
  existence. The preflight (`if [[ -f "$TARGET/.blog-craft.yaml" ]]`) must keep
  running against the same location.

### A2. Resolve at the Python API boundary too

Belt and braces, and it fixes library callers that never touch the CLI:

- `reproduce.apply(config_path, scratch_dir)` — resolve both before handing them
  to `bash`.
- `update.render_staging` / `update.base_by_rerender` — same.

### A3. The full path-argument audit (#59 asked for the family, not the instance)

| Site | Argument | Threaded into | Verdict |
|---|---|---|---|
| `update.py:_main` | `--config` | `bootstrap-render.sh` (cd) | **broken** — the reported bug |
| `update.py:_main` | `--blog` | `Path` joins only | latent; resolve for consistency |
| `update.py:_main` | `--base` | `Path` joins only | latent; resolve |
| `update.py:base_by_rerender` | `config` | `bootstrap-render.sh` (cd) | **broken** — second instance, same call |
| `reproduce.py:_main` | `--config` | `bootstrap-render.sh` (cd) | **broken** — third instance, never reported |
| `reproduce.py:_main` | `--scratch` | `--dst` inside the cd subshell | **broken** — fourth instance, never reported |
| `reproduce.py:_main` | `--reference` | `Path` joins only | latent; resolve |
| `reproduce.py:render_and_diff` | `root_a/root_b` | `cwd=` for hugo | correct as-is |

`reproduce.py --config … --scratch …` carries the identical break and is not
mentioned in #59. That is the payoff of auditing the family.

### A4. Make subprocess failures legible

A shared helper, `tools/proc.py`:

```python
run_checked(cmd, **kw) -> CompletedProcess
```

— runs the command capturing both streams, and on a non-zero exit raises
`CommandFailed` (a `subprocess.CalledProcessError` subclass, so existing
`except CalledProcessError` handlers keep working) whose `str()` carries the
command, the exit code, and the captured stderr/stdout. The one line the
renderer already prints (`load answers: open .blog-craft.yaml: no such file or
directory`) becomes the first thing the operator reads.

Swallowed-site audit — every `check=True, capture_output=True` whose streams are
discarded:

| Site | Command | Failure the operator currently cannot see |
|---|---|---|
| `reproduce.py:32` | `bootstrap-render.sh` | the reported one |
| `reproduce.py:98` | `hugo --buildDrafts` | a template error in `render_and_diff` |
| `update.py:143` | `git archive <blog_craft_version>` | **an unreachable tag** — the exact failure the `/update` guardrail "keep `blog_craft_version` accurate" warns about |
| `update.py:147` | `bootstrap-render.sh` (at the old tag) | a renderer regression at the recorded release |

All four move to `run_checked`. `update.py:146` (`tar -xf`, `check=True` with no
capture) already reaches the terminal — left alone.

`tools/proc.py` is *not* mirrored into blogs (`tools/update.py`,
`tools/reproduce.py` and `tools/path_ownership.py` are plugin-only), so it adds
no row to `test_mirrors.py`.

---

## Part B — #61: model the root, don't extend the allowlist

### B1. The question the manifest could not answer

`map_dest` hard-codes three config-rooted special cases and site-prefixes
everything else. The distinction it is groping for is not "dotfile" and not
"special case" — it is:

> **Who defines this path's location — the Hugo site, or a tool that reads it
> from the repository root?**

`.github/workflows/` is defined by GitHub. `.claude/hookify.*.local.md` is
defined by Claude Code. Neither has anything to do with where Hugo lives. That
question gets a first-class, declared answer.

### B2. `roots:` in `templates/manifest.yaml`

The manifest already declares path *ownership* (framework / merged / content)
with a completeness guard (`test_no_unclassified_materialized_path`). It gains a
parallel section declaring path *root*, with the same shape and the same guard:

```yaml
roots:
  repo:      # a tool outside Hugo locates this from the REPOSITORY root
    - ".blog-craft.yaml"
    - "prompt_for_images.yaml"
    - ".reference-pool/**"
    - ".github/**"
    - ".claude/**"
  site:      # Hugo defines it -> lands under `site_dir`
    - "layouts/**"
    - "assets/**"
    - "content/**"
    - "static/**"
    - "data/**"
    - "scripts/**"
    - "fonts/**"
    - "hugo.toml"
    - "go.mod"
    - "go.sum"
    - "README.md"
    - "MEDIA-GUIDE.md"
    - ".gitignore"
```

`map_dest` consults it: `repo` → unprefixed; `site` → `<site_dir>/<path>`. The
two config-*declared* relocations (`.reference-pool/**` → `image.reference_pool`,
`prompt_for_images.yaml` → `image.prompts_file`) stay in code — they are
repo-rooted *and* renameable by a config key — and their manifest rows record
the root that makes them unprefixed.

**The audit, recorded.** Every materialized path, against B1's question:

| Path | Root | Who defines the location |
|---|---|---|
| `.github/**` | repo | GitHub Actions — `<repo>/.github/workflows/` only. **Was wrong.** |
| `.claude/**` | repo | Claude Code / hookify — globs from the project root. **Was wrong** (see B4). |
| `.blog-craft.yaml` | repo | blog-craft — it *is* the config root |
| `prompt_for_images.yaml` | repo | the config (`image.prompts_file`) |
| `.reference-pool/**` | repo | the config (`image.reference_pool`) |
| `.gitignore` | site | git — nested `.gitignore` applies to its own subtree, so a site-scoped one is correct |
| `README.md` | site | it is the *site's* readme; a repo README is the operator's |
| `MEDIA-GUIDE.md` | site | documents the site's image workflow |
| `hugo.toml`, `go.mod`, `go.sum` | site | Hugo / Hugo Modules, resolved from the site root |
| `layouts/**`, `assets/**`, `content/**`, `static/**`, `data/**` | site | Hugo's own directory contract |
| `scripts/**` | site | invoked as `<site_dir>/scripts/…`; resolve their config-declared paths against the config root, so they run from anywhere |
| `fonts/**` | site | consumed by `assets/css` |

**Fail-safe at runtime, enforcing at review time.** `map_dest` treats an
undeclared path as `site` — byte-identical to today's behaviour, so no blog can
be broken by a template file someone forgets to declare. The *enforcement* lives
in `tests/unit/test_path_roots.py`, which asserts every materialized path matches
**exactly one** root, so a new template file cannot be merged without a reviewer
answering B1's question. That is what makes the audit durable rather than a
one-time sweep.

The guard walks the same `--src` roots `bootstrap-render.sh` renders —
`hugo-hextra`, `content-type-papers/shared`, `content-type-explainers/shared`,
and the three `features/*` — which is strictly wider than the existing
*class* guard (`test_path_manifest.py` walks `hugo-hextra` only). Note this
surfaces a pre-existing gap that is **not** in scope here: the explainers font
bundle (`fonts/**`) has no *class* row in the manifest, so an explainer blog's
`reproduce.py` reports it as an unclassified materialized path. It is declared
site-rooted below; classifying it is a separate fix.

### B3. Relocation — the migration that self-heals

Adding `.github/**` to the repo root without a migration produces exactly what
#61 warns about: a correct workflow at the root and a stale one under
`<site_dir>/`, with nothing indicating which GitHub honours.

The manifest declares, per path, where earlier releases put it:

```yaml
legacy_dests:
  ".github/workflows/blog-ci.yml":
    - "{site}/.github/workflows/blog-ci.yml"
  ".claude/hookify.warn-hextra-weight-zero.local.md":
    - "{site}/.hookify.warn-hextra-weight-zero.md"
```

`{site}/` expands to `<site_dir>/`, and to the empty string when `site_dir` is
`.` — so a legacy destination that coincides with the current one is simply not
a relocation. One mechanism covers **both** axes (a root change *and* a rename),
which is why it is a table and not a boolean.

`plan_update` gains, per path: if the mapped destination does not exist but a
declared legacy destination does, the operator's file at the legacy destination
becomes the `local` side. The plan entry carries `legacy`, and:

| dest | legacy | action |
|---|---|---|
| absent | present, identical to incoming | `relocate` — pure move |
| absent | present, differs | `replace` (framework) / `merge` / `conflict` (merged), written at `dest`, legacy pruned |
| present | present | dest is authoritative; legacy is a stale duplicate → `prune` (or the normal action, plus the prune) |
| present | absent | today's behaviour, unchanged |
| absent | absent | `add`, unchanged |

`apply_plan` writes the destination first, then removes the legacy file and
prunes directories left empty by the move. **A `conflict` writes nothing and
removes nothing** — both files stay, both are reported, consistent with
`/update`'s never-auto-resolve contract.

`dry_run_diff` names both sides so the dry-run *is* the migration notice:

```
RELOCATE blog/.github/workflows/blog-ci.yml -> .github/workflows/blog-ci.yml [merged]
PRUNE    blog/.hookify.warn-hextra-weight-zero.md [framework]  (stale — now at .claude/hookify.warn-hextra-weight-zero.local.md)
```

### B4. The hookify rule was never loaded — by any blog

#61 flagged `.hookify.warn-hextra-weight-zero.md` as *probably* the same shape
and asked for verification rather than assertion. Verified against hookify's
loader (`plugins/hookify/core/config_loader.py:210`):

```python
pattern = os.path.join('.claude', 'hookify.*.local.md')
files = glob.glob(pattern)
```

Relative to the process CWD — the Claude Code project root. The shipped file
matches **neither the directory nor the filename**. It has never loaded for any
blog, `site_dir` or not: this is worse than #61 suspected, not merely another
`site_dir` casualty. The corroborating evidence is in frank, which carries a
hand-written `.claude/hookify.warn-hextra-weight-zero.local.md` alongside the
inert `blog/.hookify.warn-hextra-weight-zero.md`.

Fix: the template becomes
`templates/hugo-hextra/.claude/hookify.warn-hextra-weight-zero.local.md.tmpl`,
classified `framework`, rooted `repo`.

**And its contents have the same bug.** hookify matches `file_path` against the
path as the tool reports it — from the project root. The shipped rule's
condition is `pattern: content/.*\.md$`; frank's working hand-written copy uses
`pattern: blog/content/.*\.md$`. So the rule's *own* path pattern must carry the
site prefix. That is B1's question one level down, inside the file — which is
why the file becomes a `.tmpl`.

### B5. A repo-rooted workflow must use repo-rooted paths

Moving the CI file to the repository root without fixing its paths leaves it
unable to run — #61's closing point, and independently proven: the current
template invokes `--config .blog-craft.yaml` and `scripts/…` relative to the
site root, while `map_dest`'s own allowlist puts the config at the repo root.
The file could not have passed had GitHub ever run it.

`blog-ci.yml.tmpl` computes a site prefix once and applies it to the paths that
are site-relative — and *only* those:

```
{{- $site := "" }}{{- with .site_dir }}{{- if ne . "." }}{{- $site = printf "%s/" . }}{{- end }}{{- end }}
```

(`text/template`, Go 1.22 — `with` guards the absent key, so no nil comparison.)

| Argument | Prefixed? | Why |
|---|---|---|
| `scripts/validate_*.py` | **yes** → `{{ $site }}scripts/…` | site-rooted per B2 |
| `content/docs/*/*/index.md` | **yes** | Hugo content, site-rooted |
| `--config .blog-craft.yaml` | **no** | repo-rooted; CI's CWD *is* the config root |
| `{{ .dossier_dir }}/*/dossier.md` | **no** | `sync_dossier_to_data.py:61` resolves it against `Path(--config).resolve().parent` — config-root-relative by contract |
| `hugo --minify` | `working-directory: {{ $site }}` | needs the site root (and its `go.mod`) |

Verified: `sync_dossier_to_data.py`, `validate_images.py` and
`glossary_scan.load_registry` all resolve their config-declared paths against
the config file's directory, so they need no prefix and work from the repo root
unchanged. Only the *arguments the workflow passes* need it.

---

## Decisions taken without a Q&A

- **D1 — no interactive channel.** Headless runner; no `AskUserQuestion`. The
  goal text pre-answered the central question ("the more general fix, no
  shortcuts"). Every remaining call is stated here and reversible.
- **D2 — relocate + prune, not report-only.** Report-only preserves exactly the
  two-copies-no-signal state #61 is about.
- **D3 — ship the hookify rule correctly** rather than dropping it. It is a real
  guard, and frank hand-placing a copy is evidence it is wanted.
- **D4 — minor bump (0.13.1 → 0.14.0).** Shipped-surface change; `/update`'s
  destinations and the materialized path set both change observably. Not major:
  no config-schema change.
- **D5 — Test Plan against `derio-net/frank`.** The only known `site_dir` blog,
  and the one the issues were filed from.

## Test Plan

*(post-merge — operator-driven; the relocation can only be proven against a real
`site_dir` blog with a stale copy on disk)*

Against `derio-net/frank` (`site_dir: blog`), which carries
`blog/.github/workflows/blog-ci.yml` (inert, zero runs) and
`blog/.hookify.warn-hextra-weight-zero.md` (inert):

1. **The documented invocation works.** From the frank repo root:
   `python <blog-craft>/tools/update.py --config .blog-craft.yaml --blog .`
   — completes and prints a plan (today: `CalledProcessError` traceback).
2. **The relative-path failure is legible.** Re-run with a config path that does
   not exist; the error names the file and carries the renderer's own stderr
   line, not a stdlib traceback.
3. **The plan relocates, and says so.** The dry-run shows
   `RELOCATE blog/.github/workflows/blog-ci.yml -> .github/workflows/blog-ci.yml`
   and a `PRUNE`/`RELOCATE` line for the hookify rule.
4. **Apply.** `--apply`; confirm `.github/workflows/blog-ci.yml` exists at the
   repo root, `blog/.github/workflows/blog-ci.yml` is gone, and
   `.claude/hookify.warn-hextra-weight-zero.local.md` is present with
   `pattern: blog/content/.*\.md$`.
5. **It re-runs clean.** A second `/update` dry-run plans **no** action on either
   path — the "next `/update` re-adds the dead file" loop is closed.
6. **GitHub actually runs it.** Open a PR on frank; the `blog` workflow appears
   in the Actions tab and its steps resolve (`blog/scripts/…`,
   `blog/content/docs/*/*/index.md`, `--config .blog-craft.yaml`).
7. **The hookify guard fires.** Edit a `blog/content/**/*.md` to `weight: 0` in a
   Claude Code session at the frank root; the warning appears.

## Acceptance rows (matrix backfill — same PR)

- **UPD-R1** — "`/update` accepts the documented relative `--config`/`--blog`
  invocation from a blog root" — `unit=blog-craft:tests/unit/test_update_paths.py`, ci.
- **UPD-R2** — "a renderer failure surfaces the renderer's own stderr, not a bare
  CalledProcessError" — `unit=blog-craft:tests/unit/test_proc.py`, ci.
- **UPD-R3** — "repo-rooted materialized paths (`.github/**`, `.claude/**`) are
  never relocated under `site_dir`" — `unit=blog-craft:tests/unit/test_path_roots.py`, ci.
- **UPD-R4** — "`/update` relocates a stale pre-root-model copy instead of
  leaving two, and re-runs clean" — `unit=blog-craft:tests/unit/test_update_relocation.py`, ci.
- **UPD-R5** — "a `site_dir` blog's CI workflow renders repo-root-relative paths
  that resolve from the repository root" — `unit=blog-craft:tests/unit/test_ci_template.py`, ci.

## Implementation Plans

| Plan | Repo | File | Depends on |
|---|---|---|---|
| 2026-07-27-path-roots-and-subprocess-legibility | `derio-net/blog-craft` | `2026-07-27-path-roots-and-subprocess-legibility` | — |

## Out of scope

- Changing `site_dir`'s meaning, or the config schema version (still v5).
- Auto-detecting a repo root distinct from the config root — `--blog` remains
  "the config root", as documented.
- Retrofitting `on: push: paths:` filters into the shipped workflow for
  `site_dir` blogs (an operator preference, not a correctness bug).
- The 50 pre-existing diagram errors #61 mentions surfacing on frank — those are
  frank's content backlog, not blog-craft's.
