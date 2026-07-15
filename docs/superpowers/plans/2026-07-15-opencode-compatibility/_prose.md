# OpenCode Compatibility for blog-craft

Three phases:
1. **Project scaffolding** — Create pyproject.toml (uv + PyYAML), opencode.json,
   and the .opencode/ directory skeleton.
2. **Sync script** — Implement scripts/sync-opencode.py that mirrors skills,
   generates commands, syncs instructions. Run once to seed initial mirrors.
3. **Install script** — Implement scripts/install.sh handling Claude Code
   marketplace registration, plugin caching, and OpenCode skill/command delivery.
