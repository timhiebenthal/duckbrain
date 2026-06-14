# imprint.md — AI-Maintained Identity Document — Implementation Tasks

## Overview

Wire `imprint.md` into all four agent injection pipelines (OpenCode, Claude Code, Cursor, Hermes). No new infrastructure — existing context injection layer handles it.

## Tasks

## SPRINT 1: Foundation — OpenCode Plugin (Primary Agent)

### Stream A: vault-context-helpers.ts + vault-context-helpers.test.ts

- [ ] **T1.1** Add `loadIdentity()` to `vault-context-helpers.ts` — reads `imprint.md` from vault root, returns content or null
- [ ] **T1.2** Write failing test for `loadIdentity()` in `vault-context-helpers.test.ts`
  - Test: returns content when `imprint.md` exists
  - Test: returns null when file missing (graceful degradation)
  - Test: returns null when vault is empty
- [ ] **T1.3** Run tests to verify RED: `cd opencode/plugins && bun test` → test fails (import error, missing function)
- [ ] **T1.4** Implement `loadIdentity()` in helpers
- [ ] **T1.5** Run tests to verify GREEN: `cd opencode/plugins && bun test` → all pass
- [ ] **T1.6** Commit: `feat: add loadIdentity() helper for imprint.md injection`

### Stream B: vault-context.ts

- [ ] **T2.1** Wire Tier 3 identity injection in `vault-context.ts` — call `loadIdentity()` and inject `<vault-identity>` block in system prompt (after tags, before session context)
- [ ] **T2.2** Commit: `feat: inject imprint.md as Tier 3 in OpenCode plugin`

## SPRINT 2: All Other Agents (Parallel)

### Stream A: claude/scripts/vault-context.sh

- [ ] **T3.1** Add `cat "$VAULT_PATH/imprint.md"` wrapped in `<vault-identity>` tags to Claude Code SessionStart hook script
- [ ] **T3.2** Commit: `feat: inject imprint.md in Claude Code SessionStart hook`

### Stream B: cursor/.cursorrules

- [ ] **T4.1** Add imprint.md identity + maintenance instruction block
- [ ] **T4.2** Commit: `feat: add imprint.md instructions to cursor/.cursorrules`

### Stream C: .cursorrules (project root)

- [ ] **T5.1** Add imprint.md identity + maintenance instruction block (same content as Stream B)
- [ ] **T5.2** Commit: `feat: add imprint.md instructions to root .cursorrules`

### Stream D: AGENTS.md

- [ ] **T6.1** Add imprint.md identity + maintenance instruction block
- [ ] **T6.2** Commit: `feat: add imprint.md instructions to AGENTS.md`

## SPRINT 3: Seed + Polish

- [ ] **T7.1** Create seed `imprint.md` at vault root with content from concept wiki page draft
- [ ] **T7.2** Update CHANGELOG.md
- [ ] **T7.3** Version bump to `0.7.0`
- [ ] **T7.4** Commit: `feat: imprint.md — AI-maintained identity document`
- [ ] **T7.5** Run full quality gates: `uv run pytest`, `uv run ruff check src/duckbrain/`, `uv run ruff format --check src/duckbrain/`

## Summary

### Sprint Overview

| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| 1 | OpenCode Plugin | T1.1–T1.6, T2.1–T2.2 | A, B |
| 2 | All Other Agents | T3.1–T3.2, T4.1–T4.2, T5.1–T5.2, T6.1–T6.2 | A, B, C, D |
| 3 | Seed + Polish | T7.1–T7.5 | 1 stream |

### Total Effort
- SPRINTS: 3
- STREAMS: 7 (across sprints)
- Tasks: 23

### Dependency Map

Sprint 1 → Sprint 2 → Sprint 3

Within Sprint 1:
- Stream B (`vault-context.ts`) ⚠️ Depends on: Stream A (`loadIdentity()` is imported)

Within Sprint 2: all streams are independent — can run in parallel.

## Notes

- **imprint.md** lives at `<vault_root>/imprint.md` — the user's Obsidian vault, not the DuckBrain repo. The seed file creation (T7.1) writes it to the vault path via `vault_write`.
- **Testing `vault-context.ts` plugin**: The plugin entry point depends on the OpenCode SDK runtime and cannot be unit-tested in isolation. The `loadIdentity()` helper IS unit-tested. The plugin logic is a simple `if (identity) output.system.push(...)` — verified by inspection and integration test.
- **OpenCode tests**: `cd opencode/plugins && bun test` — real filesystem, no mocks, follows same convention as existing tests.
- **DuckBrain Python tests**: `uv run pytest` — verify no regression.
- **No new dependencies** — all changes use existing runtime APIs (`Bun.file()`, `cat`, `vault_write`).

### Quality Standards
- No placeholders — every task produces working, mergeable code
- TDD for all TypeScript changes (test failure verified before implementation)
- Config file changes (shell scripts, .cursorrules, AGENTS.md) verified by reading the file after edit
- Full test suite passes before claiming completion
