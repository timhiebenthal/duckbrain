#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$(dirname "$0")/fixtures.sh"
export CLAUDE_PLUGIN_ROOT="$ROOT"
V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
OUT=$(bash "$ROOT/scripts/vault-precompact.sh")
echo "$OUT" | jq empty || { echo "FAIL: not valid JSON"; cleanup_vault "$V"; exit 1; }
echo "$OUT" | jq -e '.hookSpecificOutput.hookEventName == "PreCompact"' >/dev/null || { echo "FAIL: hookEventName"; cleanup_vault "$V"; exit 1; }
echo "$OUT" | jq -e '.hookSpecificOutput.additionalContext | contains("vault_write")' >/dev/null || { echo "FAIL: journal nudge"; cleanup_vault "$V"; exit 1; }
echo "$OUT" | jq -e --arg d "$(date +%Y-%m-%d)" '.hookSpecificOutput.additionalContext | contains($d)' >/dev/null || { echo "FAIL: today reference"; cleanup_vault "$V"; exit 1; }
cleanup_vault "$V"
unset CLAUDE_PLUGIN_OPTION_VAULT_PATH
bash "$ROOT/scripts/vault-precompact.sh" | jq empty || { echo "FAIL: unset still valid JSON"; exit 1; }
echo "PASS"
