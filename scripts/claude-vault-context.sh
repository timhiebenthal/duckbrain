#!/usr/bin/env bash
# Claude Code SessionStart hook — injects DuckBrain vault context.
#
# Install:
#   1. Copy this script somewhere accessible (e.g. ~/.claude/hooks/)
#   2. chmod +x ~/.claude/hooks/vault-context.sh
#   3. Set VAULT_PATH in your shell or .claude/settings.json env
#   4. Add to .claude/settings.json:
#
#   "hooks": {
#     "SessionStart": [
#       {
#         "matcher": "startup",
#         "hooks": [
#           {
#             "type": "command",
#             "command": "/full/path/to/vault-context.sh"
#           }
#         ]
#       }
#     ]
#   }
#
# Output is injected as additionalContext — invisible to you, visible to Claude.

set -euo pipefail

VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  exit 0  # silent skip if not configured
fi

WIKI="$VAULT_PATH/wiki"
DAILY="$VAULT_PATH/daily"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -j -v-1d +%Y-%m-%d 2>/dev/null || echo "")

# Vault tags
TAGS_FILE="$WIKI/tags.md"
if [ -f "$TAGS_FILE" ]; then
  echo "## Vault topic tags"
  cat "$TAGS_FILE"
  echo ""
fi

# Recent daily notes
for DATE in "$TODAY" "$YESTERDAY"; do
  NOTE="$DAILY/$DATE.md"
  if [ -f "$NOTE" ]; then
    echo "### Daily note: $DATE"
    cat "$NOTE"
    echo ""
  fi
done

# Recent log activity (last 20 lines)
LOG_FILE="$WIKI/log.md"
if [ -f "$LOG_FILE" ]; then
  echo "### Recent vault writes"
  tail -20 "$LOG_FILE"
  echo ""
fi
