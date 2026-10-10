# Journal: 2026-10-10-bc-operator-content

<!-- fr:journal kind=repro scope=debug id=4f7fb1e787f4 created=2026-10-10T18:32:54+00:00 -->
### 4f7fb1e787f4 · repro · #73: migrate_config strips comments and re-sorts keys

Config `# operator header` / `blog_craft_version: "v0.18.1"   # bump AFTER apply` / `zeta`, `alpha` at v6 -> `python tools/migrate_config.py cfg.yaml` -> output has no comments, keys alphabetical, quoting dropped. Cause visible at tools/migrate_config.py:70 (`yaml.safe_load` -> `yaml.safe_dump(sort_keys=True)`).

<!-- fr:journal kind=repro scope=debug id=16247b896084 created=2026-10-10T18:33:02+00:00 -->
### 16247b896084 · repro · #83: .gitignore REPLACEd wholesale on every --apply

templates/manifest.yaml:18 lists `.gitignore` under `framework`; tools/update.py:188 plans `replace` for any framework path whose bytes differ from staging, so operator-added lines (`*.bak`, `.DS_Store`) are dropped with no conflict. `merged` paths go through `git merge-file` 3-way (update.py:190-200).
