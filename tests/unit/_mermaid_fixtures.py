"""Shared mermaid sources for the syntax-linter and layout-gate tests."""

# Edges with a subgraph endpoint are VALID mermaid (#74). The former R1 rule
# flagged them as "dead on render"; every form below renders a sized diagram in
# real mermaid (pinned by test_mermaid_layout_gate's
# test_subgraph_edges_render_in_real_mermaid). An edge to a group is often the
# semantically right level — a linter rejecting it pushes authors to make
# diagrams narrower and less true.
SUBGRAPH_EDGES = {
    "node-to-subgraph": "flowchart TD\n subgraph db\n  pg[x]\n end\n A --> db\n",
    "labelled-subgraph-to-node": (
        "flowchart LR\n subgraph Git[Git Repo]\n  m[manifests]\n end\n"
        " subgraph Cluster\n  Root[Root App]\n end\n Git --> Root\n"),
    "subgraph-to-subgraph": (
        "flowchart LR\n subgraph a\n  x\n end\n subgraph b\n  y\n end\n"
        " a -->|feeds| b\n b -.-> a\n"),
    "member-to-own-parent": (
        "flowchart TD\n subgraph outer\n  subgraph inner\n   n1\n  end\n end\n"
        " n1 --> outer\n"),
}
