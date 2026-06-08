#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
F="$ROOT/.cursor/mcp.json"
[ -f "$F" ] || { echo "FAIL: missing $F"; exit 1; }
jq empty "$F" || { echo "FAIL: invalid JSON"; exit 1; }
jq -e '.mcpServers.duckbrain' "$F" >/dev/null || { echo "FAIL: missing duckbrain server"; exit 1; }
# Must use uv run with local repo (not uvx)
jq -e '.mcpServers.duckbrain.command == "uv"' "$F" >/dev/null || { echo "FAIL: command must be uv"; exit 1; }
jq -e '.mcpServers.duckbrain.args | index("run")' "$F" >/dev/null || { echo "FAIL: missing run arg"; exit 1; }
jq -e '.mcpServers.duckbrain.args | index("duckbrain")' "$F" >/dev/null || { echo "FAIL: missing duckbrain arg"; exit 1; }
jq -e '.mcpServers.duckbrain.env.VAULT_PATH // empty' "$F" >/dev/null || { echo "FAIL: VAULT_PATH env missing"; exit 1; }
echo "PASS"
