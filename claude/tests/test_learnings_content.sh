#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
L="$ROOT/LEARNINGS.md"
[ -f "$L" ] || { echo "FAIL: missing"; exit 1; }
grep -qi "pre-response learning guard" "$L" || { echo "FAIL: guard section"; exit 1; }
grep -qi "vault_write" "$L" || { echo "FAIL: triggers"; exit 1; }
grep -qi "session rituals" "$L" || { echo "FAIL: rituals"; exit 1; }
echo "PASS"
