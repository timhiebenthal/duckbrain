#!/usr/bin/env bash
# vault-context.sh — emit Obsidian vault context for Claude Code plugin
set -euo pipefail

source "${CLAUDE_PLUGIN_ROOT}/scripts/lib.sh"

VAULT=$(resolve_vault_path "${CLAUDE_PLUGIN_OPTION_VAULT_PATH:-${VAULT_PATH:-}}")
if [ -z "$VAULT" ]; then
  exit 0
fi

{
  # Version drift check — warn if plugin files are older than installed package
  _PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
  if command -v python3 &>/dev/null && [ -f "$_PLUGIN_JSON" ]; then
    _PLUGIN_VER=$(python3 -c "
import json, sys
try:
    print(json.load(open('$_PLUGIN_JSON')).get('version', ''))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    _PKG_VER=$(python3 -c "
import importlib.metadata, sys
try:
    print(importlib.metadata.version('duckbrain'))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    if [ -n "$_PLUGIN_VER" ] && [ -n "$_PKG_VER" ] && [ "$_PLUGIN_VER" != "$_PKG_VER" ]; then
      echo "⚠ duckbrain plugin (v${_PLUGIN_VER}) is out of sync with package (v${_PKG_VER}). Run: duckbrain install-plugin"
      echo ""
    fi
  fi

  # LEARNINGS.md first — must survive line-boundary truncation
  safe_cat "${CLAUDE_PLUGIN_ROOT}/LEARNINGS.md"

  echo ""
  echo "## Vault topic tags"
  echo ""
  safe_cat "$VAULT/wiki/tags.md"

  echo ""
  echo "## User Identity"
  echo ""
  safe_cat "$VAULT/imprint.md"

  echo ""
  TODAY=$(today)
  if [ -f "$VAULT/daily/$TODAY.md" ]; then
    echo "## Today's daily note ($TODAY)"
    echo ""
    safe_cat "$VAULT/daily/$TODAY.md"
  fi

  YDAY=$(yesterday)
  if [ -n "$YDAY" ] && [ -f "$VAULT/daily/$YDAY.md" ]; then
    echo ""
    echo "## Yesterday's daily note ($YDAY)"
    echo ""
    safe_cat "$VAULT/daily/$YDAY.md"
  fi

  echo ""
  echo "### Recent vault writes"
  echo ""
  tail_lines "$VAULT/wiki/log.md" 20

} | truncate_lines 9500 || true
