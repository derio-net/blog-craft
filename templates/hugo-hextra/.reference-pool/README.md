# Reference-pool — character anchors for image generation

Reference images are attached to every Gemini call to keep the blog's persona
consistent across covers, tiles, and banners. They stack — compose, don't replace.

1. **Master reference** — `image.reference_image` in `.blog-craft.yaml`
   (default `static/images/reference.png`). The canonical character design sheet.
   Overrides everything for a whole run via
   `scripts/generate-images.py --reference path/to.png`.
2. **Master per-series reference** — auto-picked from
   `<series>/reference-<series>.png` when a prompt entry has `series: <series>`.
   Gives a series its own flavour of the character while staying on-model.
3. **Explicit `references:` on a prompt entry** — hand-picked anchors, usually
   from `<series>/subjects/`.

## Layout

```
.reference-pool/
  README.md
  generic/
    reference-generic.png      # fallback master ref (entries with no series)
    subjects/                  # hand-curated single-character renders
  <series>/                    # one per series in .blog-craft.yaml (create as needed)
    reference-<series>.png     # master ref for that series
    subjects/                  # series-flavoured character renders
```

## Choosing the master reference (the character design sheet)

The persona + `image.layers.visual_constants` in `.blog-craft.yaml` are enough to
*generate* candidate design sheets — no hand-drawn art required:

1. Generate candidates (source your `.env` for the API key first):
   `python scripts/gen-character-sheet.py 12`
   → writes 12 model sheets + `contact-sheet.png` to `.regen-archive/reference/`
   (the `.regen-archive/` dir is **gitignored**; only keepers are tracked).
2. Browse them full-screen and compare:
   `python scripts/build-gallery.py` → open `.regen-archive/reference/gallery.html`.
3. Promote the best one:
   `cp .regen-archive/reference/reference-<sha>.png static/images/reference.png`
   (optionally also into `generic/reference-generic.png`).
4. Regenerate covers/tiles with the reference in place:
   `python scripts/generate-images.py`

The chosen sheet is what `image.layers.reference_guidance` calls "the canonical
character-design sheet" — every cover's character is drawn to match it.
