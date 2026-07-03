# Page-derived series overviews — blog-craft mechanism

Implements the mechanism half of
`docs/superpowers/specs/2026-07-03--series-index--page-derived-series-overviews-design.md`:
a generic `{{< series-index >}}` shortcode that renders a series' index from its
actual pages at Hugo build time, replacing the marker-append push model.

**Phase 1 — the shortcode (TDD).** A failing Hugo-build test over fixture pages
drives out `layouts/shortcodes/series-index.html`: infer the series from the host
overview page (positional-arg override), range that series' pages sorted by
weight, exclude the host page, and render a `# | Post | Takeaway` table — `#` from
the `NN-` slug prefix, title linked, takeaway from `.Params.summary`. Edge cases:
blank takeaway/number, empty series (muted line).

**Phase 2 — retire the push machinery.** The `per-series-overview` template drops
its two markers for `{{< series-index >}}`, and `blog-post-create.sh` drops its
overview-append step entirely (the index is now page-derived; nothing to append).
`insert-before-marker.py` is retired if unused. Full unit + reproduction + smoke
suite stays green.

Papers is untouched (its roster+status model is correct for planned/deferred
entries). frank's adoption — splitting its combined overview so building and
operating each get an auto-updating landing page — is a **separate plan in the
frank repo, sequenced after this merges** (frank consumes the shipped shortcode).
