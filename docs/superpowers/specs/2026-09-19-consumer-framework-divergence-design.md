# Consumer Framework Divergence Design

## Problem

`/update` treats every `framework` path as upstream-owned and replaces it.
That silently erases a consumer's intentional edit to a layout, shortcode, or
script. A consumer needs an explicit way to declare that its local variant is
intentional and have future updates preserve both its change and compatible
upstream changes.

## Decision

Add an optional consumer-owned `.blog-craft.overrides.yaml` at the blog root.
It declares deliberate divergences from framework-owned files:

```yaml
overrides:
  - path: layouts/_default/home.html
    reason: Keep the consumer's mobile navigation treatment.
    upstream_ref: v0.22.1
```

`path`, `reason`, and `upstream_ref` are required non-empty strings. `path`
must name a framework-class staging path. Duplicate paths and paths in another
ownership class are invalid. The updater never materializes or modifies this
manifest; it remains a consumer-owned control file.

When `/update` reads a valid override declaration for a materialized
framework path, it exposes that path as the new `divergence` classification
rather than `framework`. A divergence uses the existing three-way merge
pipeline:

* base: the recorded-version render from `.blog-craft.sync.yaml` (or the
  existing clearly warned fallback);
* local: the consumer's on-disk file;
* incoming: the current staging render.

The resulting action is `merge`, `noop`, or `conflict` under the same rules as
the established `merged` class. It is never `replace`. The dry run labels the
entry `[divergence]`, making the operator-visible classification explicit.
An absent override file leaves existing update behavior byte-for-byte
unchanged.

## Classification Model

The framework manifest continues to say which paths blog-craft owns by
default: `framework`, `merged`, and `content`. Consumer declarations create
an update-time fourth classification, `divergence`, only by opting a declared
framework path into merge semantics. This separates upstream ownership from
the consumer's intentional local evolution without broadening ordinary
`merged` behavior.

## Scope

This change delivers the override-file parser, validation, update-time
classification, merge behavior, dry-run label, and unit coverage. The
operator decision was recorded 2026-09-19: implement the issue's recommended
manifest mechanism, limited to one end-to-end working mechanism.

## Deferred

The following issue proposals are deliberately not implemented here:

* Refusing an undeclared local change to a framework path at apply time.
* Reporting declared divergences that have converged upstream and suggesting
  removal.
* Hugo module/template shadowing.
* New template extension points.
* Structural TOML/YAML merging.
* Automatic creation or mutation of the consumer override file.

## Acceptance

An operator who declares an intentional change to a framework file can run
`/update` and retain that change while a non-conflicting upstream change lands;
the plan labels the path as a divergence. Invalid declarations fail before any
update plan is produced, and an undeclared framework path continues to use
the existing replacement behavior.

## Test Plan

1. Run the updater unit suite: `uv run pytest tests/unit/test_update_flow.py`
   and verify declared framework divergence is cleanly merged, labelled in the
   dry run, and applied.
2. Verify invalid declarations (missing reason, non-framework path, duplicate
   path) are rejected.
3. Verify the same local framework edit without an override remains a
   `replace`, preserving compatibility.

Post-merge: no operator-driven deployment test is required; this is a
deterministic local updater behavior covered by the automated unit suite.

## Implementation Plans

| Plan | Repo | File | Depends on |
| --- | --- | --- | --- |
| 2026-09-19-consumer-framework-divergence | `derio-net/blog-craft` | `2026-09-19-consumer-framework-divergence` | — |
