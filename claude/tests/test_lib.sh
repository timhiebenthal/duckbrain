#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/lib.sh"

R=$(resolve_vault_path "/mnt/c/vault")
[ "$R" = "/mnt/c/vault" ] || { echo "FAIL: posix passthrough ($R)"; exit 1; }

R=$(WSLPATH_DISABLE=1 resolve_vault_path 'C:\Users\me\vault')
[ "$R" = "/mnt/c/Users/me/vault" ] || { echo "FAIL: windows fallback ($R)"; exit 1; }

printf 'a\nb\nc\nd\n' > /tmp/_lib_t.$$
[ "$(tail_lines /tmp/_lib_t.$$ 2)" = $'c\nd' ] || { echo "FAIL: tail_lines"; rm -f /tmp/_lib_t.$$; exit 1; }
rm -f /tmp/_lib_t.$$

OUT=$(tail_lines /tmp/_nonexistent_$$ 5 2>&1)
[ -z "$OUT" ] || { echo "FAIL: tail_lines missing file should produce no output ($OUT)"; exit 1; }

OUT=$(printf 'hello\nworld\nbig\n' | truncate_lines 8)
[ "$OUT" = "hello" ] || { echo "FAIL: truncate_lines ($OUT)"; exit 1; }

T=$(today)
echo "$T" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' || { echo "FAIL: today format ($T)"; exit 1; }

echo "PASS"
