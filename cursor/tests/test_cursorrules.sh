#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
F="$ROOT/.cursorrules"
[ -f "$F" ] || { echo "FAIL: missing"; exit 1; }
CHARS=$(wc -c < "$F")
[ "$CHARS" -le 8000 ] || { echo "FAIL: too large — $CHARS chars (max 8000)"; exit 1; }
grep -qi "pre-response learning guard" "$F" || { echo "FAIL: learning guard"; exit 1; }
grep -qi "vault_context(" "$F" || { echo "FAIL: vault_context instruction"; exit 1; }
grep -qi "vault_write" "$F" || { echo "FAIL: vault_write trigger"; exit 1; }
grep -qi "vault_search" "$F" || { echo "FAIL: vault_search guidance"; exit 1; }
grep -qi "vault_read" "$F" || { echo "FAIL: vault_read instruction"; exit 1; }
grep -qi "caveman" "$F" || { echo "FAIL: caveman-concise style"; exit 1; }
grep -qi "keywords" "$F" || { echo "FAIL: keywords instruction for vault_context"; exit 1; }
# Must NOT contain OpenCode-specific references
! grep -qi "opencode" "$F" || { echo "FAIL: OpenCode references must be removed"; exit 1; }
! grep -qi "Bun.file" "$F" || { echo "FAIL: OpenCode references must be removed"; exit 1; }
echo "PASS"
