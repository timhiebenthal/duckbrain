#!/usr/bin/env bash
# SessionEnd hook — intentionally a no-op.
# Session end markers added noise without signal: with concurrent agent
# sessions a "Session end" line doesn't contextually belong to any prior
# entry and just clutters the daily note.
exit 0
