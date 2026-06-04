#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
C="$ROOT/.mcp.json"
jq empty "$C" || { echo "FAIL: invalid JSON"; exit 1; }
jq -e '.mcpServers.duckbrain.command == "uvx"' "$C" >/dev/null || { echo "FAIL: command"; exit 1; }
jq -e '.mcpServers.duckbrain.args[0] == "duckbrain"' "$C" >/dev/null || { echo "FAIL: args"; exit 1; }
jq -e '.mcpServers.duckbrain | has("env") | not' "$C" >/dev/null || { echo "FAIL: env block should be absent (VAULT_PATH comes from shell)"; exit 1; }
echo "PASS"
