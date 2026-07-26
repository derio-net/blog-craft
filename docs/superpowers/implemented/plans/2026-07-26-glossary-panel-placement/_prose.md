# Glossary panel placement (#49)

The abbreviation glossary shipped in #48 works — the panel opens, carries the
right definition, closes on `Esc` and on click-away, and is keyboard-reachable.
It just opens in the **top-left corner of the viewport**, 375px left and 299px
above the term it defines, on top of the page `<h1>`.

Every unit test passes, because every unit test asserts *structure*: that a
button/popover pair exists, that ids are unique, that the panel holds the name
and description. None asserts *position*, so a purely geometric bug was
invisible to CI and only surfaced in the post-merge browser walk.

## Root cause

The top layer decides **stacking**, not **coordinates**. `{{< abbr >}}` emits
`<button popovertarget>` + `<span popover>` and `glossary.css` styles the panel
but never places it, so the UA default (`inset: 0` plus `margin: auto`
semantics) takes over and Chromium lands it in the block-start / inline-start
corner. The design spec called top-layer positioning a *benefit* of the Popover
API and never specified where the panel should appear — the code does exactly
what was designed. That spec gap is fixed first, as §5a, and the plan implements
it.

## Shape of the fix

Two pieces, and the second is the one that is easy to get wrong.

**Anchor names must be per-pair.** CSS anchor positioning needs a name on the
trigger and a matching `position-anchor` on the panel. A single `--abbr` shared
by every trigger on the page anchors them all to whichever one the browser
resolves first — the panel for the fifth term opens under the first. The
shortcode already computes a unique id (`abbr-<key>-<ordinal>`); the anchor name
is derived from that same value in the same expression, so the two cannot drift.
Both go in inline `style` attributes, because no stylesheet can address a single
shortcode instance, and both are dropped harmlessly where unsupported.

**The fallback must not be the bug.** Anchor positioning support is still
uneven, so the unanchored path is a real path. Left alone it produces exactly
the corner placement being fixed. The base rules therefore dock the panel
bottom-centred and viewport-clamped, and the anchored rules layer on top inside
`@supports (anchor-name: --x)`. Not adjacent to the term is an acceptable
compromise; covering the heading is not.

Two properties fight back and are called out in the steps: `.abbr-trigger` sets
`all: unset`, so the inline `anchor-name` is what survives; and the UA
`[popover]` sheet's `inset: 0` / `margin: auto` will stretch the panel to fill
its whole position area unless the anchored rule resets them.

## Verification

Phase 1 task 3 drives a real browser and measures the two bounding boxes,
because that is the only check that would have caught this. The unit tests pin
what CI *can* pin — that the anchor names are emitted, uniquely paired, and that
the CSS carries the placement contract — and the matrix row is honest that
genuine placement rests on the browser walk in Test Plan step 3a.
