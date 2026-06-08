#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# vault-journal.sh must be a no-op: exits 0, writes nothing to the daily note
V=$(mktemp -d /tmp/cursor-test-XXXXXX)
trap "rm -rf $V" EXIT
mkdir -p "$V/daily"
TODAY=$(date +%Y-%m-%d)
echo "# existing content" > "$V/daily/$TODAY.md"
BEFORE=$(cat "$V/daily/$TODAY.md")

echo '{}' | VAULT_PATH="$V" bash "$ROOT/hooks/vault-journal.sh"

AFTER=$(cat "$V/daily/$TODAY.md")
[ "$BEFORE" = "$AFTER" ] || { echo "FAIL: vault-journal.sh wrote to daily note (should be no-op)"; exit 1; }

# Script exits 0 when VAULT_PATH is unset
echo '{}' | VAULT_PATH="" bash "$ROOT/hooks/vault-journal.sh" >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: unset-vault exit code"; exit 1; }

# Script exits 0 when daily note does not exist
V2=$(mktemp -d /tmp/cursor-test-XXXXXX)
trap "rm -rf $V2" EXIT
mkdir -p "$V2/daily"
echo '{}' | VAULT_PATH="$V2" bash "$ROOT/hooks/vault-journal.sh" >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: missing-note exit code"; exit 1; }
rm -rf "$V2"

echo "PASS"
