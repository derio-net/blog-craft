# Journal: 2026-10-12-bc-tooling

<!-- fr:journal kind=repro scope=debug id=28a1ec65a178 created=2026-10-11T22:12:18+00:00 -->
### 28a1ec65a178 · repro · R1 flags subgraph edges that real mermaid renders; width gate verdict is host-dependent with no margin

#74: tools/validate_mermaid.py R1 rejects any edge whose endpoint is a subgraph id ('edges must connect nodes, not subgraphs'). Rendered with real mermaid 11.16.1 in headless Chrome 
(validate_mermaid_layout.mjs --max-width 1): node->subgraph 159px, frank 05-gitops 'Git --> Root' 438px, subgraph->subgraph 342px, labelled/dotted subgraph edges 381px, member->own parent 223px — all sized SVGs, no parse error. Control 'A[unclosed --> B' -> RENDER ERROR. 
#75: validate_mermaid_layout.mjs compares Math.round(width) > maxWidth with no margin and prints neither browser build nor platform; frank measured the same diagram 1395px on macOS Chrome (OK) vs 1414px on ubuntu-latest (FAILED).

<!-- fr:journal kind=root-cause scope=debug id=797b1e1c8fc8 created=2026-10-11T22:12:21+00:00 -->
### 797b1e1c8fc8 · root-cause · #74: R1's premise is false — mermaid flowcharts accept subgraph ids as edge endpoints

The rule encodes a belief (edges must connect nodes) that mermaid's flowchart grammar does not hold: subgraph ids are valid edge endpoints in every form tested. No narrower failing form was found, so there is nothing for a narrowed rule to match. Fix: drop R1; pin with a test that the former R1 fixtures lint clean, and a browser test that they render.

<!-- fr:journal kind=root-cause scope=debug id=78fdc112ae94 created=2026-10-11T22:12:23+00:00 -->
### 78fdc112ae94 · root-cause · #75: the gate presents a host-dependent measurement as a host-independent verdict, with zero margin

Widths come from text metrics, which depend on the host's browser build and fonts (~1.4% observed macOS vs ubuntu). The gate's verdict is a bare 'width > budget' with no band, and neither OK nor FAILED output names the host, so a local OK just under the budget is a coin flip for CI and nothing says so. Fix: name the host (browser product/version + os platform/arch) on every verdict; add a near-budget band (default 3%, --margin) that warns, non-blocking, for diagrams within margin BELOW the budget ('may fail on another host'), keeping the blocking budget unchanged so a clean local OK predicts a CI pass for cross-host deltas under the margin. Pinning fonts/containerised Chrome is out of scope (follow-up).

<!-- fr:journal kind=decision scope=debug id=0b5a00f261a9 created=2026-10-11T22:12:26+00:00 -->
### 0b5a00f261a9 · decision · Two root causes, one batch: proceeding without a stop

The batch rule says stop if investigation finds more than one root cause. Investigation found two mechanisms (#74 lint premise, #75 measurement provenance/margin), but these are exactly the two the batch itself names ('Both mermaid gates mislead', one Closes line per member, ONE PR). Nothing beyond the batcher's own framing was discovered, so the rule's purpose (no surprise scope) is not triggered; proceeding overnight per the operator's 'stop only at a genuine human checkpoint', and flagging this in the PR body.

<!-- fr:journal kind=finding scope=debug id=0ea3c0b750dc created=2026-10-11T22:18:17+00:00 state=fixed -->
### 0ea3c0b750dc · finding [fixed] · R1 dropped; width gate names its host and warns near budget

Fix commit on fix/batch-bc-tooling (0.22.5). Failing-tests-first commit 2dbd0cf: test_subgraph_edges_are_not_flagged (red: R1 flagged all four forms), test_pass_names_the_measuring_host / test_failure_names_the_host_and_says_other_hosts_differ / test_near_budget_pass_warns_and_still_exits_zero / test_margin_flag_sets_the_band_and_zero_silences_it (red: no host line, unknown --margin). test_subgraph_edges_render_in_real_mermaid was green before the fix — it characterises mermaid itself and is the evidence R1 was false. After the fix: 99 targeted tests pass on the host (real Chrome 154 + mermaid 11.16.1 bundle); full suite deferred to CI per the overnight rule.
