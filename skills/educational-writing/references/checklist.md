# Pre-publish checklist

The mechanical gate (`validate_educational.py`) enforces the first block. The
rest are the fuzzy things no validator can see — a human (or the drafting model)
runs them. A post ships when the gate passes **and** the judgment items hold.

## Gate — enforced mechanically (must all pass)

- [ ] **`reader_goal`** in frontmatter states, in one line, what the reader can *do* after reading.
- [ ] **`diataxis`** declares the mode(s): tutorial / how-to / reference / explanation.
- [ ] At least one **command/output code block** (real, copy-pasteable; mermaid doesn't count).
- [ ] At least one **actionable section** a reader under pressure can follow (Reproduce / Runbook / Steps / Verify / Recover).

## Orientation — the reader must not feel lost

- [ ] A **set-the-stage** opening states the motivation (the concrete problem), what it solves, and the one load-bearing design choice — before `Step 1`.
- [ ] The **foundation is named**: "you need A, B, C" — with links to the earlier posts where A/B/C were built, rather than re-explaining them.
- [ ] The `voice_level` fits the blog/post (`dry`/`balanced`/`rich`); a `balanced`+ draft reads oriented and human, not cold.

## The 2am test — judgment (must hold)

- [ ] A reader with the stated `reader_goal`, under time pressure, can act on this post **without reading anything else**.
- [ ] The **one command that matters** is in a block, near the top of its section, not buried in prose.
- [ ] An operational post has an unmissable **recovery / "when it breaks" path**.
- [ ] Every **Verify** step is the real command + its success/failure signature, not a description of it.
- [ ] Code snippets are **expanded/multi-line**, not compressed flow-style; non-obvious lines are commented.

## Mode discipline

- [ ] The post commits to its declared primary mode; a second mode (if any) is a **clearly separated section**, not blended in.
- [ ] **How-to leads with steps.** Any substantial *why* lives in a labelled Explanation section or a companion post — it does not delay the first runnable step.
- [ ] Reference facts (flags, config keys, thresholds, paths) are **tabulated**, not scattered through paragraphs.

## Evidence

- [ ] Every trust-me claim ("fast", "safe", "graceful", "under Ns") has an artifact next to it (command+output, `file:line`, commit, test) — or is cut.
- [ ] Citations are **specific**: `path/file:line`, a commit SHA, or a test name — not "see the script".
- [ ] Commands and outputs are **real**, not idealized or paraphrased.

## Persona (thin frame)

- [ ] Deleting every in-character sentence would leave the teaching **intact** — the persona carries no load the substance should.
- [ ] No **in-jokes** or **"you had to be there"** asides. Wit remains only where it aids memory/application.
- [ ] No **session narrative** ("we then tried… turns out…") standing in for instruction.

## Housekeeping

- [ ] `draft: false` only when the above hold.
- [ ] Media markers filled (`/media`) or removed; no orphan `<!-- MEDIA: -->`.
- [ ] Cover image present and on-metaphor.
- [ ] If the post **mirrors code state** (no in-post "Update" logs), it shows a visible **last-updated date + commit link** (`last_updated` + `last_updated_commit` frontmatter; the `{{< last-updated >}}` shortcode renders it) so a reader knows how current it is and can diff since.
