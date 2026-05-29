#!/usr/bin/env bash
# Cursor sessionEnd hook — appends session-end timestamp to daily note.
#
# Install:
#   1. Copy to ~/.cursor/hooks/vault-journal.sh
#   2. chmod +x ~/.cursor/hooks/vault-journal.sh
#   3. Set VAULT_PATH in your shell
#   4. Add to ~/.cursor/hooks.json:
#
#   {
#     "version": 1,
#     "hooks": {
#       "sessionEnd": [
#         { "command": "/full/path/to/vault-journal.sh" }
#       ]
#     }
#   }

set -euo pipefail

# Consume stdin (required by Cursor hooks protocol)
read -r INPUT

VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  echo '{}'
  exit 0
fi

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M)
NOTE="$VAULT_PATH/daily/$TODAY.md"

if [ -f "$NOTE" ]; then
  printf "\n## Session end — %s\n\n" "$NOW" >> "$NOTE"
fi

echo '{}'
