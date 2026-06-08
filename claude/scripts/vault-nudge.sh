#!/usr/bin/env bash
set -euo pipefail

# Read session_id from stdin JSON; sanitize to prevent path traversal in marker path
session_id=$(jq -r '.session_id // "default"' | tr -dc '[:alnum:]-_')
session_id="${session_id:-default}"

MARKER="${TMPDIR:-/tmp}/duckbrain-nudge-$session_id"

# Emit nudge if marker missing OR older than 15 minutes
if [ ! -f "$MARKER" ] || [ -n "$(find "$MARKER" -mmin +15 2>/dev/null)" ]; then
  printf 'If this turn produced a learning, a challenge, or a notable result, journal it concisely: vault_write(kind="daily", title="%s", content="## Topic\n\nDetails"). Caveman-concise — cut filler. If nothing noteworthy, skip.\n' "$(date +%Y-%m-%d)"
  touch "$MARKER"
fi

exit 0
