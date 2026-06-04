#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
M="$ROOT/.claude-plugin/plugin.json"
jq empty "$M" || { echo "FAIL: invalid JSON"; exit 1; }
jq -e '.name == "duckbrain"' "$M" >/dev/null || { echo "FAIL: name"; exit 1; }
jq -e '.userConfig.vault_path.type == "directory"' "$M" >/dev/null || { echo "FAIL: vault_path type"; exit 1; }
jq -e '.userConfig.vault_path.required == true' "$M" >/dev/null || { echo "FAIL: vault_path required"; exit 1; }
echo "PASS"
