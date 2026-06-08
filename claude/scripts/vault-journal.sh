#!/usr/bin/env bash
set -euo pipefail
source "${CLAUDE_PLUGIN_ROOT}/scripts/lib.sh"
VAULT=$(resolve_vault_path "${CLAUDE_PLUGIN_OPTION_VAULT_PATH:-${VAULT_PATH:-}}")
[ -z "$VAULT" ] && exit 0
NOTE="$VAULT/daily/$(today).md"
[ -f "$NOTE" ] || exit 0
last_entry=$(grep -v '^[[:space:]]*$' "$NOTE" | tail -1)
[[ "$last_entry" == "## Session end"* ]] && exit 0
printf '\n## Session end — %s\n' "$(date +%H:%M)" >> "$NOTE"
