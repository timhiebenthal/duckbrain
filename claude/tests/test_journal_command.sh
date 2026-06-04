#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
J="$ROOT/commands/journal.md"
[ -f "$J" ] || { echo "FAIL: missing"; exit 1; }
grep -qi "vault_write" "$J" || { echo "FAIL: must instruct vault_write"; exit 1; }
grep -qi "daily" "$J" || { echo "FAIL: must reference daily note"; exit 1; }
echo "PASS"
