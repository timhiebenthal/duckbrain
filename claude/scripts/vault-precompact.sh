#!/usr/bin/env bash
# vault-precompact.sh — emit vault snapshot for Claude Code PreCompact hook
set -euo pipefail

source "${CLAUDE_PLUGIN_ROOT}/scripts/lib.sh"

VAULT=$(resolve_vault_path "${CLAUDE_PLUGIN_OPTION_VAULT_PATH:-}")

NUDGE="Journal checkpoint — vault_write(kind=\"daily\", title=\"$(date +%Y-%m-%d)\", ...) if anything notable this session."

if [ -z "$VAULT" ]; then
  snapshot="$NUDGE"
else
  snapshot=$(
    {
      echo "### Recent vault log (last 15 lines)"
      echo ""
      tail_lines "$VAULT/wiki/log.md" 15

      TODAY=$(today)
      if [ -f "$VAULT/daily/$TODAY.md" ]; then
        echo ""
        echo "### Today's daily note ($TODAY)"
        echo ""
        safe_cat "$VAULT/daily/$TODAY.md"
      fi

      echo ""
      echo "$NUDGE"
    }
  )
fi

jq -n --arg ctx "$snapshot" '{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":$ctx}}'
