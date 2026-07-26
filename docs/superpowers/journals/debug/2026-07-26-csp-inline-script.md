# Journal: 2026-07-26-csp-inline-script

<!-- fr:journal kind=root-cause scope=debug id=rc-1 created=2026-07-26T20:30:00 -->
### rc-1 · root-cause · Two templates shipped behaviour in an inline `<script>`, which a CSP drops silently

Found running `/update` on the frank blog (blog-craft#56), the second such round
after #53. `templates/features/read-tracker/layouts/partials/custom/footer.html.tmpl`
and `templates/hugo-hextra/layouts/shortcodes/asciinema.html` each carried an
inline `<script>`.

`script-src 'self'` without `'unsafe-inline'` is the ordinary hardening posture
for a public blog. It drops inline blocks **silently** — the document still
parses, the build still succeeds, no console message an author would go looking
for. So the "Clear read history" link rendered and cleared nothing, and
`{{< asciinema >}}` emitted its container and never started a player. Both look
like content bugs, not policy failures, which is why they survived.

The read-tracker feature **already** shipped its main logic as an external asset
(`assets/js/read-tracker.js.tmpl`, loaded by `head-end.html`). So the pattern was
established and these were the two call sites that missed it — structurally the
same as `resize` vs `crop_resize`/`ico` in #53: a shipped convention with a
straggler, invisible until a downstream blog forked the file to compensate.

<!-- fr:journal kind=decision scope=debug id=d-1 created=2026-07-26T20:35:00 -->
### d-1 · decision · Guard at BOTH the source and the output level, and pin the detector

A source-level grep ("no inline `<script>` in any template") is the obvious
guard, and it is not sufficient on its own: it says nothing about whether the
replacement wiring actually works. The failure being prevented is *behaviour
silently absent from the built page*, so the built page is where it has to be
checked. `tests/unit/test_templates_csp_safe.py` therefore does three things:

1. **Source** — no inline `<script>` in any HTML-emitting template. Comments are
   stripped first (a note explaining why a handler moved *out of* a `<script>`
   must not trip it — this fired on the first draft, on its own prose), and
   `.js.tmpl` / `.css.tmpl` are skipped: they are not markup, and their source
   legitimately discusses `<script>`.
2. **Detector self-test** — synthetic markup pinning both directions. Without it,
   a later tweak to the regex or the comment-stripping would leave the guard
   passing vacuously, which is the classic way a tripwire rots.
3. **Output** — a Hugo build asserting the external scripts load, the `data-*`
   attributes are present, and the page carries zero inline blocks.

Inline `style=` is deliberately out of scope. `abbr.html` needs a unique
`anchor-name` per trigger (#49/#51) and `screenshot.html` a per-invocation
`max-width`; neither can live in a stylesheet, and `style-src` is commonly left
permissive where `script-src` is not. Widening the guard to `style=` would force
those two into a suppression list and teach readers the guard is negotiable.

<!-- fr:journal kind=note scope=debug id=n-1 created=2026-07-26T20:40:00 -->
### n-1 · note · The player library is still off-origin and unpinned

`head-end.html` loads asciinema-player from `unpkg.com`. The same
`script-src 'self'` CSP blocks it, and it carries no Subresource Integrity, so a
CDN compromise is unmitigated. Vendoring the library into `assets/` resolves the
CSP, the SRI gap and the supply-chain exposure together. Pinning a hash to a URL
the CSP rejects anyway would be motion without progress, so this is left as
follow-up and recorded in the changelog under Known.
