#!/usr/bin/env bash
# Cursor sessionStart hook — injects DuckBrain vault context.
#
# Cursor hooks communicate via JSON on stdin/stdout.
# Reads vault files and returns additional_context.
#
# Known issue: Cursor's sessionStart additional_context is dropped due to a
# timing bug (confirmed by Cursor devs). This script is a prototype — test
# before relying on it. The most reliable approach for Cursor is
# .cursor/rules/*.mdc with alwaysApply: true.
#
# Install:
#   1. Copy to ~/.cursor/hooks/vault-context.sh
#   2. chmod +x ~/.cursor/hooks/vault-context.sh
#   3. Set VAULT_PATH in your shell
#   4. Add to ~/.cursor/hooks.json:
#
#   {
#     "version": 1,
#     "hooks": {
#       "sessionStart": [
#         { "command": "/full/path/to/vault-context.sh" }
#       ]
#     }
#   }

set -euo pipefail

# Consume stdin (required by Cursor hooks protocol)
read -r INPUT

VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  echo '{"env":{}}'
  exit 0
fi

WIKI="$VAULT_PATH/wiki"
DAILY="$VAULT_PATH/daily"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -j -v-1d +%Y-%m-%d 2>/dev/null || "")

ADDITIONAL_CONTEXT=""

# Vault tags
TAGS_FILE="$WIKI/tags.md"
if [ -f "$TAGS_FILE" ]; then
  ADDITIONAL_CONTEXT+=$'## Vault topic tags\n'
  ADDITIONAL_CONTEXT+=$(cat "$TAGS_FILE")
  ADDITIONAL_CONTEXT+=$'\n\n'
fi

# Recent daily notes
for DATE in "$TODAY" "$YESTERDAY"; do
  NOTE="$DAILY/$DATE.md"
  if [ -f "$NOTE" ]; then
    ADDITIONAL_CONTEXT+="### Daily note: $DATE"$'\n'
    ADDITIONAL_CONTEXT+=$(cat "$NOTE")
    ADDITIONAL_CONTEXT+=$'\n\n'
  fi
done

# Escape for JSON
ESCAPED=$(printf '%s' "$ADDITIONAL_CONTEXT" | \
  sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g' | \
  awk '{printf "%s\\n", $0}' | \
  sed 's/\\n$//')

cat << EOF
{
  "additional_context": "$ESCAPED"
}
EOF
