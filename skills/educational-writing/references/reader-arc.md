# The reader's arc — beginning, middle, end

The most common structural failure of an AI-drafted post is the
**session-skeleton**: an outline that mirrors the work session's timeline — the
fork faced, the flag set, the proof run, the detour hit, the lesson learned.
From inside the session that order feels self-evidently important. To a reader
it is someone else's diary. The rule:

> A post is organized around the **reader's arc** — beginning, middle, end —
> never the session's chronology. The chronology is raw material; the arc is
> the outline.

The session tells you *what is true* (the evidence, the commands, the decision
that mattered). It does not tell you *what order a reader needs it in*. Outline
for the reader who wasn't there; then hang the session's artifacts on that
outline.

## Beginning — the lay of the land

Before the reader can care about your fork in the road, they need the map the
fork sits on. Open with the **conceptual landscape from general knowledge**:
the problem space, its standard shapes and names, and where this post's topic
sits in it — the paragraph a human expert would say out loud before touching a
keyboard. The worked example: a metrics-API post opens with *"Kubernetes has
two parallel metrics worlds — the resource pipeline (`metrics-server`, `kubectl
top`) and the custom/external pipeline (Prometheus adapters)"* — before any
cluster-specific fork appears. A reader who arrives knowing neither world now
has somewhere to stand; a reader who knows both skims one paragraph.

**Size it proportionally.** The beginning is sized to how idiosyncratic and
deep the meat is. A post whose middle is a standard install has earned a
two-sentence opening; a post whose middle forks on an obscure API-machinery
distinction owes the reader a real map first. An under-sized beginning strands
the reader; an over-sized one on shallow material is lecturing.

**It is mode-conditional.** Building chronicles and other **tutorial /
explanation** posts carry a real, labelled landscape section — for them the
landscape *is* part of the teaching, and it replaces the three-beat cap of
SKILL.md §2a. Operating **how-to / reference** posts keep the tight three-beat
orientation of §2a unchanged: steps-first is absolute, and the 2am reader does
not scroll past a lecture to reach the command. Key the choice off the
`diataxis` frontmatter, never off a series name.

## Middle — the meat

The evidence discipline of SKILL.md §2 is unchanged: every claim carries its
artifact, commands and outputs are real, and steps lead within their sections.
What the arc changes is how **decisions** are presented:

- Present each decision as the **space of options a reader in this situation
  would face** — the standard choices, what each trades away — with the
  session's choice as the **worked instance**: "given X and Y, we took B;
  here's what that looks like."
- Never present a decision as a timeline event. *"The fork I hit that
  afternoon"* is the anti-pattern: it makes the moment of encountering the
  choice the subject, when the choice itself is. The reader will meet the same
  fork at their own hour; give them the fork, not your afternoon.

The middle's headings are stops in the reader's arc ("Pick a metrics
pipeline", "Wire the adapter", "Verify the API serves"), not events in yours
("The first attempt", "Where it went wrong").

## End — what transfers

Close with a short **"What transfers"** section: what the reader keeps beyond
this repo, this cluster, this exact stack. Three shapes it can take:

- the **general rule** the specific work instantiated;
- the **portable decision heuristic** ("if you need per-pod numbers, start at
  the resource pipeline; the custom pipeline only when…");
- the **gotcha that generalizes** — the trap that will bite in any variant of
  this setup, not just yours.

This is explicitly **not a recap**. "In this post we configured X, then Y" is
a table of contents in past tense and teaches nothing twice. If a sentence in
the ending only restates what was done, cut it; if it tells the reader what to
do *next time in a different setup*, it belongs.

The lint layer backstops this: a tutorial/explanation post with no
what-transfers-style closing section draws a warning from
`validate_educational.py` (heading names in `ai-tells.md` `transfer_headings`).
The warning is the floor, not the bar — the section must actually transfer
something, which only judgment can check (see `checklist.md`).
