# Journal: 2026-10-12-bc-tooling

<!-- fr:journal kind=repro scope=debug id=28a1ec65a178 created=2026-10-11T22:12:18+00:00 -->
### 28a1ec65a178 · repro · R1 flags subgraph edges that real mermaid renders; width gate verdict is host-dependent with no margin

#74: tools/validate_mermaid.py R1 rejects any edge whose endpoint is a subgraph id ('edges must connect nodes, not subgraphs'). Rendered with real mermaid 11.16.1 in headless Chrome 
(validate_mermaid_layout.mjs --max-width 1): node->subgraph 159px, frank 05-gitops 'Git --> Root' 438px, subgraph->subgraph 342px, labelled/dotted subgraph edges 381px, member->own parent 223px — all sized SVGs, no parse error. Control 'A[unclosed --> B' -> RENDER ERROR. 
#75: validate_mermaid_layout.mjs compares Math.round(width) > maxWidth with no margin and prints neither browser build nor platform; frank measured the same diagram 1395px on macOS Chrome (OK) vs 1414px on ubuntu-latest (FAILED).

<!-- fr:journal kind=root-cause scope=debug id=797b1e1c8fc8 created=2026-10-11T22:12:21+00:00 -->
### 797b1e1c8fc8 · root-cause · #74: R1's premise is false — mermaid flowcharts accept subgraph ids as edge endpoints

The rule encodes a belief (edges must connect nodes) that mermaid's flowchart grammar does not hold: subgraph ids are valid edge endpoints in every form tested. No narrower failing form was found, so there is nothing for a narrowed rule to match. Fix: drop R1; pin with a test that the former R1 fixtures lint clean, and a browser test that they render.
