#!/usr/bin/env bash
# vault-context.sh — emit Obsidian vault context for Claude Code plugin
set -euo pipefail

source "${CLAUDE_PLUGIN_ROOT}/scripts/lib.sh"

VAULT=$(resolve_vault_path "${CLAUDE_PLUGIN_OPTION_VAULT_PATH:-${VAULT_PATH:-}}")
if [ -z "$VAULT" ]; then
  exit 0
fi

{
  # LEARNINGS.md first — must survive line-boundary truncation
  safe_cat "${CLAUDE_PLUGIN_ROOT}/LEARNINGS.md"

  echo ""
  echo "## Vault topic tags"
  echo ""
  safe_cat "$VAULT/wiki/tags.md"

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
