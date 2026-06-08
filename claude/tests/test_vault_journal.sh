#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$(dirname "$0")/fixtures.sh"
export CLAUDE_PLUGIN_ROOT="$ROOT"

# vault-journal.sh must be a no-op: exits 0, writes nothing to the daily note
V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
NOTE="$V/daily/$(date +%Y-%m-%d).md"

# Pre-populate so we can verify nothing is appended
echo "## existing entry" > "$NOTE"
BEFORE=$(cat "$NOTE")

bash "$ROOT/scripts/vault-journal.sh"

AFTER=$(cat "$NOTE")
[ "$BEFORE" = "$AFTER" ] || { echo "FAIL: vault-journal.sh wrote to daily note (should be no-op)"; cleanup_vault "$V"; exit 1; }
cleanup_vault "$V"

# Missing daily note — must still exit 0
V2=$(make_temp_vault); rm -f "$V2/daily/$(date +%Y-%m-%d).md"; export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V2"
bash "$ROOT/scripts/vault-journal.sh"; [ $? -eq 0 ] || { echo "FAIL: missing-note exit"; cleanup_vault "$V2"; exit 1; }
cleanup_vault "$V2"

echo "PASS"
