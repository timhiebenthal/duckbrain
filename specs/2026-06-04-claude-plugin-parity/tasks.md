# Claude Code Plugin Parity — Implementation Tasks

## Overview

Build a self-contained Claude Code plugin (`claude/`) that gives Claude automatic Obsidian vault awareness — parity with the OpenCode session plugin. The plugin bundles four hooks (SessionStart, UserPromptSubmit, PreCompact, SessionEnd), a marketplace manifest for installable distribution, the duckbrain MCP server config, a `/journal` slash command, and a `userConfig`-prompted vault path. Tests are plain bash + `jq`.

## Testing Approach

Deliverables are shell scripts and JSON config, not Python — the repo's pytest/ruff/mypy gates do not apply. Tests are **plain bash** under `claude/tests/`, using `jq` for JSON assertions (no new Node/Python deps). Each test creates a throwaway temp vault via a shared `fixtures.sh`, runs the target script, and asserts on stdout / file state.

**These are config/shape + behavior unit tests, not integration tests.** They cannot prove the plugin wires into Claude Code end-to-end. The mechanics that depend on Claude Code's runtime (userConfig env delivery, install/marketplace flow, context actually reaching the model) are covered only by the **manual smoke test** in Sprint 3 Stream E, which is a hard gate — not an afterthought.

TDD sequence per script: write failing bash test → run to confirm failure → implement → run to confirm pass → `chmod +x` → commit.

---

## Tasks

## SPRINT 1: Plugin scaffold, static config & shared helpers

Foundation everything builds on. Highest schema risk (manifest, marketplace, hook config) handled first. All streams touch distinct files and run in parallel.

### Stream A: claude/.claude-plugin/plugin.json
- [ ] **Write failing test** `claude/tests/test_plugin_manifest.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  M="$ROOT/.claude-plugin/plugin.json"
  jq empty "$M" || { echo "FAIL: invalid JSON"; exit 1; }
  jq -e '.name == "duckbrain"' "$M" >/dev/null || { echo "FAIL: name"; exit 1; }
  jq -e '.userConfig.vault_path.type == "directory"' "$M" >/dev/null || { echo "FAIL: vault_path type"; exit 1; }
  jq -e '.userConfig.vault_path.required == true' "$M" >/dev/null || { echo "FAIL: vault_path required"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_plugin_manifest.sh` → expect FAIL (file missing)
- [ ] **Write** `claude/.claude-plugin/plugin.json` with `name`, `displayName`, `description`, `userConfig.vault_path` (`type: directory`, `title`, `description`, `required: true`)
- [ ] **Run to verify pass**: `bash claude/tests/test_plugin_manifest.sh` → expect PASS
- [ ] **Commit**

### Stream B: claude/.claude-plugin/marketplace.json
- [ ] **Confirm schema first**: run `claude plugin marketplace add --help` and `claude plugin marketplace --help`; note the exact required fields for a local-directory marketplace before writing the manifest
- [ ] **Write failing test** `claude/tests/test_marketplace.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  MP="$ROOT/.claude-plugin/marketplace.json"
  jq empty "$MP" || { echo "FAIL: invalid JSON"; exit 1; }
  jq -e '.name' "$MP" >/dev/null || { echo "FAIL: marketplace name"; exit 1; }
  jq -e '[.plugins[].name] | index("duckbrain")' "$MP" >/dev/null || { echo "FAIL: duckbrain not listed"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_marketplace.sh` → expect FAIL
- [ ] **Write** `claude/.claude-plugin/marketplace.json` per the confirmed schema, listing the duckbrain plugin with a relative `source`
- [ ] **Run to verify pass**: `bash claude/tests/test_marketplace.sh` → expect PASS
- [ ] **Commit**

### Stream C: claude/.mcp.json
- [ ] **Write failing test** `claude/tests/test_mcp_config.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  C="$ROOT/.mcp.json"
  jq empty "$C" || { echo "FAIL: invalid JSON"; exit 1; }
  jq -e '.mcpServers.duckbrain.command == "duckbrain"' "$C" >/dev/null || { echo "FAIL: command"; exit 1; }
  jq -e '.mcpServers.duckbrain.env.VAULT_PATH == "${user_config.vault_path}"' "$C" >/dev/null || { echo "FAIL: VAULT_PATH substitution"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_mcp_config.sh` → expect FAIL
- [ ] **Write** `claude/.mcp.json` (`command: "duckbrain"`, `env.VAULT_PATH` = `${user_config.vault_path}`)
- [ ] **Run to verify pass**: `bash claude/tests/test_mcp_config.sh` → expect PASS
- [ ] **Commit**

### Stream D: claude/hooks/hooks.json
- [ ] **Write failing test** `claude/tests/test_hooks_config.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  H="$ROOT/hooks/hooks.json"
  jq empty "$H" || { echo "FAIL: invalid JSON"; exit 1; }
  for ev in SessionStart UserPromptSubmit PreCompact SessionEnd; do
    jq -e --arg e "$ev" '.hooks[$e] | length > 0' "$H" >/dev/null || { echo "FAIL: missing $ev"; exit 1; }
  done
  CMDS=$(jq -r '.hooks | to_entries[] | .value[].hooks[].command' "$H")
  echo "$CMDS" | grep -q 'CLAUDE_PLUGIN_ROOT' || { echo "FAIL: commands must use \${CLAUDE_PLUGIN_ROOT}"; exit 1; }
  echo "$CMDS" | grep -c 'scripts/' | grep -q '^4$' || { echo "FAIL: expected 4 script references"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_hooks_config.sh` → expect FAIL
- [ ] **Write** `claude/hooks/hooks.json` registering SessionStart, UserPromptSubmit, PreCompact, SessionEnd; each command quoted as `"${CLAUDE_PLUGIN_ROOT}"/scripts/<name>.sh`
- [ ] **Run to verify pass**: `bash claude/tests/test_hooks_config.sh` → expect PASS
- [ ] **Commit**

### Stream E: claude/LEARNINGS.md
- [ ] **Write failing test** `claude/tests/test_learnings_content.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  L="$ROOT/LEARNINGS.md"
  [ -f "$L" ] || { echo "FAIL: missing"; exit 1; }
  grep -qi "pre-response learning guard" "$L" || { echo "FAIL: guard section"; exit 1; }
  grep -qi "vault_write" "$L" || { echo "FAIL: triggers"; exit 1; }
  grep -qi "session rituals" "$L" || { echo "FAIL: rituals"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_learnings_content.sh` → expect FAIL
- [ ] **Write** `claude/LEARNINGS.md` — adapt `opencode/LEARNINGS.md` to Claude Code language (hook-based rituals, `vault_write` triggers, caveman-concise daily-note format). Keep the pre-response guard, trigger table, and session rituals; drop OpenCode-plugin-specific references
- [ ] **Run to verify pass**: `bash claude/tests/test_learnings_content.sh` → expect PASS
- [ ] **Commit**

### Stream F: claude/tests/fixtures.sh
- [ ] **Write** `claude/tests/fixtures.sh` — shared helper (sourced, not run). Provides:
  - `make_temp_vault()` — `mktemp -d`; creates `wiki/tags.md` (sample `#tag`), `wiki/log.md` (25+ lines to exercise tail), `daily/<today>.md`, `daily/<yesterday>.md` (using GNU/BSD date fallback); echoes the path
  - `cleanup_vault(path)` — `rm -rf`
- [ ] **Write self-test** `claude/tests/test_fixtures.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  source "$(dirname "$0")/fixtures.sh"
  V=$(make_temp_vault)
  [ -f "$V/wiki/tags.md" ] && [ -f "$V/wiki/log.md" ] && [ -f "$V/daily/$(date +%Y-%m-%d).md" ] || { echo "FAIL: missing files"; cleanup_vault "$V"; exit 1; }
  [ "$(wc -l < "$V/wiki/log.md")" -ge 25 ] || { echo "FAIL: log too short"; cleanup_vault "$V"; exit 1; }
  cleanup_vault "$V"
  [ ! -d "$V" ] || { echo "FAIL: cleanup"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify pass**: `bash claude/tests/test_fixtures.sh` → expect PASS
- [ ] **Commit**

### Stream G: claude/scripts/lib.sh
- [ ] **Write failing test** `claude/tests/test_lib.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  source "$ROOT/scripts/lib.sh"
  R=$(resolve_vault_path "/mnt/c/vault"); [ "$R" = "/mnt/c/vault" ] || { echo "FAIL: posix passthrough ($R)"; exit 1; }
  R=$(WSLPATH_DISABLE=1 resolve_vault_path 'C:\Users\me\vault')
  [ "$R" = "/mnt/c/Users/me/vault" ] || { echo "FAIL: windows fallback ($R)"; exit 1; }
  printf 'a\nb\nc\nd\n' > /tmp/_lib_t.$$; [ "$(tail_lines /tmp/_lib_t.$$ 2)" = $'c\nd' ] || { echo "FAIL: tail_lines"; rm -f /tmp/_lib_t.$$; exit 1; }
  rm -f /tmp/_lib_t.$$
  # truncate_lines keeps whole lines and respects the byte budget
  OUT=$(printf 'hello\nworld\nbig\n' | truncate_lines 8)
  [ "$OUT" = "hello" ] || { echo "FAIL: truncate_lines ($OUT)"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_lib.sh` → expect FAIL
- [ ] **Write** `claude/scripts/lib.sh` (sourced) with:
  - `resolve_vault_path(raw)` — `wslpath` when available and `WSLPATH_DISABLE` unset; else sed fallback (backslashes→`/`, `C:`→`/mnt/c`, lowercase drive)
  - `safe_cat(path)` / `tail_lines(path, n)` — no-op when file absent
  - `today()` / `yesterday()` — GNU (`date -d`) and BSD (`date -v`) fallbacks
  - `truncate_lines(max_chars)` — read stdin, emit whole lines until the byte budget would be exceeded; never split a line or a multibyte glyph
- [ ] **Run to verify pass**: `bash claude/tests/test_lib.sh` → expect PASS
- [ ] **Commit**

---

## SPRINT 2: Hook scripts

⚠️ **Depends on: SPRINT 1 — Stream G (`lib.sh`), Stream F (`fixtures.sh`).** Stream A additionally depends on Stream E (`LEARNINGS.md`).

Each stream is one script developed test-first, ending with `chmod +x`. Four independent files, fully parallel.

### Stream A: claude/scripts/vault-context.sh  ⚠️ Depends on SPRINT 1 — Streams E, F, G
- [ ] **Write failing test** `claude/tests/test_vault_context.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  source "$(dirname "$0")/fixtures.sh"
  export CLAUDE_PLUGIN_ROOT="$ROOT"
  V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
  OUT=$(bash "$ROOT/scripts/vault-context.sh")
  # LEARNINGS must come BEFORE the tags header (survives truncation)
  L_POS=$(echo "$OUT" | grep -n -i "learning guard" | head -1 | cut -d: -f1)
  T_POS=$(echo "$OUT" | grep -n -i "vault topic tags" | head -1 | cut -d: -f1)
  [ -n "$L_POS" ] && [ -n "$T_POS" ] && [ "$L_POS" -lt "$T_POS" ] || { echo "FAIL: LEARNINGS must precede tags"; cleanup_vault "$V"; exit 1; }
  echo "$OUT" | grep -q "$(date +%Y-%m-%d)" || { echo "FAIL: today daily"; cleanup_vault "$V"; exit 1; }
  [ "${#OUT}" -le 10000 ] || { echo "FAIL: exceeds 10k cap"; cleanup_vault "$V"; exit 1; }
  cleanup_vault "$V"
  unset CLAUDE_PLUGIN_OPTION_VAULT_PATH
  bash "$ROOT/scripts/vault-context.sh" >/dev/null; [ $? -eq 0 ] || { echo "FAIL: unset exit code"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_vault_context.sh` → expect FAIL
- [ ] **Write** `claude/scripts/vault-context.sh`: source `lib.sh`; resolve `CLAUDE_PLUGIN_OPTION_VAULT_PATH` (exit 0 if empty); emit `LEARNINGS.md` from `$CLAUDE_PLUGIN_ROOT` **first**; then `## Vault topic tags` + `wiki/tags.md`; then today's & yesterday's daily notes; then `### Recent vault writes` + last 20 log lines; pipe full output through `truncate_lines 9500`. Plain stdout
- [ ] **Run to verify pass**: `bash claude/tests/test_vault_context.sh` → expect PASS
- [ ] **chmod +x** `claude/scripts/vault-context.sh`
- [ ] **Commit**

### Stream B: claude/scripts/vault-nudge.sh  ⚠️ Depends on SPRINT 1 — Stream F
- [ ] **Write failing test** `claude/tests/test_vault_nudge.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  SID="test-$$-$RANDOM"
  MARKER="${TMPDIR:-/tmp}/duckbrain-nudge-$SID"
  rm -f "$MARKER"
  # First call (no marker) → nudge emitted
  OUT1=$(printf '{"session_id":"%s"}' "$SID" | bash "$ROOT/scripts/vault-nudge.sh")
  echo "$OUT1" | grep -qi "vault_write" || { echo "FAIL: first call should nudge"; rm -f "$MARKER"; exit 1; }
  echo "$OUT1" | grep -q "$(date +%Y-%m-%d)" || { echo "FAIL: dynamic date"; rm -f "$MARKER"; exit 1; }
  # Second call within window → suppressed (empty)
  OUT2=$(printf '{"session_id":"%s"}' "$SID" | bash "$ROOT/scripts/vault-nudge.sh")
  [ -z "$OUT2" ] || { echo "FAIL: second call should be suppressed ($OUT2)"; rm -f "$MARKER"; exit 1; }
  # Age the marker past the window → nudge again
  touch -t 200001010000 "$MARKER"
  OUT3=$(printf '{"session_id":"%s"}' "$SID" | bash "$ROOT/scripts/vault-nudge.sh")
  echo "$OUT3" | grep -qi "vault_write" || { echo "FAIL: aged marker should nudge"; rm -f "$MARKER"; exit 1; }
  rm -f "$MARKER"
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_vault_nudge.sh` → expect FAIL
- [ ] **Write** `claude/scripts/vault-nudge.sh`: read `session_id` via `jq -r '.session_id // "default"'` from stdin; `MARKER="${TMPDIR:-/tmp}/duckbrain-nudge-$session_id"`; if `[ ! -f "$MARKER" ]` or `find "$MARKER" -mmin +15` is non-empty, print the concise nudge (with `$(date +%Y-%m-%d)`) to stdout and `touch "$MARKER"`; else print nothing. Exit 0 always. Plain stdout
- [ ] **Run to verify pass**: `bash claude/tests/test_vault_nudge.sh` → expect PASS
- [ ] **chmod +x** `claude/scripts/vault-nudge.sh`
- [ ] **Commit**

### Stream C: claude/scripts/vault-precompact.sh  ⚠️ Depends on SPRINT 1 — Streams F, G
- [ ] **Write failing test** `claude/tests/test_vault_precompact.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  source "$(dirname "$0")/fixtures.sh"
  export CLAUDE_PLUGIN_ROOT="$ROOT"
  V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
  OUT=$(bash "$ROOT/scripts/vault-precompact.sh")
  echo "$OUT" | jq empty || { echo "FAIL: not valid JSON"; cleanup_vault "$V"; exit 1; }
  echo "$OUT" | jq -e '.hookSpecificOutput.hookEventName == "PreCompact"' >/dev/null || { echo "FAIL: hookEventName"; cleanup_vault "$V"; exit 1; }
  echo "$OUT" | jq -e '.hookSpecificOutput.additionalContext | contains("vault_write")' >/dev/null || { echo "FAIL: journal nudge"; cleanup_vault "$V"; exit 1; }
  echo "$OUT" | jq -e --arg d "$(date +%Y-%m-%d)" '.hookSpecificOutput.additionalContext | contains($d)' >/dev/null || { echo "FAIL: today reference"; cleanup_vault "$V"; exit 1; }
  cleanup_vault "$V"
  unset CLAUDE_PLUGIN_OPTION_VAULT_PATH
  bash "$ROOT/scripts/vault-precompact.sh" | jq empty || { echo "FAIL: unset still valid JSON"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_vault_precompact.sh` → expect FAIL
- [ ] **Write** `claude/scripts/vault-precompact.sh`: source `lib.sh`; build snapshot (last 15 log lines + today's daily + journal-checkpoint nudge with dynamic date); emit `{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"…"}}` via `jq -n --arg`. When vault path unset, emit valid JSON with just the nudge
- [ ] **Run to verify pass**: `bash claude/tests/test_vault_precompact.sh` → expect PASS
- [ ] **chmod +x** `claude/scripts/vault-precompact.sh`
- [ ] **Commit**

### Stream D: claude/scripts/vault-journal.sh  ⚠️ Depends on SPRINT 1 — Streams F, G
- [ ] **Write failing test** `claude/tests/test_vault_journal.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  source "$(dirname "$0")/fixtures.sh"
  export CLAUDE_PLUGIN_ROOT="$ROOT"
  V=$(make_temp_vault); export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V"
  NOTE="$V/daily/$(date +%Y-%m-%d).md"
  bash "$ROOT/scripts/vault-journal.sh"
  grep -q "Session end" "$NOTE" || { echo "FAIL: timestamp not appended"; cleanup_vault "$V"; exit 1; }
  cleanup_vault "$V"
  V2=$(make_temp_vault); rm -f "$V2/daily/$(date +%Y-%m-%d).md"; export CLAUDE_PLUGIN_OPTION_VAULT_PATH="$V2"
  bash "$ROOT/scripts/vault-journal.sh"; [ $? -eq 0 ] || { echo "FAIL: missing-note exit"; cleanup_vault "$V2"; exit 1; }
  cleanup_vault "$V2"
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_vault_journal.sh` → expect FAIL
- [ ] **Write** `claude/scripts/vault-journal.sh`: source `lib.sh`; resolve vault path (exit 0 if empty); if today's daily note exists, append `\n## Session end — $(date +%H:%M)\n`; else no-op
- [ ] **Run to verify pass**: `bash claude/tests/test_vault_journal.sh` → expect PASS
- [ ] **chmod +x** `claude/scripts/vault-journal.sh`
- [ ] **Commit**

---

## SPRINT 3: Slash command, test runner, docs & end-to-end validation

⚠️ **Depends on: SPRINT 1 & SPRINT 2 complete.**

### Stream A: claude/commands/journal.md
- [ ] **Write failing test** `claude/tests/test_journal_command.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  J="$ROOT/commands/journal.md"
  [ -f "$J" ] || { echo "FAIL: missing"; exit 1; }
  grep -qi "vault_write" "$J" || { echo "FAIL: must instruct vault_write"; exit 1; }
  grep -qi "daily" "$J" || { echo "FAIL: must reference daily note"; exit 1; }
  echo "PASS"
  ```
- [ ] **Run to verify failure**: `bash claude/tests/test_journal_command.sh` → expect FAIL
- [ ] **Write** `claude/commands/journal.md` — adapt `opencode/commands/journal.md`: review the session, search today's daily note, write a concise Progress/Learnings/Open summary via `vault_write(kind="daily", title="YYYY-MM-DD", …)`, confirm what was saved
- [ ] **Run to verify pass**: `bash claude/tests/test_journal_command.sh` → expect PASS
- [ ] **Commit**

### Stream B: claude/tests/run.sh
- [ ] **Write** `claude/tests/run.sh` — runs every `claude/tests/test_*.sh`, prints per-test PASS/FAIL, exits non-zero if any fail:
  ```bash
  #!/usr/bin/env bash
  set -uo pipefail
  DIR="$(dirname "$0")"; fail=0
  for t in "$DIR"/test_*.sh; do
    if bash "$t" >/tmp/_t.out 2>&1; then echo "PASS  $(basename "$t")"; else echo "FAIL  $(basename "$t")"; cat /tmp/_t.out; fail=1; fi
  done
  rm -f /tmp/_t.out
  exit $fail
  ```
- [ ] **Run full suite**: `bash claude/tests/run.sh` → expect every test PASS, exit 0
- [ ] **Commit**

### Stream C: README.md
- [ ] **Update** the Claude Code section: replace "prototype — not validated" prose with the marketplace install flow (`claude plugin marketplace add ./claude/` + `claude plugin install duckbrain@<marketplace>`), the `pip install duckbrain` prerequisite, the vault-path prompt, and the session-flow diagram from the spec. Add a short "manual wiring (advanced)" subsection pointing at the still-present `scripts/claude-vault-*.sh`. Remove the "not validated end-to-end" disclaimer
- [ ] **Verify**: `grep -i "not validated" README.md` → no matches; `grep -q "plugin marketplace add" README.md` → match
- [ ] **Commit**

### Stream D: confirm install/marketplace flow against the live CLI
⚠️ **Depends on: SPRINT 1 Streams A, B (manifest + marketplace).**
- [ ] **Validate manifest**: `claude plugin validate ./claude/` → expect zero errors (note any unrecognized-field warnings; do NOT use `--strict` unless the installed CLI recognizes `userConfig`/`displayName`/marketplace fields — confirm first)
- [ ] **Add marketplace**: `claude plugin marketplace add ./claude/` → expect success; capture the resolved marketplace name for the install command
- [ ] **Dry inventory**: `claude plugin list --available --json` → confirm `duckbrain` appears
- [ ] **Commit** (document the confirmed marketplace name + exact install command in the message; feed it back into README Stream C if it differs)

### Stream E: end-to-end smoke test (hard gate)
⚠️ **Depends on: all prior streams.**
- [ ] **Verify executable bits**: `test -x claude/scripts/vault-context.sh && test -x claude/scripts/vault-nudge.sh && test -x claude/scripts/vault-precompact.sh && test -x claude/scripts/vault-journal.sh` → exit 0
- [ ] **Full bash suite green**: `bash claude/tests/run.sh` → exit 0
- [ ] **Install & configure**: `claude plugin install duckbrain@<marketplace>`; confirm the vault-path prompt appears and accepts the path
- [ ] **Verify runtime wiring** (the integration checks unit tests cannot cover): in a fresh session, confirm (a) duckbrain MCP tools are listed, (b) SessionStart context (LEARNINGS + tags + daily note) appears in the transcript, (c) the UserPromptSubmit nudge appears on the first prompt and not on an immediate second prompt, (d) `/journal` writes to today's daily note
- [ ] **Only after all of the above pass**: remove the "not validated" disclaimer from README (coordinate with Stream C)
- [ ] **Commit** (document smoke-test results in the message)

---

## Summary

### Sprint Overview
| Sprint | Name | Streams |
|--------|------|---------|
| 1 | Plugin scaffold, marketplace, static config & helpers | A, B, C, D, E, F, G |
| 2 | Hook scripts | A, B, C, D |
| 3 | Slash command, runner, docs & validation | A, B, C, D, E |

### Total Effort
- SPRINTS: 3
- STREAMS: 16

### Critical Path
SPRINT 1 Stream G (`lib.sh`) + Stream F (`fixtures.sh`) → SPRINT 2 (hook scripts) → SPRINT 3 Stream E (e2e smoke gate). SPRINT 1 Stream E (`LEARNINGS.md`) gates SPRINT 2 Stream A. SPRINT 1 Streams A + B (manifest + marketplace) gate SPRINT 3 Stream D.

## Notes

- **Test framework**: plain bash + `jq`. No bats/Node/Python. Unit tests validate config shape and script behavior; they do **not** prove Claude Code integration — Sprint 3 Stream E is the integration gate.
- **Stop → UserPromptSubmit**: the journal nudge uses a throttled `UserPromptSubmit` hook because `Stop` cannot inject `additionalContext`. Throttle is `session_id`-keyed via a marker file + `find -mmin +15`, the working equivalent of OpenCode's once-per-segment dedup flag.
- **LEARNINGS first**: `vault-context.sh` emits `LEARNINGS.md` before vault content so line-boundary truncation never drops the guard.
- **JSON-emitting hooks** (`vault-precompact.sh`) build output with `jq -n --arg`, never string interpolation — vault content with quotes/newlines escapes correctly.
- **Dynamic dates**: `vault-nudge.sh` and `vault-precompact.sh` compute `$(date +%Y-%m-%d)` at runtime.
- **Executable bits**: hooks fail silently without `chmod +x`. Every script stream ends with chmod; Sprint 3 Stream E re-verifies.
- **`--strict` caution**: `claude plugin validate --strict` treats unrecognized-field warnings as errors. Confirm the installed CLI recognizes `userConfig`/`displayName`/marketplace fields before using `--strict`, else it will fail the very manifest being shipped.
- **Existing `scripts/claude-vault-*.sh` untouched** — documented manual-wiring fallback.

### Quality Standards
- No placeholders — every file fully functional when its stream is checked off.
- Each hook script ships with a passing dedicated bash test.
- README "not validated" disclaimer removed only after Sprint 3 Stream E passes.
