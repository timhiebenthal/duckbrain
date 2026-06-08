#!/usr/bin/env bash
set -euo pipefail

# Consume stdin — Cursor's hook runner writes a JSON payload to stdin;
# not reading it can cause the process to hang.
read -r INPUT || true

VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  echo '{}'
  exit 0
fi

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M)
NOTE="$VAULT_PATH/daily/$TODAY.md"

if [ -f "$NOTE" ]; then
  printf "\n\n## Session end — %s\n" "$NOW" >> "$NOTE"
fi

echo '{}'
