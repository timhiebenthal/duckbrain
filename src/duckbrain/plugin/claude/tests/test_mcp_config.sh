#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
C="$ROOT/.mcp.json"
jq empty "$C" || { echo "FAIL: invalid JSON"; exit 1; }
jq -e '.mcpServers.duckbrain.command == "uvx"' "$C" >/dev/null || { echo "FAIL: command"; exit 1; }
jq -e '.mcpServers.duckbrain.args[0] == "duckbrain"' "$C" >/dev/null || { echo "FAIL: args"; exit 1; }
jq -e '.mcpServers.duckbrain.env.VAULT_PATH == "${user_config.vault_path}"' "$C" >/dev/null || { echo "FAIL: VAULT_PATH substitution"; exit 1; }
echo "PASS"
