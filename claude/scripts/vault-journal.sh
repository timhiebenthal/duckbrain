#!/usr/bin/env bash
set -euo pipefail
source "${CLAUDE_PLUGIN_ROOT}/scripts/lib.sh"
VAULT=$(resolve_vault_path "${CLAUDE_PLUGIN_OPTION_VAULT_PATH:-}")
[ -z "$VAULT" ] && exit 0
NOTE="$VAULT/daily/$(today).md"
[ -f "$NOTE" ] || exit 0
printf '\n## Session end — %s\n' "$(date +%H:%M)" >> "$NOTE"
