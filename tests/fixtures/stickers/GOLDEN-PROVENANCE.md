# Sticker goldens — where they came from

`golden/<key>.txt` (18 files) and `golden/<key>.refs.txt` (18 files) are the
output of **frank's own private sticker generator**, not of blog-craft. That is
the whole point: `tests/unit/test_stickers_golden.py` compares blog-craft's
composed prompt against frank's, so it is an **equality proof** that the port
changed nothing — not a transcription of what blog-craft happens to produce.

If a golden and the engine disagree, **the fixture is wrong, not the golden.**
Never regenerate a golden to make a test pass.

## Provenance

| | |
|---|---|
| frank repo | `derio-net/frank` |
| frank checkout HEAD at derivation | `0aa4095c7b540d19133080346437025ce9e77f28` |
| last commit touching `stickers.yaml` | `1373d06e87127515960ec2b7b081a689577880c7` ("Update image generation script and replace favicon assets", 2026-07-21) |
| source function | `blog/_private/frank-stickers/generate-stickers.py` → `compose_prompt(cfg, s)` and `scene_refs(cfg, s)` |
| config passed to it | the **vendored** `frank-stickers.yaml` in this directory, byte-identical to `frank/blog/_private/frank-stickers/stickers.yaml` (sha256 `723c2b5b5b1cbf686f35c27eacec07b281c8feb23c08519ed6d22bb4b12f4ab5`) |
| derived | 2026-08-03, by `derive-goldens.py` (committed next to this file) |

`derive-goldens.py --check` re-derives and diffs against the committed set; it
needs a frank checkout and therefore never runs in CI (frank is not mounted in
blog-craft's isolation container — journal `orch-frank-not-mounted-in-container`).

## Why `--dry-run` could NOT be used

frank's CLI truncates: `print(compose_prompt(cfg, s)[:300] + " ...")`
(`generate-stickers.py:101`). The real prompts are ~4.6k characters, so the CLI
discards ~93% of every prompt — including the mood frame (section 6), the scene
and the border spec. A golden derived from `--dry-run` would "pass" while
proving nothing about the five sections that follow char 300.

## Why the script has to be stubbed, and why that is safe

`generate-stickers.py` **cannot be imported or run as-is**. Its module level does

```python
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from lib.contact_sheet import compose_contact_sheet
```

and that module no longer exists: frank's own blog-craft cutover (`bd0415e6`)
deleted both `scripts/lib/contact_sheet.py` and `lib/__init__.py`. So frank's
sticker generator has raised `ModuleNotFoundError` on *every* invocation since
that cutover — not even `--list` works. (`build-sheets.py` does not import it,
which is why the breakage went unnoticed: the visible artifact still rebuilds.)

The derivation therefore stubs five module names before loading the file:

| stub | used by frank for | why stubbing is safe |
|---|---|---|
| `google` | package parent of `google.genai` | namespace only; nothing is called |
| `google.genai` | `genai.Client(...)`, `genai.types.GenerateContentConfig/HttpOptions/ImageConfig` | referenced only inside `main()` on the generation path |
| `PIL` | `Image.open(p)` to build the reference payload | referenced only inside `main()`; `scene_refs` returns `Path`s and never opens them |
| `lib` | package parent of the deleted helper | namespace only |
| `lib.contact_sheet` | `compose_contact_sheet(...)` for the run-level regen sheet | called only inside `main()`, after generation |

**The two functions the goldens come from touch none of them.**
`compose_prompt` is a `"\n\n".join` over dict lookups plus one f-string;
`scene_refs` is `pathlib` joins plus `.exists()`. Both are pure over
`(cfg, sticker)` — so the stubs remove an import-time crash without standing in
for any behaviour the goldens depend on.

## What was verified before committing (measured 2026-08-03)

- 18 `.txt` + 18 `.refs.txt`, keys exactly the 18 in the vendored yaml;
- every prompt splits into **exactly 8** blank-line-separated sections, and each
  of the 8 is non-empty — which is what makes frank's unfiltered
  `"\n\n".join([...])` and blog-craft's `compose()` (which *drops* empty
  sections) agree;
- each golden equals `"\n\n".join` of the 8 pieces read straight out of the
  vendored yaml, in frank's order — including `border_spec` **after** `scene`;
- reference payloads are **4** images when the sticker has a `clothing_anchor`
  and **3** when it is `null` (both cases occur: 12 and 6), always in the order
  `reference-building.png`, `sticker-09-server-blade.png`,
  `sticker-20-tinkering.png`, then the clothing subject;
- prompt lengths 4628–4697 characters;
- spot check: `22-coffee-b.txt` contains
  `Frank's expression: satisfied — sleepy half-smile, eyes half closed.`
  as section 6 of 8.

## File format

`<key>.txt` is the prompt **plus one trailing newline** — i.e. exactly what
`generate-images.py --print-prompt <key>` writes to stdout, because `print()`
adds that newline. The test compares raw bytes with no normalisation step, so
there is nothing in the middle to get wrong.

`<key>.refs.txt` is one reference **basename** per line, in payload order,
primary first. Basenames rather than paths because the directories move in the
port (frank resolved against his repo root; blog-craft resolves against the blog
root) while the payload *order* is the thing under test.
