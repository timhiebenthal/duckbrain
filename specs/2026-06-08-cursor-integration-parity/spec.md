# Cursor Integration Parity — Specification

## Overview

DuckBrain v0.5.0 ships polished integrations for OpenCode (v2.1 TypeScript plugin) and Claude Code (self-contained plugin with 4 lifecycle hooks). Cursor has 25M+ users but its DuckBrain integration is primitive — two prototype bash scripts (`scripts/cursor-vault-context.sh`, `scripts/cursor-vault-journal.sh`) with a known-broken SessionStart hook and no guard, rituals, or journal command.

This spec brings Cursor integration to parity with v0.5.0 by exploiting what Cursor **does** support reliably: `.cursorrules` (always injected into system prompt), `.cursor/mcp.json` (MCP wiring), `.cursor/commands/` (slash commands), and `SessionEnd` hooks. The gap from the broken `SessionStart` hook is filled by `.cursorrules` — it's actually more reliable because it survives compaction and session resume natively.

The deliverable is a `cursor/` directory at repo root that a user copies into their Cursor workspace. No plugin system to target — Cursor doesn't have one.

**Cursor capability map (key constraint):**

| Feature | OpenCode | Claude Code | Cursor |
|---|---|---|---|
| MCP wiring | `.opencode/opencode.json` | `.mcp.json` (auto) | `.cursor/mcp.json` ✅ |
| Session context injection | `system.transform` every call | `SessionStart` hook | `.cursorrules` ✅ |
| Pre-response learning guard | `LEARNINGS.md` instructions | `LEARNINGS.md` in SessionStart | `.cursorrules` instructions ✅ |
| Journal nudge during session | `session.idle` re-prompt | `UserPromptSubmit` throttled | ❌ No hook exists |
| Compaction awareness | `session.compacting` | `PreCompact` hook | ❌ No hook exists |
| Session end journal | `session.idle` + `/journal` | `/journal` + SessionEnd timestamp | SessionEnd hook + `/journal` ✅ |
| Install flow | Copy files to `~/.config/` | `claude plugin install` | Copy files to workspace ✅ |
| Plugin manifest | — | `plugin.json` | ❌ No plugin system |

**Key insight:** `.cursorrules` is always injected into the system prompt — it naturally survives compaction, session resume, and window close in ways that hook-based injection doesn't. The trade-off is it can't be tiered (tags every call, dailies first call) since it's injected in full every turn. But `.cursorrules` content is small (~6K chars), matching OpenCode's total per-call injection size, and the always-injected guard is arguably better than hook-injected guards that scroll out of context.

## Requirements

### Functional Requirements

- **FR1** `.cursorrules` includes the complete DuckBrain integration:
  - **Learning guard**: pre-response checklist, trigger table, session rituals, daily note structure, save formats — mirrors `opencode/LEARNINGS.md` and `claude/LEARNINGS.md`
  - **Vault context instructions**: tells the AI to call `vault_context()` at session start to get today's + yesterday's daily notes and keyword search results
  - **Tool usage guidance**: when to use vault tools vs. web search (tag routing), how to write daily notes (server stamps HH:MM), vault_search-first-before-write pattern
  - **Caveman-concise style**: same communication norms as OpenCode/Claude Code LEARNINGS
- **FR2** `.cursor/mcp.json` wires the duckbrain MCP server with `VAULT_PATH` from environment variable — uses `uv run` from the local DuckBrain repo (matches how OpenCode config does it)
- **FR3** `commands/journal.md` implements the `/journal` slash command — same functionality as OpenCode and Claude Code `/journal`: review session, search today's daily, write Progress/Learnings/Open summary, check for permanent learnings, confirm
- **FR4** `hooks/vault-journal.sh` is a SessionEnd hook that appends `## Session end — HH:MM` timestamp to today's daily note — replaces the prototype `scripts/cursor-vault-journal.sh`
- **FR5** `README.md` documents the complete setup flow: copy files to Cursor workspace, wire the SessionEnd hook in `~/.cursor/hooks.json`, install uv if needed, set VAULT_PATH
- **FR6** Deprecation notice: the old `scripts/cursor-vault-context.sh` and `scripts/cursor-vault-journal.sh` are left in place but marked as superseded — `.cursorrules` replaces the broken context script, the new `cursor/hooks/vault-journal.sh` replaces the old journal script
- **FR7** Existing `scripts/cursor-vault-context.sh` and `scripts/cursor-vault-journal.sh` remain untouched as the documented manual-wiring fallback (same policy as `scripts/claude-vault-*.sh` in the Claude plugin spec)

### Non-Functional Requirements

- `.cursorrules` content must stay under ~8K chars (Cursor has no documented context cap for rules, but OpenCode's ~6K baseline is the target)
- All vault file reads gracefully no-op when vault path is unset or files are missing — never crash a Cursor session
- SessionEnd hook script must handle missing vault path (exit 0) and missing daily note (no-op)
- Hook must work on Linux (user runs WSL2) — no macOS portability required (Cursor on Windows runs agent on WSL)
- No new Python, Node, or package dependencies — hook is pure bash. MCP server already requires `uv`.
- `.cursorrules` text must be plain markdown — no JSON, no frontmatter (Cursor injects rules as raw system prompt text)

## Scope

### In Scope

- New `cursor/` directory at repo root:
  - `cursor/.cursorrules` — complete DuckBrain integration rules
  - `cursor/.cursor/mcp.json` — MCP server wiring
  - `cursor/commands/journal.md` — `/journal` slash command
  - `cursor/hooks/vault-journal.sh` — SessionEnd hook script
  - `cursor/README.md` — setup instructions
- Update `README.md` top-level to include Cursor in the integrations list (alongside OpenCode and Claude Code)
- Deprecation notice in the old `scripts/cursor-*` files

### Out of Scope

- Tiered injection (tags every call, dailies first call): Cursor has no per-call system prompt transform — `.cursorrules` is always injected in full. The content is small enough (~6K) that full injection every turn is acceptable.
- Compaction awareness: Cursor has no `PreCompact` hook. `.cursorrules` naturally survives compaction since it's re-injected into the fresh system prompt — this is arguably better than hook-based injection anyway.
- Idle auto-save / journal nudge: Cursor has no `session.idle` or `UserPromptSubmit` hook. The standing guard in `.cursorrules` tells the AI to journal proactively, but there is no unsolicited re-prompt. This is a hard gap — documented, not fixable.
- Plugin install flow: Cursor has no plugin system. Users copy files manually.
- SessionStart hook: confirmed broken by Cursor devs — `additionalContext` is never injected. This spec does not attempt to fix or work around it beyond `.cursorrules`.
- OpenCode or Claude Code plugin files — no changes to `opencode/` or `claude/`.
- Python/server-side changes — no changes to `src/duckbrain/`.

## Approach

### Technical Approach

**Directory structure:**

```
cursor/
├── .cursorrules              # Core integration file (injected into every Cursor system prompt)
├── .cursor/
│   └── mcp.json              # MCP server wiring (env.VAULT_PATH)
├── commands/
│   └── journal.md            # /journal slash command
├── hooks/
│   └── vault-journal.sh      # SessionEnd hook (manual install to ~/.cursor/hooks/)
└── README.md                 # Setup instructions for users
```

**`.cursorrules` — The Core Integration File**

This is the centerpiece. Since SessionStart hooks are broken, and Cursor has no `system.transform` equivalent, `.cursorrules` carries everything that OpenCode's plugin and Claude Code's SessionStart hook inject. The file is always present in the AI's system prompt.

Content sections (in injection order — guard first, same priority as Claude Code's SessionStart):

1. **`<vault-context>` block — Tags + Learnings Ritual**: Mirror of OpenCode's tier-1 injection. Full tag list (routing signal), vault learnings ritual (when to save, triggers, format), timestamp guarantee note. This is the "always injected" content — same size as OpenCode's per-call injection (~2K chars tags + ~4K chars ritual instructions).

2. **`<vault-session> block — Session Start Instructions**: Tells the AI to begin every session by calling `vault_context()` to get today's + yesterday's daily notes and keyword search. Unlike hook-based injection which happens automatically, the AI must be instructed to make the call. This is a model behavior instruction, not a context push.

3. **Pre-response learning guard**: Checklist, trigger table, session rituals — same content as `opencode/LEARNINGS.md` and `claude/LEARNINGS.md`.

4. **Vault tool usage guidance**: When to use vault tools vs. web search, vault_search-first-before-write pattern, daily note structure, caveman-concise style.

Design decisions:
- **Why one file, not split?** Cursor injects `.cursorrules` as a single block. There's no mechanism to reference external instruction files (unlike OpenCode's `instructions` array in `opencode.json`). Splitting content into multiple files would require Cursor-specific `.cursor/rules/*.mdc` patterns with `globs` — but `.cursorrules` is simpler, more portable, and the single-file approach has been battle-tested (OpenCode's ritual block is also one block in `system.transform`).
- **Why tags + ritual always?** The tags block is ~2K chars. The LEARNINGS guard is ~4K chars. Together they're ~6K — well within reasonable system prompt overhead. OpenCode's tier-1 injection is also ~6K on every call. Cursor injects this into every turn, same effective cost.
- **Why session context as an instruction, not injected data?** Cursor has no SessionStart hook that works. The alternative is telling the AI to call `vault_context()` at session start — this is actually how OpenCode's `system.transform` tier-2 injection works conceptually (the plugin pushes context, but the AI still decides what to do with it). With `.cursorrules`, the AI has the same information (here's what `vault_context` returns, use it) but must make the call itself. This is acceptable — search-first-before-action is a core principle of the vault workflow.

**`.cursor/mcp.json`:**

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

Design decisions:
- Uses `uv run --directory` with local repo path (same pattern as OpenCode's `opencode.example.json`) — no PyPI dependency. Users who installed via `uv tool install` can change this to `command: "duckbrain"`.
- `VAULT_PATH` reads from shell environment via `${env:VAULT_PATH}` — same as how `uvx duckbrain` works in Claude Code plugin. Users set `VAULT_PATH` once in `~/.bashrc`.
- The `--directory` path is a placeholder users must update — documented in README.

**`commands/journal.md`:**

Same structure as `opencode/commands/journal.md` and `claude/commands/journal.md`:
1. Review the session (code changes, debugging, decisions, investigations)
2. Search today's daily note via `vault_search`
3. Write summary (Progress/Learnings/Open) via `vault_write(kind="daily", …)`
4. Check for permanent learnings (create/update wiki concept pages)
5. Confirm what was saved

Differences from OpenCode version:
- Uses MCP tool names directly (`vault_search`, `vault_read`, `vault_write`) — no client-specific wrappers
- No `$ARGUMENTS` pass-through (Cursor command syntax may differ; documented in README if needed)

**`hooks/vault-journal.sh`:**

Pure bash, independent of `lib.sh` (the Claude plugin's shared library — not needed for one script). Logic:
1. Read `VAULT_PATH` from environment
2. If unset, exit 0 (no-op)
3. Compute today's date and current time
4. If `$VAULT_PATH/daily/$TODAY.md` exists, append `\n\n## Session end — HH:MM\n`
5. Exit 0 (SessionEnd output is ignored by Cursor — pure file side-effect)

Replaces `scripts/cursor-vault-journal.sh` — same logic, better structured, lives in the `cursor/` directory for easier discovery.

**Deprecation of old scripts:**

`scripts/cursor-vault-context.sh`:
- Add a deprecation notice at the top: "Superseded by cursor/.cursorrules. This file is kept as a manual-wiring fallback."
- Leave the script body intact (working code, just no longer the recommended path)

`scripts/cursor-vault-journal.sh`:
- Add a deprecation notice: "Superseded by cursor/hooks/vault-journal.sh. This file is kept as a manual-wiring fallback."
- Leave the script body intact

### User Experience

Setup flow (one-time):
1. Copy `cursor/.cursorrules` to project root (or adapt to `.cursor/rules/` if preferred)
2. Copy `cursor/.cursor/mcp.json` to project `.cursor/` directory
3. Copy `cursor/commands/journal.md` to project `.cursor/commands/`
4. Copy `cursor/hooks/vault-journal.sh` to `~/.cursor/hooks/` and `chmod +x`
5. Add to `~/.cursor/hooks.json`:
   ```json
   {
     "version": 1,
     "hooks": {
       "sessionEnd": [
         { "command": "/path/to/vault-journal.sh" }
       ]
     }
   }
   ```
6. Set `VAULT_PATH` in `~/.bashrc`
7. Update `.cursor/mcp.json` with correct `--directory` path

Session flow after setup:
```
Session start → .cursorrules is injected into system prompt
     ↓
AI reads guard + rituals → calls vault_context() to load today's + yesterday's dailies
     ↓
During session → guard prompts AI to journal after non-trivial work
     ↓               (no unsolicited re-prompt — AI must self-initiate journaling)
     ↓
Session end → user types /journal → AI writes summary to daily note
     ↓
SessionEnd hook → appends "Session end — HH:MM" timestamp
     ↓
Next session → .cursorrules re-injected → AI reads guard → calls vault_context() → continues
```

**Known UX gaps (documented, not fixable):**
- No unsolicited journal nudge during session (OpenCode has `session.idle`, Claude Code has `UserPromptSubmit`). The guard tells the AI to journal proactively, but it must self-initiate.
- No automatic context injection at session start — the AI must call `vault_context()` itself. `.cursorrules` instructions make this explicit.
- No compaction awareness — `.cursorrules` naturally re-injects after context loss (always in system prompt), so this is actually not a gap.

## Dependencies

- Cursor editor (version supporting `.cursorrules`, `.cursor/mcp.json`, `.cursor/commands/`, and hooks)
- `uv` on PATH — MCP server runs via `uv run duckbrain`
- `VAULT_PATH` env var set to Obsidian vault root
- Vault directory structure: `wiki/tags.md`, `wiki/log.md`, `daily/YYYY-MM-DD.md`

## Success Criteria

- `.cursorrules` content is under 8K chars and covers: tags + ritual, session start instructions, learning guard, tool usage guidance
- `.cursor/mcp.json` is valid JSON and matches the duckbrain MCP server schema
- `commands/journal.md` triggers a vault write to today's daily note when invoked in Cursor
- `hooks/vault-journal.sh` appends `## Session end — HH:MM` to today's daily note when the session ends (verified by checking the file)
- Hook exits 0 when `VAULT_PATH` is unset and when daily note does not exist
- README setup instructions are complete and accurate — a new user can follow them without prior DuckBrain knowledge
- Old `scripts/cursor-*` files have deprecation notices
- Top-level `README.md` updated to list Cursor alongside OpenCode and Claude Code
- Quality gates: `uv run ruff check src/duckbrain/`, `uv run mypy src/duckbrain/`, `uv run pytest` all pass (no Python code changes expected)

## Notes

- **`.cursorrules` vs `.cursor/rules/`**: Cursor recently added support for `.cursor/rules/*.mdc` files with `globs` and `alwaysApply` metadata. This spec uses `.cursorrules` for simplicity — one file, no metadata, works with all Cursor versions. The README can mention `.cursor/rules/` as an alternative for users who prefer project-specific rule files. The content is the same either way.
- **`{env:VAULT_PATH}` in mcp.json**: Cursor supports `${env:VAR}` syntax in `.cursor/mcp.json`. This is the standard Cursor MCP env variable reference — distinct from Claude Code's `${user_config.KEY}` (plugin-level) and OpenCode's `"environment": {"VAULT_PATH": "..."}` (inline). The README must clearly document this.
- **SessionEnd parity gap**: OpenCode's end-of-session capture is a model re-prompt that writes a full journal. Cursor's SessionEnd hook cannot invoke the model, so it only appends a timestamp. The actual journal write relies on the user typing `/journal`. This is identical to the Claude Code plugin's SessionEnd limitation (documented in the Claude spec's parity-gap note) — not a Cursor-specific defect.
- **No marketplace/distribution**: Unlike the Claude Code plugin (installed via `claude plugin marketplace`), the Cursor integration is distributed as source files to copy. A future v2 could add a `cursor-setup.sh` script to automate the copy + hooks wiring, but for v1 parity the manual README flow is sufficient and aligns with how OpenCode's integration is distributed.
- **Dynamic dates**: The `.cursorrules` file uses placeholder text ("today's date") — the AI computes the actual date at runtime via `vault_context()`. The server stamps HH:MM timestamps on writes. No hardcoded dates in the rules file.
- **WSL path handling**: Not needed in `.cursorrules` (it's just text). Not needed in `vault-journal.sh` — Cursor on Windows runs the agent on WSL, so `VAULT_PATH` is already a WSL path. The Claude plugin's `resolve_vault_path` with `wslpath` is unnecessary here.
- **The existing `scripts/cursor-*` files are left untouched** as the manual-wiring fallback — same policy as `scripts/claude-vault-*.sh` in the Claude plugin spec.
