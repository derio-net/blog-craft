# Journal: 2026-10-10-bc-operator-content

<!-- fr:journal kind=repro scope=debug id=4f7fb1e787f4 created=2026-10-10T18:32:54+00:00 -->
### 4f7fb1e787f4 · repro · #73: migrate_config strips comments and re-sorts keys

Config `# operator header` / `blog_craft_version: "v0.18.1"   # bump AFTER apply` / `zeta`, `alpha` at v6 -> `python tools/migrate_config.py cfg.yaml` -> output has no comments, keys alphabetical, quoting dropped. Cause visible at tools/migrate_config.py:70 (`yaml.safe_load` -> `yaml.safe_dump(sort_keys=True)`).

<!-- fr:journal kind=repro scope=debug id=16247b896084 created=2026-10-10T18:33:02+00:00 -->
### 16247b896084 · repro · #83: .gitignore REPLACEd wholesale on every --apply

templates/manifest.yaml:18 lists `.gitignore` under `framework`; tools/update.py:188 plans `replace` for any framework path whose bytes differ from staging, so operator-added lines (`*.bak`, `.DS_Store`) are dropped with no conflict. `merged` paths go through `git merge-file` 3-way (update.py:190-200).

<!-- fr:journal kind=root-cause scope=debug id=fbc726d2456c created=2026-10-10T18:33:12+00:00 -->
### fbc726d2456c · root-cause · Two independent root causes, not one

(1) migrate_config.py persists through a lossy PyYAML dict round-trip — comments/order/quoting are not representable in a dict, so any rewrite destroys them. (2) the manifest misclassifies `.gitignore` as framework (overwrite) though blogs are expected to extend it, like `assets/css/**` (merged). Shared theme only: /update rewrites operator-edited files wholesale. No single change fixes both; per batch rule, stopped to ask before fixing.
