# Hand-built CSS schematics (when Mermaid fights the content)

Mermaid is the default for explainer diagrams — themed per `--style`, zero
layout work. But for a few archetypes its auto-layout fights the content, and a
small set of **CSS-only schematic primitives** reads as *intentional* rather
than generated. These are for hand-authored HTML blocks inside an explainer
(raw HTML passes through markdown), paired with the `broadsheet` style whose
tokens they reference.

Reach for a schematic only when Mermaid genuinely can't express the shape well:

| Archetype | Why Mermaid struggles | Schematic |
|---|---|---|
| Nested boundaries (host ⊃ container ⊃ process) | subgraph nesting renders as cramped boxes | `.boundary` nested divs |
| Decision staircase (if→elif→else cascade) | flowchart branches sprawl horizontally | `.ledger` ordered steps |
| Assembly-line flow (stage → stage → stage) | LR graph wraps unpredictably | `.rail` flex row with `→` separators |

## Tokens

All primitives use the broadsheet CSS variables (`--brass`, `--teal`, `--line`,
`--ink-2`, `--paper`, `--mono`), so a schematic matches the page automatically.
Do **not** hard-code colors — reference the variables, so a future palette
change carries through. The key rule from `frontend-design`: **dominant tones
with accents that carry meaning** (brass = human/attention, teal =
automated/verified), never an evenly-spread palette.

## Primitives

### Nested boundary

```html
<div class="boundary"><span class="eyebrow">host</span>
  <div class="boundary"><span class="eyebrow">container</span>
    <code>process</code>
  </div>
</div>
```
```css
.boundary{border:1px solid var(--line);border-radius:6px;padding:1rem;margin:.5rem 0}
.boundary .boundary{border-color:var(--teal)}
```

### Assembly-line rail

```html
<div class="rail"><span>fetch</span><span>embed</span><span>render</span></div>
```
```css
.rail{display:flex;gap:.75rem;align-items:center;font-family:var(--mono);font-size:.8rem}
.rail>span{border:1px solid var(--line);padding:.4rem .7rem;border-radius:4px}
.rail>span+span::before{content:"→";color:var(--brass);margin-right:.75rem;margin-left:-.35rem}
```

### Decision ledger

Use the theme's `.ledger` (numbered, `decimal-leading-zero`) for a decision
staircase — each `<li>` is one branch, in order, with the condition in `<code>`.

## When NOT to use a schematic

- The diagram is a genuine graph (nodes + edges, cycles) → Mermaid.
- You'd hand-place more than ~6 boxes → the maintenance cost isn't worth it.
- The page isn't `broadsheet` → the tokens won't be defined.
