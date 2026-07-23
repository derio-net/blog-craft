# Journal: 2026-07-23-marketplace-namespace-collision

<!-- fr:journal kind=root-cause scope=debug id=rc-1 created=2026-07-23T18:19:04 -->
### rc-1 · root-cause · blog-craft squatted super-fr's derio-net marketplace name; both installers rsync --delete'd the shared dir

A Claude Code marketplace name is a 1:1 namespace over ONE source repo. Its
manifest — `~/.claude/plugins/marketplaces/<name>/.claude-plugin/marketplace.json`
— is a single file listing every plugin of that marketplace, and every installer
populates it with `rsync -a --delete <own repo root>/`: replace, never merge.

blog-craft `scripts/install.sh:22` claimed `derio-net`, the name super-fr owns
and declares in its own manifest. Our own `.claude-plugin/marketplace.json`
declares `"name": "blog-craft"` — the installer contradicted our own manifest.
Both repos rsync-ed into the same directory, so whichever installer ran last
evicted the other's plugins from the manifest while their `enabledPlugins` and
`installed_plugins.json` entries survived as dangling references.

Full investigation (host evidence, hypothesis trail) lives in super-fr:
docs/superpowers/journals/debug/2026-07-23-marketplace-config-clobber.md — PR #392.

<!-- fr:journal kind=finding scope=debug id=fix-1 created=2026-07-23T18:19:05 state=fixed -->
### fix-1 · finding [fixed] · Move to the blog-craft marketplace; own-key writes; ownership-scoped uninstall + migration

- `MARKETPLACE_NAME=blog-craft` -> `marketplaces/blog-craft`, `cache/blog-craft`,
  plugin id `blog-craft@blog-craft`. Never registers `derio-net` again.
- Registry writes are UNCONDITIONAL on our own key (was skip-if-present, i.e.
  first-writer-wins), so a stale `directory`-source entry from the pre-plugin
  era converges instead of persisting.
- `--uninstall` deletes only keys we own. It used to run `del(."derio-net")` on
  both registries — deregistering super-fr@derio-net and
  super-fr-dispatch@derio-net along with blog-craft.
- Migration for machines that ran the old installer: drops
  `blog-craft@derio-net` from installed_plugins.json + enabledPlugins, removes
  `cache/derio-net/blog-craft`, and vacates `marketplaces/derio-net` ONLY when
  the manifest there is still ours — leaving a manifest that lies about the
  marketplace identity is worse than an empty slot. The `derio-net` key itself
  and every other `*@derio-net` plugin are untouched.
- Drive-by: the preflight `[ ! -d "$PLUGIN_ROOT/.git" ]` rejected every linked
  worktree (`.git` is a FILE there), so install.sh could not run from an
  fr-isolation workspace at all. Now asks git via `rev-parse --is-inside-work-tree`.

Failing test first: tests/unit/test_install_marketplace_namespace.py — 14 tests,
13 red before the fix. Full suite 391 passed. Acceptance row OC-4
not-implemented -> skipped. Version 0.10.0 -> 0.10.1.

<!-- fr:journal kind=finding scope=debug id=fix-rename created=2026-07-23T19:02:14 state=fixed -->
### fix-rename · finding [fixed] · Operator decision: retire bare marketplace names; both repos become <org>--<repo>

Supersedes fix-1 (which moved blog-craft to the bare name `blog-craft` while
super-fr kept `derio-net`). The operator chose the stronger invariant: no repo
owns an org-level namespace.

  blog-craft -> derio-net--blog-craft
  super-fr   -> derio-net--super-fr
  derio-net  -> RETIRED; both installers purge it on sight
  blog-craft (bare) -> also retired: our own pre-plugin directory-source name

Why this beats the asymmetric fix:
- Closes the trap for optionality-fr and every future derio-net plugin, not
  just for this pair.
- `<org>--<repo>` makes the 1:1 name<->repo rule self-documenting, so the next
  installer author cannot repeat the mistake by copying.
- The purge becomes safe BY CONSTRUCTION. The earlier design had to leave the
  `derio-net` key alone because super-fr owned it; once no repo owns it, every
  `*@derio-net` id is dangling by definition and removing the whole key is not
  cross-repo interference. That objection dissolves.

`--uninstall` now scopes by OUR plugin name and OUR marketplace names, so a
sibling registered under `derio-net--super-fr` survives untouched — pinned by
test_leaves_a_siblings_marketplace_registered.

Note the id/key disjointness this relies on: `blog-craft@derio-net--blog-craft`
does NOT end with `@blog-craft` (it ends `--blog-craft`), so the bare-name purge
cannot eat the id we just wrote. Same for super-fr. Pinned by
test_idempotent_across_reinstalls on both sides.

Also: scripts/validate-plans.sh delegates into super-fr's marketplace dir, which
moved in the same rename — updated to derio-net--super-fr.

Suite 395 passed. Acceptance 32 rows OK. Version 0.10.1 -> 0.11.0 (breaking
plugin-id change).
