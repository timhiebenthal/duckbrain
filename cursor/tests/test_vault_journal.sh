#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Create temp vault
V=$(mktemp -d /tmp/cursor-test-XXXXXX)
trap "rm -rf $V" EXIT
mkdir -p "$V/daily"
TODAY=$(date +%Y-%m-%d)
echo "# existing content" > "$V/daily/$TODAY.md"

# Run the hook — pipe dummy JSON input to satisfy Cursor's hook protocol (stdin consumption)
echo '{}' | VAULT_PATH="$V" bash "$ROOT/hooks/vault-journal.sh"

# Check timestamp was appended
grep -q "Session end" "$V/daily/$TODAY.md" || { echo "FAIL: timestamp not appended"; exit 1; }

# Check time format (HH:MM)
grep -qE "Session end — [0-9][0-9]:[0-9][0-9]" "$V/daily/$TODAY.md" || { echo "FAIL: bad time format"; exit 1; }

# Check script exits 0 when VAULT_PATH is unset
echo '{}' | VAULT_PATH="" bash "$ROOT/hooks/vault-journal.sh" >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: unset-vault exit code"; exit 1; }

# Check script exits 0 when daily note does not exist
V2=$(mktemp -d /tmp/cursor-test-XXXXXX)
trap "rm -rf $V2" EXIT
mkdir -p "$V2/daily"
echo '{}' | VAULT_PATH="$V2" bash "$ROOT/hooks/vault-journal.sh" >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: missing-note exit code"; exit 1; }
rm -rf "$V2"

echo "PASS"
