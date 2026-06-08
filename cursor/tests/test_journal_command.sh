#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
F="$ROOT/commands/journal.md"
[ -f "$F" ] || { echo "FAIL: missing $F"; exit 1; }
grep -qi "vault_write" "$F" || { echo "FAIL: must instruct vault_write"; exit 1; }
grep -qi "daily" "$F" || { echo "FAIL: must reference daily note"; exit 1; }
grep -qi "progress" "$F" || { echo "FAIL: must include Progress section"; exit 1; }
grep -qi "learnings" "$F" || { echo "FAIL: must include Learnings section"; exit 1; }
grep -qi "open" "$F" || { echo "FAIL: must include Open section"; exit 1; }
grep -qi "vault_search" "$F" || { echo "FAIL: must instruct vault_search before write"; exit 1; }
echo "PASS"
