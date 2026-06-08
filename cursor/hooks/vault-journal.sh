#!/usr/bin/env bash
# Cursor SessionEnd hook — intentionally a no-op.
# Session end markers added noise without signal: with concurrent agent
# sessions a "Session end" line doesn't contextually belong to any prior
# entry and just clutters the daily note.

# Consume stdin — Cursor's hook runner writes a JSON payload to stdin;
# not reading it can cause the process to hang.
read -r INPUT || true

echo '{}'
