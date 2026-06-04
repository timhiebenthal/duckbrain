#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$(dirname "$0")/fixtures.sh"
export CLAUDE_PLUGIN_ROOT="$ROOT"
V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
NOTE="$V/daily/$(date +%Y-%m-%d).md"
bash "$ROOT/scripts/vault-journal.sh"
grep -q "Session end" "$NOTE" || { echo "FAIL: timestamp not appended"; cleanup_vault "$V"; exit 1; }
cleanup_vault "$V"
V2=$(make_temp_vault); rm -f "$V2/daily/$(date +%Y-%m-%d).md"; export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V2"
bash "$ROOT/scripts/vault-journal.sh"; [ $? -eq 0 ] || { echo "FAIL: missing-note exit"; cleanup_vault "$V2"; exit 1; }
cleanup_vault "$V2"
echo "PASS"
