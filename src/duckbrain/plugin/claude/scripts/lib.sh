#!/usr/bin/env bash
# Shared helpers for duckbrain Claude Code plugin hooks — source this file

resolve_vault_path() {
  local raw="$1"
  if [ -z "$raw" ]; then echo ""; return; fi
  if [[ "$raw" == /* ]]; then echo "$raw"; return; fi
  if [ -z "${WSLPATH_DISABLE:-}" ] && command -v wslpath >/dev/null 2>&1; then
    wslpath "$raw"
    return
  fi
  echo "$raw" \
    | sed 's|\\|/|g' \
    | sed 's|^\([A-Za-z]\):|/mnt/\L\1|'
}

tail_lines() {
  local path="$1" n="$2"
  [ -f "$path" ] && tail -n "$n" "$path" || true
}

safe_cat() {
  local path="$1"
  [ -f "$path" ] && cat "$path" || true
}

truncate_lines() {
  local max="$1"
  local count=0
  while IFS= read -r line; do
    local len=$(( ${#line} + 1 ))
    if (( count + len > max )); then break; fi
    echo "$line"
    (( count += len )) || true
  done
}

today() {
  date +%Y-%m-%d
}

yesterday() {
  date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo ""
}
