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

<!-- fr:journal kind=ruled-out scope=debug id=04e399808849 created=2026-10-10T19:00:06+00:00 -->
### 04e399808849 · ruled-out · Plain ruamel round-trip is not enough for #73

ruamel rt preserves comments and key order, but on the frank fixture it still re-indented (load_yaml_guess_indent guessed 4, frank uses 2), normalised flow-collection whitespace (`{ a: 1 }` -> `{a: 1}`), joined a multi-line flow map, and dropped column alignment — on blocks the migration never touched. Tests passed only because the V6 fixture had no flow style and the frank test checked full-line comments. Next: keep ruamel for rendering, but splice the ORIGINAL text for every key whose value the migration left unchanged (recursing into changed block mappings), so only migrated keys are re-rendered; tighten the frank test to an exact removed-lines set.

<!-- fr:journal kind=finding scope=debug id=0b821d29c1ce created=2026-10-10T19:12:15+00:00 state=fixed -->
### 0b821d29c1ce · finding [fixed] · Fixed #73 and #83

#73: tools/migrate_config.py renders with ruamel.yaml and splices original lines back for every unchanged key (recursing into changed block mappings; new keys drop the trailing comment ruamel relocates onto them). #83: templates/manifest.yaml moves `.gitignore` framework -> merged. Pinned by tests/unit/test_operator_content_preserved.py (red at fceacd7): frank fixture v2->v7 removes exactly the two migrated lines, adds no comment/blank lines; .gitignore operator rules survive a 3-way merge, a clash is a conflict leaving the file untouched; missing ruamel writes nothing.

<!-- fr:journal kind=review scope=debug id=e26ea8a59802 created=2026-10-10T19:13:01+00:00 -->
### e26ea8a59802 · review · Self-review of the fix: three findings, all fixed

1) Plain ruamel round-trip still reformatted untouched blocks on frank (indent guess, flow padding, alignment) — fixed by key-level splicing; test tightened to an exact removed-lines set. 2) ruamel relocates a mapping trailing comment onto an appended key, duplicating it — fixed (new keys drop trailing comment/blank lines); test asserts no added comment/blank lines. 3) A trailing `|+` block scalar would have its content blank lines moved by tail relocation — fixed with a parse-parity guard falling back to the whole ruamel render; red/green verified. Also: a missing ruamel now refuses before writing .bak or config. No out-of-scope findings.
