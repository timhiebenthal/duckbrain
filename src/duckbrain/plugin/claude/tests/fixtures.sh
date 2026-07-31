#!/usr/bin/env bash
# Shared test fixture helpers — source this, don't run it directly

_yesterday() {
  date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo ""
}

make_temp_vault() {
  local V
  V=$(mktemp -d)
  mkdir -p "$V/wiki" "$V/daily"
  printf '# Tags\n\n#ai #coding #learning #debugging #architecture\n' > "$V/wiki/tags.md"
  for i in $(seq 1 30); do
    printf '## [2026-06-0%d] ingest | Source %d\nBrief entry %d.\nPages created: [[page%d]]\n\n' "$((i % 9 + 1))" "$i" "$i" "$i"
  done > "$V/wiki/log.md"
  printf '## 10:00 — Morning standup\n\nStarted work on feature.\n' > "$V/daily/$(date +%Y-%m-%d).md"
  local YESTERDAY
  YESTERDAY=$(_yesterday)
  if [ -n "$YESTERDAY" ]; then
    printf '## 09:00 — Yesterday session\n\nCompleted previous task.\n' > "$V/daily/$YESTERDAY.md"
  fi
  echo "$V"
}

cleanup_vault() {
  rm -rf "$1"
}
