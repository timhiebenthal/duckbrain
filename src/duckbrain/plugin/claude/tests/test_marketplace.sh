#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MP="$ROOT/.claude-plugin/marketplace.json"
jq empty "$MP" || { echo "FAIL: invalid JSON"; exit 1; }
jq -e '.name' "$MP" >/dev/null || { echo "FAIL: marketplace name"; exit 1; }
jq -e '[.plugins[].name] | index("duckbrain")' "$MP" >/dev/null || { echo "FAIL: duckbrain not listed"; exit 1; }
echo "PASS"
