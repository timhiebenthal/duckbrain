#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SID="test-$$-$RANDOM"
MARKER="${TMPDIR:-/tmp}/duckbrain-nudge-$SID"
rm -f "$MARKER"
# First call (no marker) → nudge emitted
OUT1=$(printf '{"session_id":"%s"}' "$SID" | bash "$ROOT/scripts/vault-nudge.sh")
echo "$OUT1" | grep -qi "vault_write" || { echo "FAIL: first call should nudge"; rm -f "$MARKER"; exit 1; }
echo "$OUT1" | grep -q "$(date +%Y-%m-%d)" || { echo "FAIL: dynamic date"; rm -f "$MARKER"; exit 1; }
# Second call within window → suppressed (empty)
OUT2=$(printf '{"session_id":"%s"}' "$SID" | bash "$ROOT/scripts/vault-nudge.sh")
[ -z "$OUT2" ] || { echo "FAIL: second call should be suppressed ($OUT2)"; rm -f "$MARKER"; exit 1; }
# Age the marker past the window → nudge again
touch -t 200001010000 "$MARKER"
OUT3=$(printf '{"session_id":"%s"}' "$SID" | bash "$ROOT/scripts/vault-nudge.sh")
echo "$OUT3" | grep -qi "vault_write" || { echo "FAIL: aged marker should nudge"; rm -f "$MARKER"; exit 1; }
rm -f "$MARKER"
echo "PASS"
