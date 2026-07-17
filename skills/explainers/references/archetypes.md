# Explainer Archetypes — Content Recipes

Each recipe gives the content guidance for one explainer archetype. All five
are **scaffolded and validated**: `scaffold-explainer.sh --archetype <id>`
emits the section headings below, and `validate_explainers.py` enforces them.
Use this recipe for what each section should contain (and its recommended
visual); follow the same find/research/draft/publish lifecycle as
`feature-deep-dive`.

---

## Presenting a Claude Skill

`id: skill-presentation`

**When to use:** Writing about a single skill — what it does, when it
triggers, its workflow, and how to invoke it.

**Section structure:**

- **Overview** — one paragraph: what the skill does and the problem it solves.
- **When it triggers** — the conditions that activate it (user phrases, repo
  context, config gates). Include a concrete invocation example.
- **Workflow** — step-by-step lifecycle (what the skill does from start to
  finish). Use a Mermaid sequence diagram or flowchart if the flow has
  branches.
- **Configuration** — what the operator configures (skill arguments, config
  knobs, environment variables). A table or Hextra `cards` if comparing
  config options.
- **Try it yourself** — minimal reproducible invocation with expected output.

**Visuals:** 1 Mermaid flowchart of the workflow; code blocks for invocation
examples.

---

## Comparing Two Similar Skills

`id: skill-comparison`

**When to use:** Side-by-side comparison of two skills or tools that overlap
in function.

**Section structure:**

- **Overview** — what both skills do, why a comparison matters.
- **Side-by-side** — Hextra `cards` or a Markdown table: capability matrix
  (feature rows, skill columns). Mark each cell ✓/✗/partial with a one-line
  note.
- **When to choose which** — decision criteria: context size, autonomy level,
  output format, cost. A Mermaid decision flowchart with ≤4 leaves.
- **Concrete divergence** — one specific scenario where the two skills
  produce different results; show both outputs.
- **Try it yourself** — invoke both on the same input, compare outputs.

**Visuals:** 1 capability-matrix table; 1 Mermaid decision flowchart.

---

## Testing Pyramid

`id: testing-pyramid`

**When to use:** Explaining the testing layers and their distribution in a
specific repo.

**Section structure:**

- **Overview** — what the testing strategy is and why this shape.
- **The pyramid** — Mermaid pyramid or flowchart of the repo's actual layers
  with real counts (e.g. "47 unit, 12 integration, 3 E2E"). Label each layer
  with the test directory or runner.
- **One example per layer** — a minimal test from each layer, with a
  `file:line` reference and a one-sentence explanation of what it covers and
  why it lives at that layer.
- **Gaps and tradeoffs** — what's missing or under-tested, any deliberate
  choices (e.g. "no E2E for the CLI because...").
- **Try it yourself** — how to run the full suite, how to run one layer.

**Visuals:** 1 Mermaid pyramid/flowchart with real counts.

---

## Deployment Strategy

`id: deployment-strategy`

**When to use:** Walking through how code gets from merge to production in a
specific repo.

**Section structure:**

- **Overview** — one paragraph: the deployment model (CI/CD, manual, hybrid).
- **The pipeline** — Mermaid flowchart of the actual CI/CD flow: triggers,
  jobs, gates, environments. Label each node with the workflow file and job
  name.
- **Environments** — table of environments (staging, production, canary),
  what deploys to each, and how promotion works.
- **Rollback path** — how to revert: the command, the trigger, the expected
  time-to-recover.
- **Try it yourself** — how to trigger a deploy manually (if possible), how
  to verify it landed.

**Visuals:** 1 Mermaid pipeline flowchart; 1 environment table.

---

## Security Posture

`id: security-posture`

**When to use:** Explaining what's enforced, what's manual, and what the
threat surface looks like for a specific repo or feature.

**Section structure:**

- **Threat surface** — what's exposed (endpoints, file access, secrets, CI
  inputs). One sentence per surface, rated high/medium/low.
- **What's enforced in CI** — automated checks: secret scanning, dependency
  auditing, SAST, permission boundaries. Name the workflow and the tool.
- **What's manual** — things that require human review: privilege escalation,
  credential rotation, infrastructure changes. Why they can't be automated.
- **One concrete control** — deep-dive on one control: what it enforces,
  where it's defined (file:line), how it's tested (if at all).
- **Try it yourself** — how to run the security checks locally.

**Visuals:** 1 table of controls vs. enforcement points; optional Mermaid
data-flow diagram showing trust boundaries.
