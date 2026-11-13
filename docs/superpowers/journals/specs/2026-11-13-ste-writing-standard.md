<!-- fr:journal-schema=3 -->
# Journal: 2026-11-13-ste-writing-standard

<!-- fr:journal kind=discovery scope=spec id=brief created=2026-11-13T11:50:19+00:00 input=true -->
### brief · discovery · Operator brief (verbatim)

Turn 1: "can you write a few of the fr documentation & explainer pages with ASD-STE100 and show them here for comparison? Are the current pages using a standard today? What is decided by blog-craft?"

Turn 2: "make the side-by-side comparison page

What about a blog-craft feature that uses STE as another writing method and we use it in super-fr afterwards to regenerate the explainers/documentation?"

Turn 3: "yes, add blog-craft and start the brainstorm"

<!-- fr:journal kind=decision scope=spec id=d-scope created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-scope · decision · First release: checker + rewrite + fact check

Operator chose the recommended scope: deterministic checker and rules reference, batch rewrite of any Markdown, read-only fact-check subagent.

<!-- fr:journal kind=decision scope=spec id=d-strictness created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-strictness · decision · Exact checks fail, heuristic checks warn

Sentence length, contractions, one instruction per step fail; passive, -ing, vocabulary warn; every severity overridable fail|warn|off.

<!-- fr:journal kind=decision scope=spec id=d-vocabulary created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-vocabulary · decision · Own replacement list, no ASD dictionary text

Feature described as 'STE writing rules, based on ASD-STE100', never STE-conformant; product terms exempt.

<!-- fr:journal kind=decision scope=spec id=d-optin created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-optin · decision · Opt-in by front matter plus group default

writing_standard front matter wins; else series default (blog) or CLI --default (no blog config).

<!-- fr:journal kind=decision scope=spec id=d-home created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-home · decision · New skill apply-writing-standard, standard as a parameter

Operator: 'new skill, apply-writing-standard with the standard passed as a parameter. We can even ship multiple writing standards'. A standard is a registry entry; ste is the first.

<!-- fr:journal kind=decision scope=spec id=d-verification created=2026-11-13T12:00:27+00:00 decided_by=operator -->
### d-verification · decision · CI plus one pre-merge client-live rewrite, no post-merge gate

Unit tests for checker/registry/selection; one client-live walk of the skill on two super-fr pages; super-fr adoption is a separate super-fr feature.

<!-- fr:journal kind=decision scope=spec id=d-three-standards created=2026-11-13T12:17:55+00:00 decided_by=operator -->
### d-three-standards · decision · Ship three standards: ste, elements-of-style, plain-language

Operator: "let's extend this by shipping a second and third standard": The Elements of Style (Strunk & White) and Plain English / Plain Language, "We could try these for the explainers". Built on Strunk 1918 (public domain) and the US Federal Plain Language Guidelines (US government work); check data moves to named instances of a closed set of kinds.

<!-- fr:journal kind=decision scope=spec id=d-verify-none created=2026-11-13T13:23:39+00:00 decided_by=operator -->
### d-verify-none · decision · No live walk: verify none, unit and contract tests suffice

Operator: "verify: none, the tests should suffice". Replaces the client-live walk of decision d-verification.
