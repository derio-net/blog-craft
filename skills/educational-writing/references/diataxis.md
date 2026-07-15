# Diátaxis, adapted for teaching blog posts

Diátaxis (Daniele Procida, <https://diataxis.fr/>) is the established framework
for structuring technical documentation around what the reader is actually
trying to do. It names four modes and insists they not be blended. A blog post
is not a docs site, but the same discipline is what separates a useful post from
session narrative: **decide the mode, then serve it.**

We adopt Diátaxis; we don't reinvent it. When in doubt, the canonical source
governs.

## The compass

Ask two questions about the reader in front of this post:

1. Do they need to **act** (do something now) or to **understand** (build a mental model)?
2. Are they **studying** (acquiring a skill they don't have) or **working** (applying a skill they have, to a real goal)?

| | **Action** | **Cognition** |
|---|---|---|
| **Acquisition** (studying) | **Tutorial** | **Explanation** |
| **Application** (working) | **How-to guide** | **Reference** |

Or, phrased as a lookup:

| If the content… | …and serves | then it is a |
|---|---|---|
| describes practical steps | acquiring a skill | **tutorial** |
| describes practical steps | a real-world goal | **how-to guide** |
| provides theoretical knowledge | a real-world goal | **reference** |
| provides theoretical knowledge | understanding | **explanation** |

## The four modes, and how to write each well

### Tutorial — "follow me and you'll learn"
A lesson. The reader is a beginner; you are the teacher; you take responsibility
for their success. Every step must work. No choices, no "you could also" — a
tutorial is a guided path, not a menu.
- **Quality test:** a novice who follows it verbatim reaches a working result and feels they learned.
- **Fails when:** it stops to explain *why* mid-step, offers options, or assumes prior knowledge it should be teaching.

### How-to guide — "you have a goal; here's how"  ← the one most posts should be
Directions for a **competent** reader with a **specific real-world goal** ("get
the homelab to shut down before the UPS dies"). It is a sequence of actions, not
a lesson. It omits what a competent reader already knows and includes exactly
what the goal requires.
- **Quality test:** a reader with the stated goal, under time pressure, gets it done without reading anything else.
- **Fails when:** it becomes a tutorial (over-explains), a narrative ("here's how *we* did it"), or an essay (why before what). Lead with the steps.

### Reference — "the facts, exactly"
Dry, complete, accurate description a reader looks things up in: flags, config
keys, paths, default values, thresholds, return codes. Structured for scanning,
not reading. No opinion, no how-to.
- **Quality test:** a reader finds the exact value/flag in seconds and trusts it.
- **Fails when:** it editorializes, or when facts a reader needs are buried in prose elsewhere instead of tabulated here.

### Explanation — "why it is the way it is"
Background, context, design rationale, tradeoffs, the alternatives you rejected.
It serves *understanding*, read away from the keyboard. This is where the
genuinely interesting "story" belongs — but labelled as explanation, not smuggled
into the how-to.
- **Quality test:** the reader comes away understanding *why*, able to make their own decisions in situations you didn't cover.
- **Fails when:** it masquerades as instruction, or when it's the *only* mode present and the reader still can't do anything.

## Applying it to a blog post

- **Commit to one primary mode.** State it in frontmatter (`diataxis:`). A post may carry a second mode if it's a clearly separated section (a how-to guide with a short Reference table at the end is the workhorse pattern).
- **Split, don't blend.** If a draft is trying to be all four, it's four posts — or one how-to with the explanation moved to its own section (or a companion post in the "why" track).
- **The homelab lesson.** The graceful-shutdown posts should have been: a **how-to guide** ("make your homelab shut down on power loss") + a **reference** block (the NUT/`upsmon` config keys, thresholds, and the recovery command), with the war-story moved to a short **explanation** section clearly marked as such. What shipped was explanation-as-narrative with the how-to missing. That inversion is the single most common failure this framework catches.

## The map of modes (mnemonic)

- Tutorial is **learning-oriented** → *"take my hand."*
- How-to is **task-oriented** → *"here's the recipe."*
- Reference is **information-oriented** → *"look it up."*
- Explanation is **understanding-oriented** → *"let me tell you why."*

Sources: <https://diataxis.fr/>, <https://diataxis.fr/compass/>. See the site for
the full treatment; this file is the working subset blog-craft applies.
