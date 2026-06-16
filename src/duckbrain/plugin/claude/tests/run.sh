#!/usr/bin/env bash
set -uo pipefail
DIR="$(dirname "$0")"; fail=0
tmpout=$(mktemp); trap 'rm -f "$tmpout"' EXIT
for t in "$DIR"/test_*.sh; do
  if bash "$t" >"$tmpout" 2>&1; then echo "PASS  $(basename "$t")"; else echo "FAIL  $(basename "$t")"; cat "$tmpout"; fail=1; fi
done
exit $fail
