#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$(dirname "$0")/fixtures.sh"
export CLAUDE_PLUGIN_ROOT="$ROOT"
V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
OUT=$(bash "$ROOT/scripts/vault-context.sh")
# LEARNINGS must come BEFORE the tags header (survives truncation)
L_POS=$(echo "$OUT" | grep -n -i "learning guard" | head -1 | cut -d: -f1)
T_POS=$(echo "$OUT" | grep -n -i "vault topic tags" | head -1 | cut -d: -f1)
[ -n "$L_POS" ] && [ -n "$T_POS" ] && [ "$L_POS" -lt "$T_POS" ] || { echo "FAIL: LEARNINGS must precede tags"; cleanup_vault "$V"; exit 1; }
echo "$OUT" | grep -q "$(date +%Y-%m-%d)" || { echo "FAIL: today daily"; cleanup_vault "$V"; exit 1; }
[ "${#OUT}" -le 10000 ] || { echo "FAIL: exceeds 10k cap"; cleanup_vault "$V"; exit 1; }
cleanup_vault "$V"
unset CLAUDE_PLUGIN_OPTION_VAULT_PATH
bash "$ROOT/scripts/vault-context.sh" >/dev/null; [ $? -eq 0 ] || { echo "FAIL: unset exit code"; exit 1; }
echo "PASS"
