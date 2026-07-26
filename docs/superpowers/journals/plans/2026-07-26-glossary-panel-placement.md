# Journal: 2026-07-26-glossary-panel-placement

<!-- fr:journal kind=discovery scope=plan id=p1-zgotmplz created=2026-07-26T14:55:13 phase=1 -->
### p1-zgotmplz · discovery · Go's escaper turns an interpolated style attribute into ZgotmplZ — safeCSS is mandatory (phase 1)

First GREEN attempt emitted style="anchor-name: {{ $anchor }}" straight from the template. The shortcode file materialized correctly and the unit tests still failed; the built HTML contained style="anchor-name: ZgotmplZ".

html/template treats a style attribute as a CSS context and substitutes the literal ZgotmplZ for any interpolated value it cannot prove safe — silently, with a zero exit code from hugo. Nothing in the build output says so.

Fix: build each declaration with printf and pipe it through safeCSS. Safe here by construction — both values derive from $id, which is anchorize(key) plus an integer .Ordinal, so no author input reaches the CSS context.

Worth knowing for any future shortcode that computes an inline style: the failure is invisible unless a test asserts on the built HTML rather than on the template file.

<!-- fr:journal kind=discovery scope=plan id=p1-browser-walk created=2026-07-26T15:04:52 phase=1 -->
### p1-browser-walk · discovery · Browser walk: panel measured adjacent to its term in all four cases (phase 1)

Chrome 147 (Playwright chromium-1217), real layout, against a bootstrapped blog served under its /gt/ baseURL. #49's evidence was trigger=(375,299) panel=(0,0).

ANCHORED — 1280x850:
  NUT trigger=(375,178) panel=(375,213) 352x139  6px below, dx=0
  SLO trigger=(560,178) panel=(560,213) 349x73   6px below, dx=0
  CDP trigger=(590,600) panel=(590,635) 352x93   6px below, dx=0
Each panel under its OWN trigger — the shared-anchor-name failure mode is absent.

ANCHORED — 500x850 (inline flip):
  NUT panel=(95,213)  dx=0     — room to the inline end, no flip
  SLO panel=(151,213) dx=-129  — flipped to span-inline-start
  CDP panel=(148,639) dx=-162  — flipped
All fully on-screen, none overlapping the h1.

ANCHORED — block-start flip, 1280x760, term parked 30px from the viewport foot:
  CDP trigger y=701..730, panel y=602..695 — 6px ABOVE the term, fully on-screen.
  position-try-fallbacks: block-start span-inline-end confirmed live.

FALLBACK (same build with the @supports block stripped from the served CSS, standing in for a browser without anchor positioning):
  1280x850 panels x=464..466, w=352 -> centred on 640; bottoms all 834 (1rem above the foot)
   500x850 panels x=74..76,  w=352 -> centred on 250; bottoms all 834
All fully on-screen, none overlapping the h1. The corner placement does not occur on either path.

Harness notes for anyone repeating this: the site's baseURL is /gt/, so a flat static server 404s every asset and the panel silently falls back to UA geometry (352->1044 wide, inset:0) — serve under the prefix or the walk measures nothing. --disable-blink-features=CSSAnchorPositioning does NOT disable it in 147 (stable feature); stripping the @supports block from the built CSS is the way to exercise the fallback.
