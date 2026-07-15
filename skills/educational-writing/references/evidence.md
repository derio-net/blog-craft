# Evidence-grounding — gather before you write

A teaching post is only as trustworthy as the artifacts under it. The rule is
blunt: **no claim without a citable artifact.** This file is how you gather them,
and what counts.

## What counts as evidence (in rough order of value)

1. **Real command + real output.** The actual invocation and what it printed, in a fenced block. Not paraphrased, not idealized. If output is long, trim with `# …` and keep the lines that matter.
2. **The actual source code**, read — not inferred. Open the files the post is about and report what they *do*. Every config value, flag, and behaviour must come from a file you read, not from a commit message, a doc, or a spec. When a doc and the code disagree, the code wins.
3. **`file:line` references** into the source repo — for the config, the script, the test. A reader can open exactly that line.
4. **Design docs — specs and plans.** If the repo uses a spec/plan workflow, read the design substrate: `docs/superpowers/{specs,plans}` and `docs/superpowers/implemented/{specs,plans}` (and any `docs/investigations/` the post references). They carry the *why* and the intended design.
5. **Intent-vs-implementation divergence.** Where the shipped code departed from the spec — a key that didn't exist, a component the plan assumed but the system lacks, a test that asserted the wrong thing — that gap is often the single most useful thing to teach: it's the wall the reader will hit.
6. **Commit SHAs** — the change that introduced the behaviour, so a reader can `git show` it.
7. **Test names + how to run them** — proof the behaviour holds, and a way to re-verify. `pytest tests/…::test_x` beats "it's tested."
8. **Config values in context** — the key, its file, the chosen value, and *why that value* (the threshold that matters for the reader's goal).
9. **Incident/failure timeline** — when the post chronicles something breaking, timestamps and the sequence: what fired, what didn't, what the log said, what recovered it.
10. **Media** — a screenshot or asciinema cast (via `/media`) only where a picture advances understanding a code block can't.

If a sentence asserts something a reader would want to trust ("it fails over in
under 2s", "this is safe", "it shuts down gracefully"), it needs one of the above
next to it — or it gets cut or softened to what you can show.

## Gathering it from a source repo: the `post-researcher` subagent

Heavy codebase exploration burns the drafting context. Dispatch the
`post-researcher` agent (see `agents/post-researcher.md`) at the source repo /
feature / incident. It is read-only and returns a **structured evidence brief**:
key files with `file:line` (read, not inferred), the design intent from the
repo's specs/plans cross-checked against what the code actually does, the real
commands and outputs it could capture from tests/docs, the relevant config with
values, the commit history behind the change, and any failure/recovery path it
found. You draft from the brief; the exploration stays out of your context.

Dispatch it when:
- The post chronicles work in another repo (the classic building/operating split).
- You're rewriting a post and need the evidence the original omitted.
- You need `file:line`/commit/test citations you don't already have in context.

You still capture **live** outputs yourself (running a command now, a screenshot)
— the subagent is read-only and won't run your homelab. It gathers what's *in the
repo*; you supply what's only observable *at runtime*.

## Turning evidence into the post

- **Lead with the runnable thing.** The command a reader needs goes in a block near the top of its section, not buried mid-paragraph.
- **Show, then explain — briefly.** Output first, one or two sentences on what to notice, move on. Save the deep *why* for the explanation section.
- **Tabulate reference facts.** Config keys, flags, thresholds → a table, not prose. A reader scans it at 2am.
- **Make the recovery path unmissable.** Operational posts need a "when it breaks, run this" block. That is often the single most-read part of the post.
- **Cite, don't gesture.** "See the shutdown script" → `scripts/graceful-shutdown.sh:42`. "It's configured in NUT" → the exact `upsmon.conf` lines.
- **Write snippets to be read and pasted — verbose over clever.** A reader scans
  and copies code; compressed flow-style fights both. Prefer expanded, multi-line
  form over inline maps/lists:

  ```yaml
  # do this
  loki:
    hostport: "http://192.168.55.225:9428"
    endpoint: "/insert/loki/api/v1/push"
  # not this
  loki: { hostport: "http://192.168.55.225:9428", endpoint: "/insert/loki/api/v1/push" }
  ```

  Keep a comment on any non-obvious line (why *this* value), and show enough
  surrounding context that the snippet is usable, not just illustrative.
- **Make verification runnable.** A "Verify" step is the actual command a reader
  runs plus what a right/wrong result looks like — not a description of it. Not
  "query the logs and you'll see the request lines"; give the query and the
  success/failure signature.

## The missteps table — a journey, not disconnected trivia

The wrong turns during a build are some of the most useful teaching there is —
*if* each carries enough context to stand on its own. A bare list of gotchas reads
as trivia; the same facts in a table with **what you assumed → why it was wrong →
what it cost / how you caught it** becomes a map of the terrain. Use it for the
design-time missteps (the plan that assumed a component that didn't exist, the
chart key that wasn't real) and keep it distinct from the runtime
symptom→cause→fix troubleshooting table — one is "what I got wrong building it,"
the other is "what breaks running it." Include a misstep only when you can give
its context; a row the reader can't connect to anything is noise.

## The self-check

For each major claim in the draft, ask: *what could a skeptical reader run or
open to verify this?* If the answer is "nothing — they'd have to take my word,"
you have either missing evidence to gather or a claim to cut.
