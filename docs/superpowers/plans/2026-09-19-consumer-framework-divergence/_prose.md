# Issue #88 Implementation Plan

Implement the declared-divergence mechanism from
`2026-09-19-consumer-framework-divergence-design.md`. The first phase creates
a strict consumer manifest boundary with tests. The second phase consumes that
boundary in `/update`, preserving the existing three-way merge behavior and
the default framework replacement behavior.

The plan intentionally does not add undeclared-drift refusal, upstream
convergence reporting, structural config merging, Hugo modules, or extension
points. Those are deferred by the approved specification.

Verification is the focused updater unit suite, including its existing
application tests. No manual phase is needed.
