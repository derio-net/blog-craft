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
