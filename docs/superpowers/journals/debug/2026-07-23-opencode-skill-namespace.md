# Journal: 2026-07-23-opencode-skill-namespace

<!-- fr:journal kind=root-cause scope=debug id=rc-1 created=2026-07-23T21:29:46 -->
### rc-1 · root-cause · OpenCode's flat global skill dir has no namespace layer; bare names like media/update collide

Follow-up to the marketplace-namespace work (super-fr#392, blog-craft#46). The
Claude Code MARKETPLACE trap does not exist in OpenCode (no marketplace/manifest/
rsync--delete), but a weaker cousin does: OpenCode discovers skills into ONE flat
global dir `~/.config/opencode/skills/<name>/` and commands into
`~/.config/opencode/commands/<name>.md`, keyed only by leaf name, shared with every
plugin and third-party skill. blog-craft shipped grabby generic names (media, update,
papers, explainers) with nothing protecting them.

OpenCode forbids real namespacing: skill names must match `^[a-z0-9]+(-[a-z0-9]+)*$`
(no colons/slashes) and it has no nested skill dirs. So Claude's `blog-craft:media`
form is illegal there; a hyphenated prefix is the only mechanism.

No ACTIVE bug (the derio-net repos' names are disjoint today), but a latent
collision risk vs third-party OpenCode skills / future repos.

<!-- fr:journal kind=finding scope=debug id=fix-1 created=2026-07-23T21:29:48 state=fixed -->
### fix-1 · finding [fixed] · Prefix blog-craft- in the OpenCode delivery layer only; canonical stays bare

Operator decision: OpenCode-only placement, prefix `blog-craft-` (chosen over bc-/
blcr-/cr- for maximal collision-safety). Rejected "rename canonical dirs" once the
mapping showed the skill names are entangled with content-type identities
(papers/explainers), tool names (update.py, media-fill.py) and the MEDIA marker
across ~25 live files + dozens of archived specs — a canonical rename would create a
skill-vs-content-type split (bc-papers skill vs papers content-type) and not deliver
the "one name everywhere" it promised. OpenCode-only confines the change to ~4 files.

Implementation:
- scripts/sync-opencode.py: mirror_name()=blog-craft-<name>; generates
  .opencode/skills/blog-craft-<name>/ with SKILL.md `name:` rewritten to match
  (OpenCode requires name==dir), body verbatim; .opencode/commands/blog-craft-<name>.md
  invoking the prefixed skill. Drift/sync/cleanup re-keyed on mirror names, so legacy
  bare mirror dirs are removed.
- scripts/install.sh: delivers OpenCode skills from the .opencode/ mirror (not
  canonical skills/); migrates off a stale bare-named copy ONLY when byte-identical to
  our own skill (cmp) / our own command body (grep marker) — never a same-named third
  party; --uninstall removes prefixed + stale-bare (same gate).
- Canonical skills/<name>/ UNCHANGED -> Claude Code stays blog-craft:media.

Tests: tests/unit/test_opencode_namespace.py (mirror contract + canonical-bare +
install delivery/migration/third-party-safety) and test_opencode_sync.py (--check).
Full suite 406 passed. Version 0.11.0 -> 0.12.0. Acceptance OC-4 skipped->ci; new row
opencode-skill-namespace (ci).
