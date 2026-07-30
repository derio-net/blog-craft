# Scaffolder output fidelity + glossary display text — design

**Issue:** [#65](https://github.com/derio-net/blog-craft/issues/65)
**Status:** design
**Date:** 2026-07-27

Four defects reported from one `/blog-post operating 30 silent-failure` run
against `derio-net/frank` (blog-craft 0.16.2, `site_dir: blog`, schema v5).
Three are `tools/blog-post-create.sh` output defects — one data-corrupting, two
silently-wrong. The fourth is a glossary enhancement: let an entry declare the
text it renders as, so two expansions of the same abbreviation can coexist.

## §1 The defects, reproduced

Reproduction against a prompts file whose `images:` sequence sits at column 0
(valid YAML; what `bootstrap` and 88 prior entries in that blog produced):

```yaml
images:
- key: existing-01
  output: static/images/existing.png
```

`bash tools/blog-post-create.sh --no-generate <blog> operating 30 silent-failure
"Operating on Green" scene.txt body.md summary.txt` exits **0** and leaves:

```yaml
images:
- key: existing-01
  output: static/images/existing.png
  composition:
    scene: |
      a scene
  - key: operating-30          # ← indented two spaces
    output: static/images/operating-30-cover.png
```

```
yaml.parser.ParserError: expected <block end>, but found '-'
```

The generated frontmatter:

```yaml
title: "Operating on Green"
date: 2026-07-27
draft: false
tags: []
summary: "s"
weight: 31
```

Three failures in one run:

| # | Defect | Severity | Root cause |
|---|---|---|---|
| 1 | Entry appended at a hard-coded 2-space indent | **high — corrupts the file the whole image pipeline reads** | `blog-post-create.sh:139-160` emits `"  - key: …"` literally; it never reads the file's own sequence indentation |
| 2 | Frontmatter omits `series`, `layer`; `tags: []` bare | silent wrong output | `:109-128` emits a fixed field list that predates both conventions |
| 3 | `key` and `output:` defaults ignore the blog's convention | silent wrong output | `:99-100` hard-codes `<series>-<number>` and `<output_dir>/<key>-cover.png`; `key` has no override at all |

Item 1 is silent because the helper never re-reads what it appended. Item 2 is
silent because `{{< series-index >}}` is page-derived from `series` — a post
without it simply never appears, and Step 8 of the skill promises the opposite.

Why the existing tests miss all three: `tests/unit/test_blog_post_create.py:37`
seeds the prompts file as `"images:\n"` — an **empty** sequence, where both
indentations parse identically, and where no existing entry establishes a
convention to detect.

## §2 Decisions

No interactive channel was available in the session that produced this spec
(no `AskUserQuestion` tool), and the operator's instruction was "use fr-goal and
your best judgement … open a PR when the work is complete". These are therefore
**agent-made calls, flagged for review**, not operator answers.

- **D1 — item 1 is fixed by detecting the file's indentation, not by
  round-tripping the YAML.** The issue offers "load, append, dump" as the safest
  fix. Rejected: `dump` rewrites all ~1900 lines of a real prompts file,
  reflowing every block scalar, re-quoting every string and reordering keys. The
  scaffolder would stop corrupting the file and start rewriting it. Detection
  keeps the rest of the file byte-identical.
- **D2 — the append is verified, not trusted.** After writing, re-parse the
  file: it must load, `images` must still be a list, and it must have grown by
  exactly one entry whose `key` is the new key. Failure restores the pre-append
  bytes and exits non-zero. This is what turns item 1's class of bug from silent
  into loud, independently of the indentation fix.
- **D3 — `series` is always emitted**, as a single-element list
  (`series: ["operating"]`), matching every post in the reporting blog and Hugo
  taxonomy shape. It is the skill's first positional argument; nothing to ask.
  (The sibling scaffolders already emit it — `scaffold-explainer.sh:214,239`,
  `scaffold-paper.sh:58` — unquoted; quoted here, equivalent after parsing and
  safe for any key.)
- **D4 — `layer` gets a `--layer <code>` flag, validated against the blog's own
  registry** (`series_index.layers[].code`); an unknown code is an error that
  lists the valid ones. Omitted **and** the blog declares layers → emit
  `layer: TODO` plus a stderr warning. That is `scaffold-paper.sh:59`'s existing
  convention, it is greppable, and it is inert: `series-index.html:79-80` looks
  the code up in `data/layer_palette.yaml` behind a `with` guard, so an unmatched
  code renders exactly like no layer — a neutral card, no badge. Omitted and the
  blog declares no layers → emit nothing (that blog does not use layers). Not a
  hard failure: the helper must stay usable on a blog mid-setup.
- **D5 — `tags` gets a repeatable `--tag <t>` flag**; with none supplied the
  emitted `tags: []` carries a `# TODO` comment. Here the spec deliberately
  *departs* from the sibling scaffolders' `tags: ["TODO"]`: they also emit
  `draft: true`, whereas `blog-post-create.sh` emits `draft: false`, so a literal
  `TODO` tag would publish a bogus taxonomy term on the next build. A comment
  cannot.
- **D6 — `key` gets a `--key <key>` override; the default is unchanged.**
  Convention *detection* for keys is rejected: the reporting blog's
  `ops-30-silent-failure` needs an abbreviation map (`operating` → `ops`) that
  exists nowhere in the config, so any detection would be guesswork applied to
  the one field that names the entry. An explicit override plus a skill step that
  tells the agent to read existing entries is honest.
- **D7 — `output:` default is detected from existing entries.** Covers inside the
  page bundle and covers in `image.output_dir` are both legitimate; the file says
  which this blog uses. Rule: among existing entries carrying `output`, count
  those under `<site_dir>/content/`; if they outnumber the rest, default to
  `<site_dir>/content/docs/<series>/<NN>-<slug>/cover.png` (the bundle this run
  just created), else keep `<output_dir>/<key>-cover.png`. No existing entries →
  `output_dir`. Every blog in the field keeps its current default;
  `--output` still wins.
- **D8 — glossary `rendered_text` follows the issue's proposal exactly**, with
  two additions: `abbr.html`'s `aria-label` uses the resolved display text too
  (it leaks the raw key today), and `glossary-index.html` sorts by resolved
  display text with the key as tiebreaker — a no-op for every entry without
  `rendered_text`, and it keeps two senses of `GC` adjacent instead of ordered by
  an identifier the reader cannot see.
- **D9 — minor version bump** (0.16.2 → 0.17.0): four new flags and a new
  optional data field are added capability, not just fixes.
- **D10 — scope is blog-craft only.** The already-corrupted
  `blog/prompt_for_images.yaml` in `derio-net/frank` is that repo's to repair
  (the issue records the one-line manual workaround).

## §3 Item 1 + 2 — the append path

New helper `tools/prompts_append.py` (PyYAML is already a hard dependency —
`pyproject.toml:5`, and the shell path already invokes Python for
`tools/blog_config.py`). Shell composes the entry body; the helper places it and
answers the one question the file can answer about itself.

```
prompts_append.py append       --file <prompts.yaml> --key <key> --entry-file <block>
prompts_append.py output-style --file <prompts.yaml> --site-prefix <site_dir>
```

`output-style` prints `bundle` or `output_dir` (D7). Two subcommands, one module,
because both need the same "where is the `images:` sequence and what is in it"
knowledge — splitting them would duplicate the parse.

`series_index.layers[].code` is read with an inline PyYAML heredoc in the shell,
matching `scaffold-explainer.sh:220-227` and `scaffold-paper.sh:26-34`;
`blog_config.py get` cannot serve it (it flow-dumps non-scalars —
`blog_config.py:52` — which is not shell-parseable).

- **Detect indentation.** Find the `images:` mapping key at column 0, then the
  first `- ` sequence item belonging to it; its column is the sequence indent.
  Empty sequence → 2 (the `templates/hugo-hextra` bootstrap default, so a fresh
  blog is unchanged).
- **Re-indent** the entry block from its authored 2-space form to the detected
  indent, shifting continuation lines by the same delta so block scalars survive.
- **Normalise the seam.** Ensure exactly one trailing newline before appending;
  today a prompts file without a final newline is silently merged into.
- **Verify (D2).** Re-parse; require `len(images) == before + 1` and
  `images[-1]["key"] == key`. On any failure restore the original bytes and exit
  2 with the parser error.

Frontmatter (`blog-post-create.sh` step 1) gains, in convention order:

```yaml
title: "…"
series: ["operating"]
layer: obs                 #   or `layer: TODO`, or omitted entirely (D4)
date: 2026-07-27
draft: false
tags: ["operations"]       #   or: `tags: []  # TODO: add tags` (D5)
summary: "…"
weight: 31
reader_goal: "…"
diataxis: [how-to, reference]
```

## §4 Item 4 — glossary `rendered_text`

Optional per-entry field, defaulting to the key:

```yaml
GC:
  name: Garbage Collection
  description: >- …
GC_GOATCOUNTER:
  rendered_text: GC
  name: GoatCounter
  description: >- …
```

Resolution, one precedence chain in both surfaces —
**call-site arg 1 › `entry.rendered_text` › key**:

```go-html-template
{{- $display := or (.Get 1) $entry.rendered_text $key -}}
```

- `abbr.html` — `$display` in the `<abbr>` body **and** the `aria-label`.
- `glossary-index.html` — renders the resolved display text instead of `{{ $k }}`,
  and sorts on it.
- `tools/validate_glossary.py` — accepts optional `rendered_text` (non-empty
  string; wrong type is an error), keeps rejecting keys that differ only in case,
  and **does not** reject two entries sharing a `rendered_text` — that is the
  feature.
- `skills/glossary/SKILL.md` — documents the field, and states plainly that
  `glossary_apply.py` matches literal tokens and can therefore only auto-mark the
  **default** sense; the second sense is marked by hand.

`validate_glossary.py` has no unknown-key rejection today (`_REQUIRED` at
`validate_glossary.py:34` is a whitelist of *required* fields, not an allowlist),
so `rendered_text` would already pass silently — the point of touching it is the
type check and the sorted-registry warning, not permission.

## §4a What else moves with those files

- **Mirror.** `tools/validate_glossary.py` ships into a blog as
  `templates/hugo-hextra/scripts/validate_glossary.py`, byte-identical, guarded by
  `tests/unit/test_mirrors.py:34`. Both copies change together.
- **Ownership classes** (`templates/manifest.yaml`): `layouts/**` and `scripts/**`
  are `framework` (overwritten on `/update` — the new templates arrive
  automatically), `data/**` is `content` (the operator's registry is never
  touched). So no migration is needed: `rendered_text` is purely additive to a
  file blog-craft does not own.
- **OpenCode mirror.** `skills/glossary/SKILL.md` and `skills/blog-post/SKILL.md`
  have byte-identical copies under `.opencode/skills/blog-craft-<name>/`,
  regenerated by `scripts/sync-opencode.py` and guarded by
  `tests/unit/test_opencode_sync.py`. Re-sync after editing either skill.
- **Version + changelog.** The diff touches `tools/`, `templates/` and `skills/`,
  all under `check_version_bump_needed.py:22`'s required prefixes, so
  `tools/bump_version.py minor` (D9) plus a `## [0.17.0]` CHANGELOG section are
  mandatory — `tests/unit/test_changelog.py` fails without the section.
- **Acceptance matrix.** This spec carries a Test Plan, so
  `.claude/rules/acceptance-matrix.md` requires new rows citing it in the same PR.

## Implementation Plans

| Plan | Repo | File | Depends on |
|---|---|---|---|
| 2026-07-27-scaffolder-output-fidelity | `derio-net/blog-craft` | `2026-07-27-scaffolder-output-fidelity` | — |

## §5 Test Plan

Automated (CI, `tests/run-unit.sh`):

1. A prompts file with its sequence at **column 0** plus an existing entry →
   scaffold → the file still parses and holds exactly 2 entries. *(the reported
   corruption)*
2. Same at **2-space** indent → still parses, 2 entries. *(no regression for a
   bootstrap-shaped blog)*
3. A prompts file with **no trailing newline** → parses, 2 entries.
4. A prompts file that is **already broken** → helper exits non-zero and leaves
   the bytes untouched. *(D2)*
5. Frontmatter carries `series: ["<series>"]` always.
6. `--layer obs` emits `layer: obs`; an unknown code errors and names the valid
   codes; omitted-with-registry emits `layer: TODO` and warns; omitted-without-
   registry emits no `layer` key at all.
7. `--tag a --tag b` emits `tags: ["a", "b"]`; omitted emits `tags: []` with the
   TODO comment (never a literal `TODO` tag — the post is `draft: false`).
8. `--key ops-30-silent-failure` overrides the entry key; default unchanged.
9. `output:` defaults to the page bundle when existing entries are bundle-shaped,
   to `output_dir` when they are not, and to `output_dir` when there are none;
   `--output` beats detection.
10. Glossary: `rendered_text` renders in `abbr.html` (body + aria-label) and
    `glossary-index.html`; the call-site arg still wins; two entries sharing a
    `rendered_text` validate; a case-colliding key still fails; a non-string
    `rendered_text` fails.

Post-merge, operator-driven (not automatable here — needs the real blog):

11. In `derio-net/frank`, repair the corrupted `blog/prompt_for_images.yaml` by
    hand (rewrite the appended block at column 0), then `/update` to the new
    blog-craft and re-run `/blog-post operating 30 silent-failure` on a scratch
    branch: the file still parses, the entry key/output match the blog's 88
    existing entries, and the post appears in the `operating` series overview.
12. Add the `GC` / `GC_GOATCOUNTER` pair to that blog's `data/glossary.yaml`,
    render a page carrying `{{< glossary-index >}}`, and confirm both read `GC`.

## §6 Post-merge evidence (2026-07-30)

Merged as `1665bfc` (#66, blog-craft 0.20.0); issue #65 closed.

**Step 11 — verified against the real artifact, not a fixture.** The reporting
blog's own `blog/prompt_for_images.yaml` was copied byte-identically
(md5 `d140bbcf42f8674c6fc2f3b4b79263ec`, 1751 lines, 87 entries) into a scratch
tree with that blog's real `.blog-craft.yaml` (`site_dir: blog`), and the
scaffolder **as it exists on `main`** was run against it:

- `sequence_indent` reads the file's own indentation as **0** — the exact shape
  that corrupted it (§1). The entry lands at column 0.
- The result **parses**: 88 entries, the last one the appended key.
- The original 1751 lines are a **byte-identical prefix** of the result; nothing
  above the insertion point was rewritten (D1).
- `output:` detection (D7) resolved to
  `blog/content/docs/operating/30-silent-failure/cover.png` — the page-bundle
  convention **83 of that blog's 87 entries** already use, which the old
  hard-coded default got wrong every time.
- `generate-images.py --print-prompt <key>` runs and prints the composed prompt,
  exit 0 — the Step 6 preview the issue reports as impossible.
- Frontmatter carries `series: ["operating"]`, `layer: obs`, and
  `tags: ["operations", "slo"]`.

`--key ops-30-silent-failure` was passed, matching that blog's
`<series>-<NN>-<slug>` keys. This is D6 working as designed and as documented:
nothing in the config could have derived `ops` from `operating`, so the skill
step that tells the agent to read an existing entry is what makes the flag get
used.

**What step 11 did NOT cover.** The blog itself was never modified — per D10
that repo owns its own repair, and it has already applied the manual workaround
(its file parses today). So `/update`-ing that blog to 0.20.0 and rendering the
`operating` overview to see the new post listed remain genuinely unexercised;
`series` reaching the frontmatter is verified, the Hugo render of it is not.

**Step 12 is not drivable and its premise no longer holds.** That blog has
`features.glossary` **absent** — the feature is off and there is no
`data/glossary.yaml` at all — and its checkout is pinned at
`blog_craft_version: v0.10.0`. The collision the issue predicts is nonetheless
real and confirmed: its config sets `analytics.provider: goatcounter`, and
GoatCounter is named in 6 posts, so the day that blog enables the glossary and
adds `GC` for Garbage Collection, `rendered_text` is what keeps both senses
definable. The CI evidence (GL-11, GL-12) is a real Hugo build, so the behaviour
is pinned regardless; what is missing is only the confirmation on this
particular blog.
