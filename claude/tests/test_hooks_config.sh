#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
H="$ROOT/hooks/hooks.json"
jq empty "$H" || { echo "FAIL: invalid JSON"; exit 1; }
for ev in SessionStart UserPromptSubmit PreCompact SessionEnd; do
  jq -e --arg e "$ev" '.hooks[$e] | length > 0' "$H" >/dev/null || { echo "FAIL: missing $ev"; exit 1; }
done
CMDS=$(jq -r '.hooks | to_entries[] | .value[].hooks[].command' "$H")
echo "$CMDS" | grep -q 'CLAUDE_PLUGIN_ROOT' || { echo "FAIL: commands must use \${CLAUDE_PLUGIN_ROOT}"; exit 1; }
COUNT=$(echo "$CMDS" | grep -c 'scripts/')
[ "$COUNT" -eq 4 ] || { echo "FAIL: expected 4 script references, got $COUNT"; exit 1; }
echo "PASS"
