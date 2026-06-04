#!/usr/bin/env bash
set -uo pipefail
DIR="$(dirname "$0")"; fail=0
for t in "$DIR"/test_*.sh; do
  if bash "$t" >/tmp/_t.out 2>&1; then echo "PASS  $(basename "$t")"; else echo "FAIL  $(basename "$t")"; cat /tmp/_t.out; fail=1; fi
done
rm -f /tmp/_t.out
exit $fail
