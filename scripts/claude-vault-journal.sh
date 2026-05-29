#!/usr/bin/env bash
# Claude Code SessionEnd hook — appends session-end timestamp to daily note.
#
# Install:
#   1. Copy to ~/.claude/hooks/vault-journal.sh
#   2. chmod +x ~/.claude/hooks/vault-journal.sh
#   3. Set VAULT_PATH in your shell
#   4. Add to .claude/settings.json:
#
#   "hooks": {
#     "SessionEnd": [
#       {
#         "hooks": [
#           {
#             "type": "command",
#             "command": "/full/path/to/vault-journal.sh"
#           }
#         ]
#       }
#     ]
#   }

set -euo pipefail

VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  exit 0
fi

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M)
NOTE="$VAULT_PATH/daily/$TODAY.md"

if [ -f "$NOTE" ]; then
  printf "\n## Session end — %s\n\n" "$NOW" >> "$NOTE"
fi
