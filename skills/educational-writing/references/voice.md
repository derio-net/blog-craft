# The voice dial (`voice_level`)

The persona is a frame, not the substance — but *how thick* the frame should be
is a real choice, and different blogs (and different posts) want it set
differently. `voice_level` is that dial. It changes **how much personality colors
the teaching**; it never changes what evidence a post must carry, the mode
discipline, or the gate. Dryness is orthogonal to correctness.

Set it in `.blog-craft.yaml` (`voice_level: <level>`, default `balanced`), and
override per-run with the `/post-rewrite` or `/blog-post` `voice_level` argument.
It works *with* the freeform `voice:` string: `voice` describes the character and
tone; `voice_level` decides how loud it is.

## The three levels

| Level | Feels like | Persona in the body | Use when |
|-------|-----------|---------------------|----------|
| `dry` | clean technical docs | almost none — the cover image is the flavor | reference-heavy posts; a reader who wants facts and out |
| `balanced` *(default)* | a knowledgeable friend explaining | a thin frame + a warm orientation + asides that *aid memory* | most teaching posts — oriented and human, but the how-to leads |
| `rich` | the persona narrating the build | voiced throughout — transitions, stakes, character — while every section still carries its evidence and the how-to still leads | story-forward blogs where the character *is* part of the draw |

What the dial actually moves, going `dry` → `balanced` → `rich`:

- **Orientation warmth.** `dry` states the problem in two sentences; `balanced`
  sets the stage with stakes a reader feels; `rich` opens in-character.
- **Aside frequency.** `dry`: none. `balanced`: only where an aside makes a fact
  stick. `rich`: regular, as connective tissue — but never *replacing* substance.
- **Transition prose.** `dry`: headings do the work. `rich`: the narrator carries
  you between sections.
- **How the "why" is told.** `dry`: a terse rationale line. `rich`: the decision
  narrative, voiced (still in the labelled Explanation section, not blocking the how-to).

What the dial **never** moves:

- Evidence — real commands/output, `file:line`, config values (all levels).
- The reader_goal, the declared Diátaxis mode, the actionable section (the gate).
- The rule that deleting every in-character sentence must leave the teaching intact.
  Even `rich` obeys this — richer framing, same load-bearing structure underneath.

## Calibrating

If a `balanced` draft reads cold and a reader would feel *lost* — no sense of why
they're here — it's under-framed; warm the orientation and add one or two asides
that aid recall. If a `rich` draft has paragraphs you could delete with no loss to
the teaching, it's tipped into session-narrative — cut them; that's the failure
mode `rich` is closest to. The dial's whole job is to let a blog sit where it
wants on that spectrum *without* sliding into prose-about-the-session.
