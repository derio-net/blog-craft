#!/usr/bin/env bash
# Canonical blog-craft installer.
# Handles Claude Code marketplace/plugin registration and OpenCode
# skill/command delivery.
set -euo pipefail

cleanup_tmps() {
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    rm -f "${SETTINGS:-}.tmp" "${KNOWN_MARKETPLACES:-}.tmp" \
          "${INSTALLED_PLUGINS:-}.tmp" 2>/dev/null || true
    echo "install.sh failed (exit $rc). Rerun after fixing." >&2
  fi
  exit "$rc"
}
trap cleanup_tmps EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"
MARKETPLACE_DIR="$CLAUDE_DIR/plugins/marketplaces/derio-net"
CACHE_BASE="$CLAUDE_DIR/plugins/cache/derio-net"
PLUGINS_DIR="$CLAUDE_DIR/plugins"
KNOWN_MARKETPLACES="$PLUGINS_DIR/known_marketplaces.json"
INSTALLED_PLUGINS="$PLUGINS_DIR/installed_plugins.json"
PLUGIN_NAME="blog-craft"
OPENCODE_SKILLS_DIR="$HOME/.config/opencode/skills"
OPENCODE_COMMANDS_DIR="$HOME/.config/opencode/commands"
OPENCODE_INSTRUCTIONS_DIR="$HOME/.config/opencode/instructions"
OPENCODE_PLUGIN_DIR="$HOME/.config/opencode/plugins/blog-craft"

if [[ "${1:-}" == "--uninstall" ]]; then
  echo "Uninstalling blog-craft..."
  if [ -d "$OPENCODE_SKILLS_DIR" ]; then
    for skill_dir in "$PLUGIN_ROOT"/skills/*/; do
      skill="$(basename "$skill_dir")"
      if [ -d "$OPENCODE_SKILLS_DIR/$skill" ]; then
        rm -rf "$OPENCODE_SKILLS_DIR/$skill"
        echo "  Removed $OPENCODE_SKILLS_DIR/$skill"
      fi
    done
  fi
  if [ -d "$OPENCODE_COMMANDS_DIR" ]; then
    for skill_dir in "$PLUGIN_ROOT"/skills/*/; do
      skill="$(basename "$skill_dir")"
      if [ -f "$OPENCODE_COMMANDS_DIR/$skill.md" ]; then
        rm -f "$OPENCODE_COMMANDS_DIR/$skill.md"
        echo "  Removed $OPENCODE_COMMANDS_DIR/$skill.md"
      fi
    done
  fi
  rm -f "$OPENCODE_INSTRUCTIONS_DIR/blog-craft.md"
  echo "  Removed OpenCode instruction"
  if [ -d "$OPENCODE_PLUGIN_DIR" ]; then
    rm -rf "$OPENCODE_PLUGIN_DIR"
    echo "  Removed $OPENCODE_PLUGIN_DIR"
  fi
  if command -v jq &>/dev/null; then
    if [ -f "$SETTINGS" ]; then
      jq 'del(.enabledPlugins["blog-craft@derio-net"])' "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
      echo "  Disabled blog-craft@derio-net in settings.json"
    fi
    if [ -f "$KNOWN_MARKETPLACES" ]; then
      jq 'del(.["derio-net"])' "$KNOWN_MARKETPLACES" > "${KNOWN_MARKETPLACES}.tmp" && mv "${KNOWN_MARKETPLACES}.tmp" "$KNOWN_MARKETPLACES"
      echo "  Removed derio-net from known_marketplaces.json"
    fi
    if [ -f "$SETTINGS" ]; then
      jq 'del(.extraKnownMarketplaces["derio-net"])' "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
      echo "  Removed derio-net from extraKnownMarketplaces"
    fi
  fi
  rm -rf "$CACHE_BASE/$PLUGIN_NAME"
  echo "  Removed plugin cache"
  echo "Done."
  exit 0
fi

for cmd in jq rsync git; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' not found in PATH. Install it first." >&2
    exit 1
  fi
done

echo ""
echo "Preflight: validating source repo at $PLUGIN_ROOT..."
if [ ! -d "$PLUGIN_ROOT/.git" ]; then
  echo "ERROR: $PLUGIN_ROOT is not a git checkout." >&2
  exit 1
fi

CURRENT_BRANCH="$(git -C "$PLUGIN_ROOT" symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "  WARNING: on branch '$CURRENT_BRANCH', expected 'main'." >&2
fi
echo "  OK"

echo ""
echo "Installing blog-craft..."

echo ""
echo "Registering marketplace..."
if command -v jq &>/dev/null; then
  if [ -f "$SETTINGS" ]; then
    if ! jq -e '.extraKnownMarketplaces["derio-net"]' "$SETTINGS" &>/dev/null; then
      jq '.extraKnownMarketplaces["derio-net"] = {"source":{"source":"github","repo":"derio-net/blog-craft"}}' \
        "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
      echo "  Added derio-net to extraKnownMarketplaces"
    else
      echo "  derio-net already in extraKnownMarketplaces"
    fi
  fi

  if [ -f "$KNOWN_MARKETPLACES" ]; then
    if ! jq -e '.["derio-net"]' "$KNOWN_MARKETPLACES" &>/dev/null; then
      jq '."derio-net" = {"source":{"source":"github","repo":"derio-net/blog-craft"},"installLocation":"'"$MARKETPLACE_DIR"'"}' \
        "$KNOWN_MARKETPLACES" > "${KNOWN_MARKETPLACES}.tmp" && mv "${KNOWN_MARKETPLACES}.tmp" "$KNOWN_MARKETPLACES"
      echo "  Added derio-net to known_marketplaces.json"
    else
      echo "  derio-net already in known_marketplaces.json"
    fi
  fi

  if [ -f "$SETTINGS" ]; then
    if ! jq -e '.enabledPlugins["blog-craft@derio-net"]' "$SETTINGS" &>/dev/null; then
      jq '.enabledPlugins["blog-craft@derio-net"] = true' \
        "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
      echo "  Enabled blog-craft@derio-net in settings.json"
    else
      echo "  blog-craft@derio-net already enabled"
    fi
  fi
else
  echo "  WARNING: jq not found — cannot register marketplace" >&2
fi

echo ""
echo "Setting up marketplace directory..."
mkdir -p "$MARKETPLACE_DIR"
if [ -L "$MARKETPLACE_DIR" ]; then
  rm "$MARKETPLACE_DIR"
  mkdir -p "$MARKETPLACE_DIR"
  echo "  Replaced stale symlink"
fi
rsync -a --delete --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
  "$PLUGIN_ROOT/" "$MARKETPLACE_DIR/"
echo "  Copied plugin to $MARKETPLACE_DIR"

echo ""
echo "Registering plugin..."
if command -v jq &>/dev/null && [ -f "$INSTALLED_PLUGINS" ]; then
  CURRENT_VERSION=$(jq -r '.version' "$PLUGIN_ROOT/.claude-plugin/plugin.json" 2>/dev/null || echo "unknown")
  PLUGIN_CACHE="$CACHE_BASE/$PLUGIN_NAME"
  CACHE_VERSION_DIR="$PLUGIN_CACHE/$CURRENT_VERSION"
  CACHE_CURRENT_LINK="$PLUGIN_CACHE/current"
  mkdir -p "$CACHE_VERSION_DIR"
  rsync -a --delete --exclude='__pycache__' \
    "$PLUGIN_ROOT/" "$CACHE_VERSION_DIR/"
  echo "  Synced $PLUGIN_NAME v$CURRENT_VERSION to cache"

  ln -sfn "$CURRENT_VERSION" "$CACHE_CURRENT_LINK"
  echo "  Pointed $PLUGIN_NAME/current -> $CURRENT_VERSION"

  INSTALL_ENTRY='[{"scope":"user","installPath":"'"$CACHE_CURRENT_LINK"'","version":"'"$CURRENT_VERSION"'","installedAt":"'"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"'","lastUpdated":"'"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"'"}]'
  jq --argjson entry "$INSTALL_ENTRY" ".plugins[\"$PLUGIN_NAME@derio-net\"] = \$entry" \
    "$INSTALLED_PLUGINS" > "${INSTALLED_PLUGINS}.tmp" && mv "${INSTALLED_PLUGINS}.tmp" "$INSTALLED_PLUGINS"
  echo "  Registered $PLUGIN_NAME@derio-net v$CURRENT_VERSION in installed_plugins.json"
else
  echo "  WARNING: cannot register plugin — jq or installed_plugins.json missing" >&2
fi

echo ""
echo "Installing OpenCode skills and commands..."
if command -v uv &>/dev/null; then
  uv run "$PLUGIN_ROOT/scripts/sync-opencode.py" 2>&1 | sed 's/^/  /'
else
  echo "  WARNING: uv not found — cannot refresh .opencode/ mirrors" >&2
fi

if [ -d "$OPENCODE_SKILLS_DIR" ] || mkdir -p "$OPENCODE_SKILLS_DIR" 2>/dev/null; then
  mkdir -p "$OPENCODE_SKILLS_DIR"
  for skill_dir in "$PLUGIN_ROOT"/skills/*/; do
    skill="$(basename "$skill_dir")"
    mkdir -p "$OPENCODE_SKILLS_DIR/$skill"
    cp "$skill_dir/SKILL.md" "$OPENCODE_SKILLS_DIR/$skill/SKILL.md"
    echo "  Installed $OPENCODE_SKILLS_DIR/$skill/SKILL.md"
  done
else
  echo "  WARNING: cannot install OpenCode skills — $OPENCODE_SKILLS_DIR not writable" >&2
fi

if [ -d "$OPENCODE_COMMANDS_DIR" ] || mkdir -p "$OPENCODE_COMMANDS_DIR" 2>/dev/null; then
  mkdir -p "$OPENCODE_COMMANDS_DIR"
  for skill_dir in "$PLUGIN_ROOT"/skills/*/; do
    skill="$(basename "$skill_dir")"
    if [ -f "$PLUGIN_ROOT/.opencode/commands/$skill.md" ]; then
      cp "$PLUGIN_ROOT/.opencode/commands/$skill.md" "$OPENCODE_COMMANDS_DIR/$skill.md"
      echo "  Installed $OPENCODE_COMMANDS_DIR/$skill.md"
    fi
  done
else
  echo "  WARNING: cannot install OpenCode commands — $OPENCODE_COMMANDS_DIR not writable" >&2
fi

echo ""
echo "Installing blog-craft plugin directory (tools, agents, templates)..."
mkdir -p "$OPENCODE_PLUGIN_DIR"
rsync -a --delete --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='node_modules' \
  "$PLUGIN_ROOT/" "$OPENCODE_PLUGIN_DIR/"
echo "  Installed plugin root at $OPENCODE_PLUGIN_DIR"

echo ""
echo "Installing OpenCode global instruction..."
mkdir -p "$OPENCODE_INSTRUCTIONS_DIR"
cat > "$OPENCODE_INSTRUCTIONS_DIR/blog-craft.md" << INSTR
# blog-craft plugin root

The blog-craft plugin is installed at \`$OPENCODE_PLUGIN_DIR\`.
When a skill references \`<plugin_root>\`, resolve it to this absolute path.
This is where \`tools/\`, \`agents/\`, \`templates/\`, \`migrations/\`, \`docs/\`,
and \`skills/\` reside.
INSTR
echo "  Installed $OPENCODE_INSTRUCTIONS_DIR/blog-craft.md"

echo ""
echo "Installation complete. Restart Claude Code to pick up plugin changes."
echo ""
echo "Verify with:"
echo "  jq '.extraKnownMarketplaces[\"derio-net\"]' ~/.claude/settings.json"
echo "  jq '.enabledPlugins[\"blog-craft@derio-net\"]' ~/.claude/settings.json"
echo "  ls ~/.config/opencode/skills/"
echo "  ls ~/.config/opencode/commands/"
