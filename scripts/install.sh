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
# A Claude Code marketplace name is a 1:1 namespace over ONE source repo: its
# manifest (marketplaces/<name>/.claude-plugin/marketplace.json) is a single
# file listing every plugin of that marketplace, and the rsync below is
# `--delete` — replace, never merge. So the name encodes org AND repo, and it
# matches the name our own .claude-plugin/marketplace.json declares.
#
# It used to be the bare org name `derio-net`, which the sibling super-fr repo
# also claimed; both installers rsync'd their own repo root into the same
# directory and evicted each other. The bare name is now RETIRED — no repo owns
# an org-level namespace — and both installers purge it on sight. See super-fr
# PR #392 and docs/superpowers/journals/debug/2026-07-23-marketplace-namespace-collision.md.
MARKETPLACE_NAME="derio-net--blog-craft"
MARKETPLACE_DIR="$CLAUDE_DIR/plugins/marketplaces/$MARKETPLACE_NAME"
CACHE_BASE="$CLAUDE_DIR/plugins/cache/$MARKETPLACE_NAME"
PLUGINS_DIR="$CLAUDE_DIR/plugins"
KNOWN_MARKETPLACES="$PLUGINS_DIR/known_marketplaces.json"
INSTALLED_PLUGINS="$PLUGINS_DIR/installed_plugins.json"
PLUGIN_NAME="blog-craft"
PLUGIN_ID="$PLUGIN_NAME@$MARKETPLACE_NAME"
# Retired namespaces we purge on sight. `derio-net` is the shared one both
# repos fought over; with no owner left, every `*@derio-net` id is dangling by
# definition, so removing the whole key is safe by construction rather than one
# repo reaching into another's install state. `blog-craft` is our own earlier
# bare-repo name from the pre-plugin directory-source install.
LEGACY_MARKETPLACE_NAMES=(derio-net blog-craft)
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
  # Delete only OUR plugin ids and OUR marketplace. This block used to run
  # `del(."derio-net")` on both registries, which deregistered the whole shared
  # marketplace — taking super-fr@derio-net and super-fr-dispatch@derio-net
  # down with it. Uninstalling us must never uninstall a sibling.
  if command -v jq &>/dev/null; then
    if [ -f "$SETTINGS" ]; then
      jq --arg name "$PLUGIN_NAME" \
        '.enabledPlugins |= with_entries(select(.key | startswith($name + "@") | not))
         | .extraKnownMarketplaces |= with_entries(
             select(.key | (. == "blog-craft" or . == "derio-net--blog-craft") | not))' \
        "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
      echo "  Disabled $PLUGIN_NAME in settings.json"
    fi
    if [ -f "$INSTALLED_PLUGINS" ]; then
      jq --arg name "$PLUGIN_NAME" \
        '.plugins |= with_entries(select(.key | startswith($name + "@") | not))' \
        "$INSTALLED_PLUGINS" > "${INSTALLED_PLUGINS}.tmp" && mv "${INSTALLED_PLUGINS}.tmp" "$INSTALLED_PLUGINS"
      echo "  Deregistered $PLUGIN_NAME from installed_plugins.json"
    fi
    if [ -f "$KNOWN_MARKETPLACES" ]; then
      jq 'with_entries(select(.key | (. == "blog-craft" or . == "derio-net--blog-craft") | not))' \
        "$KNOWN_MARKETPLACES" > "${KNOWN_MARKETPLACES}.tmp" && mv "${KNOWN_MARKETPLACES}.tmp" "$KNOWN_MARKETPLACES"
      echo "  Removed our marketplace from known_marketplaces.json"
    fi
  fi
  rm -rf "$MARKETPLACE_DIR" "$CACHE_BASE" \
    "$PLUGINS_DIR/marketplaces/blog-craft" "$PLUGINS_DIR/cache/blog-craft" \
    "$PLUGINS_DIR/cache/derio-net/$PLUGIN_NAME"
  echo "  Removed plugin cache and marketplace directory"
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
# Ask git, don't stat `.git`: in a linked worktree (what `fr isolation up`
# creates, and how this repo is meant to be worked on) `.git` is a FILE, so the
# old `[ ! -d "$PLUGIN_ROOT/.git" ]` rejected every isolated checkout.
if ! git -C "$PLUGIN_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
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
# These writes are UNCONDITIONAL, not skip-if-present. `if ! jq -e '.<key>'`
# reads as idempotence but means first-writer-wins: a stale or wrong
# `source.repo` on our own key survives every reinstall, and a later
# `/plugin marketplace update blog-craft` then re-fetches the wrong source.
# Idempotence for a key we own means converging on our value.
if command -v jq &>/dev/null; then
  MARKETPLACE_SOURCE='{"source":"github","repo":"derio-net/blog-craft"}'

  if [ -f "$SETTINGS" ]; then
    jq --arg name "$MARKETPLACE_NAME" --argjson src "$MARKETPLACE_SOURCE" \
      '.extraKnownMarketplaces[$name] = {"source":$src}' \
      "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
    echo "  Registered $MARKETPLACE_NAME in extraKnownMarketplaces"
  fi

  if [ -f "$KNOWN_MARKETPLACES" ]; then
    jq --arg name "$MARKETPLACE_NAME" --argjson src "$MARKETPLACE_SOURCE" \
      --arg loc "$MARKETPLACE_DIR" \
      '.[$name] = {"source":$src,"installLocation":$loc}' \
      "$KNOWN_MARKETPLACES" > "${KNOWN_MARKETPLACES}.tmp" && mv "${KNOWN_MARKETPLACES}.tmp" "$KNOWN_MARKETPLACES"
    echo "  Registered $MARKETPLACE_NAME in known_marketplaces.json"
  fi

  if [ -f "$SETTINGS" ]; then
    jq --arg id "$PLUGIN_ID" '.enabledPlugins[$id] = true' \
      "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
    echo "  Enabled $PLUGIN_ID in settings.json"
  fi

  # Purge the retired marketplaces. `derio-net` is the shared bare-org name both
  # repos fought over and neither now owns, so every `*@derio-net` id is
  # dangling by definition — removing the whole key is safe by construction, not
  # us reaching into super-fr's install state. (super-fr's own installer does
  # the same, and re-registers itself as `derio-net--super-fr`.) `blog-craft` is
  # our own earlier bare-repo name from the pre-plugin directory-source install.
  purged_ids=""
  for legacy_name in "${LEGACY_MARKETPLACE_NAMES[@]}"; do
    for state_file in "$INSTALLED_PLUGINS" "$SETTINGS"; do
      [ -f "$state_file" ] || continue
      if [ "$state_file" = "$INSTALLED_PLUGINS" ]; then
        key_path='.plugins'
      else
        key_path='.enabledPlugins'
      fi
      while IFS= read -r plugin_id; do
        [ -n "$plugin_id" ] || continue
        case " $purged_ids " in *" $plugin_id "*) ;; *) purged_ids="$purged_ids $plugin_id" ;; esac
      done < <(jq -r "($key_path // {}) | keys[] | select(endswith(\"@$legacy_name\"))" \
                 "$state_file" 2>/dev/null || true)
      jq --arg suffix "@$legacy_name" \
        "$key_path |= with_entries(select(.key | endswith(\$suffix) | not))" \
        "$state_file" > "${state_file}.tmp" && mv "${state_file}.tmp" "$state_file"
    done
    if [ -f "$KNOWN_MARKETPLACES" ]; then
      jq --arg name "$legacy_name" 'del(.[$name])' \
        "$KNOWN_MARKETPLACES" > "${KNOWN_MARKETPLACES}.tmp" && mv "${KNOWN_MARKETPLACES}.tmp" "$KNOWN_MARKETPLACES"
    fi
    if [ -f "$SETTINGS" ]; then
      jq --arg name "$legacy_name" 'del(.extraKnownMarketplaces[$name])' \
        "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
    fi
    rm -rf "$PLUGINS_DIR/marketplaces/$legacy_name" "$PLUGINS_DIR/cache/$legacy_name"
  done
  if [ -n "$purged_ids" ]; then
    echo "  Retired the bare-name marketplaces (registry, cache, directory)"
    for plugin_id in $purged_ids; do
      echo "    - dropped $plugin_id"
    done
    if [ -n "$(echo "$purged_ids" | tr ' ' '\n' | grep -v "^$PLUGIN_NAME@\|^$" || true)" ]; then
      echo "  NOTE: some of those belong to sibling repos. Re-run their installers" >&2
      echo "  to re-register them under their own 'derio-net--<repo>' marketplace." >&2
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
  jq --argjson entry "$INSTALL_ENTRY" --arg id "$PLUGIN_ID" '.plugins[$id] = $entry' \
    "$INSTALLED_PLUGINS" > "${INSTALLED_PLUGINS}.tmp" && mv "${INSTALLED_PLUGINS}.tmp" "$INSTALLED_PLUGINS"
  echo "  Registered $PLUGIN_ID v$CURRENT_VERSION in installed_plugins.json"
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
echo "  jq '.extraKnownMarketplaces[\"$MARKETPLACE_NAME\"]' ~/.claude/settings.json"
echo "  jq '.enabledPlugins[\"$PLUGIN_ID\"]' ~/.claude/settings.json"
echo "  ls ~/.config/opencode/skills/"
echo "  ls ~/.config/opencode/commands/"
