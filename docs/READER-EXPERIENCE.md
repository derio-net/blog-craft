# Reader and agent publishing

The optional reader experience keeps Hugo and Hextra. It adds compact article
headers, reading metadata, responsive covers, a configurable home page, problem
based topic guides, canonical share images, and published-content exports.
It does not generate social posts or add a client-side application runtime.

## Enable

Add this to the consuming repository's `.blog-craft.yaml`:

```yaml
features:
  reader_experience:
    enabled: true
    agent_exports: true
    author:
      name: Example author
      url: https://example.org/about/
```

Both switches default to false. `agent_exports` requires `enabled`. Set
`project.base_url` to the canonical production URL, including its trailing slash.
The updater merges that setting into Hugo; preview builds may override the origin.
Existing Hextra version pins are preserved by the three-way updater.

Run the normal updater dry run and apply. Everything reader-specific — the
`reader-home` layout and shortcodes, the `reader/*` partials, a reader-aware
`docs/single.html`, the catalog and `llms.txt` output templates, `reader.css`,
`reader.js`, `scripts/build-site.py` and `scripts/export-content.py` — ships as
one feature bundle (`templates/features/reader-experience/`) that materializes
only when `enabled` is true; a blog without the feature gets none of it, and the
shared templates include the reader partials only when they exist. Do not patch
generated layouts: layouts, JavaScript and scripts are framework-owned and
replaced on update. CSS and `hugo.toml` are merged. Content, `data/`, and the configuration are operator-owned.
Commit the generated `.blog-craft.sync.yaml` together with the update. Follow the
update skill's version-pin instructions so the next three-way merge has its base.

## Curate the home page and topics

Use `layout: reader-home` and `{{< reader-home >}}` in `content/_index.md`, with a
short explicit `description`. Create `data/reader.yaml`, for example:

```yaml
home:
  eyebrow: Field notes
  title: Build and understand
  description: Practical guides and the evidence behind them.
  featured: [/docs/building/02-foundation]
series:
  - key: building
    title: Building
    path: /docs/building/
    description: Decisions and implementation.
topics:
  - slug: troubleshooting
    title: Troubleshooting
    description: Find a useful starting point.
    layers: [obs, gitops]
```

Share images: the reader emits an `og:image` from the page cover (or the
landing banner) only when neither the page's `images` frontmatter nor
`params.images` is set — those go through Hextra's own opengraph partial and
take precedence, so a page never carries two tags.

Create `content/topics/troubleshooting/index.md` with a title, description and
`{{< reader-topic "troubleshooting" >}}`. Topic lists use the article's existing
`series` and `layer` metadata. Add About and Topics section pages and navigation
items to suit the blog. The footer shows these links only when the pages exist.
A missing curated featured page fails the build instead of silently dropping it.

Article headings precede imagery. Operating posts omit decorative covers; Papers
use larger reading type. Site and track banners render on section and home
pages only — article pages open with the title, meta and cover instead. The
theme's `custom/footer.html` hook becomes framework-owned when the feature is
on (as it already is with `read_tracker`): an operator's own copy of that
partial is replaced on update, so put footer additions in `custom.css`-style
merged paths or ask for a hook. Existing content, glossary, diagrams, references and
cross-links remain in place. Readers can use the existing search, theme switch,
series navigation and table of contents.

## Dates and evidence

Write a short `description` for search previews, cards and the catalog. Optional
article frontmatter includes `reader_goal`, `prerequisites` (list),
`tested_versions` (list), `last_verified` (date), and `commands_change_state` (bool).
Only populate verification fields from actual checks; never infer them from a
publication or edit date. Hugo resolves the editorial update date from
`last_updated`, `lastmod`, then `date` — on a reader blog `last_updated` must
therefore be a date (the `{{</* last-updated */>}}` shortcode still prints it);
blogs without the feature keep Hugo's default chain and may use the key as free
text. A page with no date (About, Topics) gets empty `published` / `updated`
fields and no date lines in its export rather than a fake `0001-01-01`. The
catalog emits `false` for an unknown verification date and `"unknown"` for
missing command-state metadata; explicit `commands_change_state: false` stays
false.

## Production build

Use Python 3.9+ (both scripts are stdlib-only and avoid newer syntax) and the
blog's pinned Hugo version:

```sh
cd path/to/hugo-site
python3 scripts/build-site.py
```

The helper builds clean production output in `public/`, then runs the stdlib
exporter when the catalog exists. It takes no arguments at all (a flag
allowlist cannot be made safe against hugo's combined shorthands such as
`-DF`). Use `hugo server` for editorial previews; Markdown endpoints require a
completed production build. Wire this helper into the consuming repository's
CI/deployment. A container without Python in its Hugo stage can run
`python3 scripts/export-content.py public` in a separate build stage after Hugo.
Deploy the resulting `public/` directory as a unit.

The endpoints are `llms.txt`, `content-index.json`, `index.xml` (RSS), and each
published regular page's `index.md`. The catalog is generated by Hugo, so drafts,
future/expired posts and private source directories are outside the publication
boundary. It includes canonical HTML and Markdown URLs, summaries, series, layers,
tags, dates, prerequisites, evidence metadata and the source-relative file path.
The exporter adds a SHA-256 digest of each complete Markdown response, useful for
change detection. It exports rendered article bodies, expanding shortcodes while
preserving code whitespace, Mermaid source, tables, glossary definitions and
references. Heading links point back to their canonical HTML anchors. This is a
reading representation, not a round-trip copy of the original authoring source.

`llms.txt` uses Hextra's own `llms` output format; the feature overrides the
theme's generic page listing with a catalog-first entry point. Do not add
Hextra's `markdown` output format to `outputs.page`: it also writes `index.md`
(the raw source, shortcodes unexpanded) and would race the exporter for the same
file. `llms.txt` is a discovery convenience, not an access policy or a guarantee
of agent adoption. Robots and sitemap behavior remain Hugo's. No new analytics,
third-party scripts or inline JSON-LD are required. The copy action fetches the
Markdown only when clicked and offers a readable link if clipboard access fails.

Compression and cache headers belong to the consuming host: compress text, cache
content briefly, and use long immutable caching only for fingerprinted assets.
Measure deployed performance separately; build success is not a Lighthouse score.
