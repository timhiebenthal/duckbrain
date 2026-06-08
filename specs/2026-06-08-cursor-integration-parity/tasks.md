# Cursor Integration Parity — Implementation Tasks

## Overview

Build a `cursor/` directory at repo root with `.cursorrules` (the core integration file), `.cursor/mcp.json` (MCP server wiring), `/journal` slash command, SessionEnd hook script, and user-facing README. Add deprecation notices to the old `scripts/cursor-*` prototypes and update the top-level `README.md` to list Cursor alongside OpenCode and Claude Code.

The integration exploits Cursor's reliable features: `.cursorrules` (always injected into system prompt), `.cursor/mcp.json` (MCP wiring), `.cursor/commands/` (slash commands), and `SessionEnd` hook. The broken `SessionStart` hook is avoided entirely — `.cursorrules` fills the gap.

## Testing Approach

Only one deliverable is a real bash script (`cursor/hooks/vault-journal.sh`) — the rest are content/config files. Tests for content files verify shape (file exists, required sections present, char count limit). The hook script gets a full behavior test with a throwaway temp vault, following the same pattern as `claude/tests/test_vault_journal.sh`.

All tests are plain bash (no Node/Python deps). A `cursor/tests/run.sh` runs all test files. Python quality gates (`pytest`, `ruff`, `mypy`) still apply but expect no Python changes.

TDD sequence: write failing bash test → run to confirm failure → implement → run to confirm pass → commit.
Content-file tasks verify at char count / section level, not behavioral.

---

## Tasks

## SPRINT 1: Core content files + test infrastructure

Foundation. **Begin with Stream D (test runner) — it is the prerequisite for Sprint 2's hook test.** Streams A-C are independent of each other and can run in parallel after D is written. Content files are tested for shape (exists, valid, sections present, size limit). These tests are deliberately lightweight — the real integration verification happens when a user copies the files into Cursor.

### Stream A: cursor/.cursorrules

- [x] **Write failing test** `cursor/tests/test_cursorrules.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  F="$ROOT/.cursorrules"
  [ -f "$F" ] || { echo "FAIL: missing"; exit 1; }
  CHARS=$(wc -c < "$F")
  [ "$CHARS" -le 8000 ] || { echo "FAIL: too large — $CHARS chars (max 8000)"; exit 1; }
  grep -qi "pre-response learning guard" "$F" || { echo "FAIL: learning guard"; exit 1; }
  grep -qi "vault_context(" "$F" || { echo "FAIL: vault_context instruction"; exit 1; }
  grep -qi "vault_write" "$F" || { echo "FAIL: vault_write trigger"; exit 1; }
  grep -qi "vault_search" "$F" || { echo "FAIL: vault_search guidance"; exit 1; }
  grep -qi "caveman" "$F" || { echo "FAIL: caveman-concise style"; exit 1; }
  # Must NOT contain OpenCode-specific references
  ! grep -qi "opencode" "$F" || { echo "FAIL: OpenCode references must be removed"; exit 1; }
  ! grep -qi "Bun.file" "$F" || { echo "FAIL: OpenCode references must be removed"; exit 1; }
  echo "PASS"
  ```
- [x] **Run to verify failure**: `bash cursor/tests/test_cursorrules.sh` → expect FAIL (file missing)
- [x] **Write** `cursor/.cursorrules` — single markdown file with these sections, in injection order:
  1. **`<vault-context>` block**: Explains vault directory layout (`wiki/`, `daily/`), when to use vault tools vs. web search (if a vault tag matches the topic, search vault first), and how to retrieve the tag list (`vault_read("wiki/tags.md")`). Do NOT hardcode tag data — the AI reads tags live. Keep this block to ~1K chars.
  2. **`<vault-session>` block**: Tell the AI to begin every session by: (a) calling `vault_context(keywords=["<keywords from current task>"])` — keywords MUST be derived from the user's first message or task description (omitting keywords disables search: server only searches `if include_search and keywords`); (b) calling `vault_read("wiki/tags.md")` for tag routing. Both calls together replace what the Claude Code SessionStart hook injected automatically.
  3. **Pre-response learning guard**: Checklist, trigger table, session rituals — adapt `claude/LEARNINGS.md` for Cursor. NO references to OpenCode (`Bun.file`, `opencode`, plugin runtime). Use only MCP tool names (`vault_search`, `vault_read`, `vault_write`, `vault_context`, `vault_info`).
  4. **Tool usage guidance**: vault_search-first-before-write pattern, daily note structure (server stamps HH:MM — model writes content, not timestamps), caveman-concise style.
  Content must be plain markdown (no JSON, no frontmatter). Target under 8K chars, budget ~7K (`claude/LEARNINGS.md` alone is ~3.5K). Review against `opencode/LEARNINGS.md` and `claude/LEARNINGS.md` to ensure parity.
- [x] **Run to verify pass**: `bash cursor/tests/test_cursorrules.sh` → expect PASS
- [x] **Commit**

### Stream B: cursor/.cursor/mcp.json

- [x] **Write failing test** `cursor/tests/test_mcp_config.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  F="$ROOT/.cursor/mcp.json"
  jq empty "$F" || { echo "FAIL: invalid JSON"; exit 1; }
  jq -e '.mcpServers.duckbrain' "$F" >/dev/null || { echo "FAIL: missing duckbrain server"; exit 1; }
  # Must use uv run with local repo (OpenCode-style), not uvx
  jq -e '.mcpServers.duckbrain.command == "uv"' "$F" >/dev/null || { echo "FAIL: command must be uv"; exit 1; }
  jq -e '.mcpServers.duckbrain.args | index("run")' "$F" >/dev/null || { echo "FAIL: missing run arg"; exit 1; }
  jq -e '.mcpServers.duckbrain.args | index("duckbrain")' "$F" >/dev/null || { echo "FAIL: missing duckbrain arg"; exit 1; }
  jq -e '.mcpServers.duckbrain.env.VAULT_PATH // empty' "$F" >/dev/null || { echo "FAIL: VAULT_PATH env"; exit 1; }
  echo "PASS"
  ```
- [x] **Run to verify failure**: `bash cursor/tests/test_mcp_config.sh` → expect FAIL
- [x] **Write** `cursor/.cursor/mcp.json`:
  ```json
  {
    "mcpServers": {
      "duckbrain": {
        "command": "uv",
        "args": ["run", "--directory", "/path/to/duckbrain", "duckbrain"],
        "env": {
          "VAULT_PATH": "${env:VAULT_PATH}"
        }
      }
    }
  }
  ```
  Both `--directory` and `VAULT_PATH` are hardcoded placeholder strings — Cursor's `.cursor/mcp.json` does not support env var interpolation (verified: `${env:VAULT_PATH}` is not resolved). Users must update both values at install time. Document this clearly in `cursor/README.md` — no env var syntax, no JSON comments.
- [x] **Run to verify pass**: `bash cursor/tests/test_mcp_config.sh` → expect PASS
- [x] **Commit**

### Stream C: cursor/commands/journal.md

- [x] **Write failing test** `cursor/tests/test_journal_command.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  F="$ROOT/commands/journal.md"
  [ -f "$F" ] || { echo "FAIL: missing"; exit 1; }
  grep -qi "vault_write" "$F" || { echo "FAIL: must instruct vault_write"; exit 1; }
  grep -qi "daily" "$F" || { echo "FAIL: must reference daily note"; exit 1; }
  grep -qi "progress" "$F" || { echo "FAIL: must include Progress section"; exit 1; }
  grep -qi "learnings" "$F" || { echo "FAIL: must include Learnings section"; exit 1; }
  grep -qi "open" "$F" || { echo "FAIL: must include Open section"; exit 1; }
  echo "PASS"
  ```
- [x] **Run to verify failure**: `bash cursor/tests/test_journal_command.sh` → expect FAIL
- [x] **Write** `cursor/commands/journal.md` — adapt `opencode/commands/journal.md` for Cursor:
  1. Review the session (code changes, debugging, decisions, investigations)
  2. Search today's daily note via `vault_search(query="YYYY-MM-DD")`
  3. Write summary via `vault_write(kind="daily", title="YYYY-MM-DD", …)` with Progress/Learnings/Open structure
  4. Check for permanent learnings (create/update wiki concept pages)
  5. Confirm what was saved
  Use MCP tool names directly (`vault_search`, `vault_read`, `vault_write`, `vault_context`). For `$ARGUMENTS`: do not assume `$ARGUMENTS` works — during implementation, verify whether Cursor's `.cursor/commands/` runner substitutes arguments and what the exact syntax is. Document the finding in `cursor/README.md`. Fallback instruction if unconfirmed: "Type extra context inline in your message after invoking /journal." Keep caveman-concise instructions.
- [x] **Run to verify pass**: `bash cursor/tests/test_journal_command.sh` → expect PASS
- [x] **Commit**

### Stream D: cursor/tests/run.sh

- [x] **Write** `cursor/tests/run.sh` — runs every `cursor/tests/test_*.sh`, prints per-test PASS/FAIL, exits non-zero if any fail:
  ```bash
  #!/usr/bin/env bash
  set -uo pipefail
  DIR="$(dirname "$0")"; fail=0
  for t in "$DIR"/test_*.sh; do
    if bash "$t" >/tmp/_ctout 2>&1; then
      echo "PASS  $(basename "$t")"
    else
      echo "FAIL  $(basename "$t")"
      cat /tmp/_ctout
      fail=1
    fi
  done
  rm -f /tmp/_ctout
  exit $fail
  ```
- [x] **Verify runner works**: `bash cursor/tests/run.sh` → expect all PASS (Streams A-C complete before this verification step runs; the runner correctly executes each test and aggregates results)
- [x] **Commit**

---

## SPRINT 2: Hook script

⚠️ **Depends on: SPRINT 1 — Stream D (`cursor/tests/run.sh`).** The test runner is needed to add the new test.

Single stream — one file, testable bash script with real behavior.

### Stream A: cursor/hooks/vault-journal.sh  ⚠️ Depends on SPRINT 1 — Stream D

- [x] **Write failing test** `cursor/tests/test_vault_journal.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  # Create temp vault
  V=$(mktemp -d /tmp/cursor-test-XXXXXX)
  trap "rm -rf $V" EXIT
  mkdir -p "$V/daily"
  TODAY=$(date +%Y-%m-%d)
  echo "# existing content" > "$V/daily/$TODAY.md"
  # Run the hook — pipe dummy JSON input to satisfy Cursor's hook protocol (stdin consumption)
  echo '{}' | VAULT_PATH="$V" bash "$ROOT/hooks/vault-journal.sh"
  # Check timestamp was appended
  grep -q "Session end" "$V/daily/$TODAY.md" || { echo "FAIL: timestamp not appended"; exit 1; }
  # Check time format (HH:MM)
  grep -qE "Session end — [0-9][0-9]:[0-9][0-9]" "$V/daily/$TODAY.md" || { echo "FAIL: bad time format"; exit 1; }
  # Check script exits 0 when VAULT_PATH is unset
  echo '{}' | VAULT_PATH="" bash "$ROOT/hooks/vault-journal.sh" >/dev/null 2>&1; [ $? -eq 0 ] || { echo "FAIL: unset-vault exit code"; exit 1; }
  # Check script exits 0 when daily note does not exist
  V2=$(mktemp -d /tmp/cursor-test-XXXXXX)
  trap "rm -rf $V2" EXIT
  mkdir -p "$V2/daily"
  echo '{}' | VAULT_PATH="$V2" bash "$ROOT/hooks/vault-journal.sh" >/dev/null 2>&1; [ $? -eq 0 ] || { echo "FAIL: missing-note exit code"; exit 1; }
  rm -rf "$V2"
  echo "PASS"
  ```
- [x] **Run to verify failure**: `bash cursor/tests/test_vault_journal.sh` → expect FAIL
- [x] **Write** `cursor/hooks/vault-journal.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  # Consume stdin — Cursor's hook runner writes a JSON payload to stdin;
  # not reading it can cause the process to hang.
  read -r INPUT || true

  VAULT_PATH="${VAULT_PATH:-}"
  if [ -z "$VAULT_PATH" ]; then
    echo '{}'
    exit 0
  fi

  TODAY=$(date +%Y-%m-%d)
  NOW=$(date +%H:%M)
  NOTE="$VAULT_PATH/daily/$TODAY.md"

  if [ -f "$NOTE" ]; then
    printf "\n\n## Session end — %s\n" "$NOW" >> "$NOTE"
  fi

  echo '{}'
  ```
  Pure bash, no dependencies. Consumes stdin and emits `{}` — required by Cursor's hook runner protocol. Exits 0 when `VAULT_PATH` unset (no-op). Exits 0 when daily note missing (no-op). Appends `\n\n## Session end — HH:MM\n` to today's daily note (two leading newlines for separation from prior content). No `jq`, no `lib.sh`, no WSL path handling (Cursor on Windows runs the agent on WSL, so `VAULT_PATH` is already a WSL path).
- [x] **Run to verify pass**: `bash cursor/tests/test_vault_journal.sh` → expect PASS
- [x] **chmod +x** `cursor/hooks/vault-journal.sh`
- [x] **Commit**

---

## SPRINT 3: Documentation, deprecation & integration

⚠️ **Depends on: SPRINT 1 & SPRINT 2 complete.** All streams independent — parallel.

### Stream A: cursor/README.md  ⚠️ Depends on SPRINT 1 & 2 (full directory layout known)
- [x] **Write** `cursor/README.md` — user-facing setup guide. Content:
  1. What this directory is (DuckBrain Cursor integration)
  2. Prerequisites: Cursor editor, `uv` on PATH, `VAULT_PATH` set in `~/.bashrc`, Obsidian vault with `wiki/tags.md`, `wiki/log.md`, `daily/YYYY-MM-DD.md`
  3. Step-by-step setup:
     - Copy `cursor/.cursorrules` → project root
     - Copy `cursor/.cursor/mcp.json` → project `.cursor/` directory
     - Copy `cursor/commands/journal.md` → project `.cursor/commands/`
     - Copy `cursor/hooks/vault-journal.sh` → `~/.cursor/hooks/` and `chmod +x`
     - Wire hook in `~/.cursor/hooks.json` (show exact JSON snippet with placeholder path)
     - Update `--directory` path in `.cursor/mcp.json` to point at your DuckBrain clone
  4. Session flow diagram (same as spec: session start → guard → vault_context → journal → SessionEnd)
  5. Known gaps: no automatic journal nudge, no SessionStart injection — AI must call `vault_context()` itself; `.cursorrules` instructions handle this
  6. Alternative: `.cursor/rules/` directory option for Cursor users who prefer `.mdc` files
- [x] **Commit**

### Stream B: Deprecation notices in scripts/cursor-vault-context.sh and scripts/cursor-vault-journal.sh
- [x] **Edit** `scripts/cursor-vault-context.sh`: add a deprecation comment block after the shebang, before the existing code:
  ```bash
  # ⚠️ DEPRECATED — use cursor/.cursorrules instead.
  # Cursor's SessionStart hook (the event this script is wired to) has a known bug:
  # additional_context is never injected into the session. This script is kept as a
  # manual-wiring fallback. The recommended integration is cursor/.cursorrules —
  # copy it to your project root for automatic vault awareness.
  # See cursor/README.md for setup instructions.
  ```
  Leave all existing code below the deprecation block untouched.
- [x] **Edit** `scripts/cursor-vault-journal.sh`: add a deprecation comment block after the shebang:
  ```bash
  # ⚠️ DEPRECATED — use cursor/hooks/vault-journal.sh instead.
  # The new version lives in the cursor/ directory for easier discovery and has tests.
  # Kept as a manual-wiring fallback. See cursor/README.md for setup instructions.
  ```
  Leave all existing code below the deprecation block untouched.
- [x] **Verify**: `head -5 scripts/cursor-vault-context.sh` shows DEPRECATED; `head -5 scripts/cursor-vault-journal.sh` shows DEPRECATED
- [x] **Commit**

### Stream C: Update top-level README.md
- [x] **Edit** top-level `README.md` Cursor section (search for "Cursor" or "cursor" in the file):
  - If a Cursor section exists, replace it with the new integration content
  - If no Cursor section exists, add one alongside the OpenCode and Claude Code sections
  - Content: brief description of the integration, link to `cursor/README.md` for full setup, note the two hard gaps (no journal nudge, no SessionStart injection), mention `.cursorrules` as the primary mechanism
  - Remove any "prototype" or "not validated" language
- [x] **Verify**: `grep -i "cursor" README.md` returns the new section
- [x] **Commit**

### Stream D: Full test suite verification & quality gates
- [x] **Run full cursor test suite**: `bash cursor/tests/run.sh` → expect all PASS, exit 0
- [x] **Run Python quality gates**: `uv run ruff check src/duckbrain/` → 0 errors
- [x] **Run Python quality gates**: `uv run ruff format --check src/duckbrain/` → all formatted
- [x] **Run Python quality gates**: `uv run mypy src/duckbrain/` → 0 errors
- [x] **Run Python quality gates**: `uv run pytest` → all pass (expect same count as before — no Python changes)
- [x] **Verify directory structure**: all 6 files are present and correct:
  ```
  cursor/.cursorrules
  cursor/.cursor/mcp.json
  cursor/commands/journal.md
  cursor/hooks/vault-journal.sh
  cursor/README.md
  cursor/tests/run.sh
  cursor/tests/test_cursorrules.sh
  cursor/tests/test_mcp_config.sh
  cursor/tests/test_journal_command.sh
  cursor/tests/test_vault_journal.sh
  ```
- [x] **Commit**

---

## Summary

### Sprint Overview
| Sprint | Name | Streams |
|--------|------|---------|
| 1 | Core content files + test infrastructure | A (.cursorrules), B (.mcp.json), C (journal.md), D (test runner) |
| 2 | Hook script | A (vault-journal.sh) |
| 3 | Documentation, deprecation & integration | A (README.md), B (deprecation notices), C (top-level README), D (suite verification) |

### Total Effort
- SPRINTS: 3
- STREAMS: 9
- FILES CREATED: 10 (5 cursor/ files + 4 test files + 1 test runner)
- FILES EDITED: 3 (2 deprecation notices + top-level README)

### Critical Path
SPRINT 1 Stream D (test runner) → SPRINT 2 Stream A (hook script, depends on runner to add test) → SPRINT 3 Stream D (full suite verification, depends on all prior streams). All other streams are independent within their sprints.

## Notes

- **Test framework**: plain bash. No bats/Node/Python deps for cursor tests. Content-file tests verify shape (exists, valid, sections, size). Hook-script test verifies behavior. The Python `pytest`/`ruff`/`mypy` gates run separately in SPRINT 3 Stream D — they should pass without changes since no Python code is modified.
- **`.cursorrules` size target**: under 8K chars, budget ~7K. `claude/LEARNINGS.md` alone is ~3.5K; adding vault context block + session start instructions + tool usage guidance reaches ~6.5-7K. The test enforces a hard 8K cap. If content exceeds 8K, trim by removing redundancy and shortening examples — do not drop required sections. The "~6K target" from OpenCode is not achievable here while maintaining full parity.
- **No shared lib.sh**: `cursor/hooks/vault-journal.sh` is a single self-contained script. No `lib.sh` dependency — unlike the Claude plugin which has 4 scripts sharing path resolution, date helpers, and truncation logic. If future Cursor hooks are added, extract shared helpers then.
- **No fixtures.sh**: The vault-journal test creates a temp vault inline — one test doesn't justify a shared fixture module. If future tests are added, extract then.
- **No WSL path handling in hook**: Cursor on Windows runs the agent on WSL2, so `VAULT_PATH` is already a WSL path (`/mnt/c/...`). The hook doesn't need `wslpath` or sed fallbacks. If a user runs Cursor natively on macOS, `VAULT_PATH` is already a POSIX path.
- **`.cursorrules` vs `.cursor/rules/`**: The spec ships `.cursorrules` (single file, works with all Cursor versions). `cursor/README.md` mentions `.cursor/rules/*.mdc` as an alternative. The implementation only creates `.cursorrules`.
- **Old `scripts/cursor-*` files**: Marked deprecated with a comment block but otherwise untouched — same policy as `scripts/claude-vault-*.sh` in the Claude plugin spec. They remain as the documented manual-wiring fallback.
- **No Python/server changes**: This integration is purely configuration + bash. No changes to `src/duckbrain/` or `tests/`. All Python quality gates should pass unchanged.
- **No Cursor-specific plugin system**: Unlike the Claude Code plugin (which targets Claude's plugin API with manifests, marketplace, and install flow), Cursor has no plugin system. Users copy files manually. The README documents this flow clearly.

### Quality Standards
- No placeholders — every file fully functional when its stream is checked off.
- Each file has a passing test verifying its shape or behavior.
- `.cursorrules` under 8K chars with all required sections present.
- Hook script tested with `VAULT_PATH` set, unset, and daily-note-missing.
- Top-level `README.md` updated and verified not to contain "prototype" or "not validated" language.
