#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/fixtures.sh"
V=$(make_temp_vault)
[ -f "$V/wiki/tags.md" ] && [ -f "$V/wiki/log.md" ] && [ -f "$V/daily/$(date +%Y-%m-%d).md" ] || { echo "FAIL: missing files"; cleanup_vault "$V"; exit 1; }
[ "$(wc -l < "$V/wiki/log.md")" -ge 25 ] || { echo "FAIL: log too short for tail test"; cleanup_vault "$V"; exit 1; }
cleanup_vault "$V"
[ ! -d "$V" ] || { echo "FAIL: cleanup did not remove dir"; exit 1; }
echo "PASS"
