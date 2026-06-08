# Claude Code Plugin Parity — Specification

## Overview

The OpenCode integration ships a polished session plugin (`opencode/`) that gives the AI automatic vault awareness: tags injected on every turn, daily notes loaded at session start, a compaction snapshot to survive context resets, and a `/journal` command for end-of-session capture. The Claude Code equivalent (`scripts/claude-vault-*.sh` + a README snippet) is marked "prototype — not validated end-to-end" and requires manual `settings.json` editing.

This spec closes that gap by building a **proper Claude Code plugin** (`claude/`) — a self-contained directory distributed through a bundled marketplace manifest. The plugin bundles all hooks, the MCP server config, and the `/journal` slash command. No manual `settings.json` editing. The vault path is prompted at enable time via `userConfig`.

All Claude Code plugin mechanics below were verified against the installed `claude` CLI and the official hooks/plugins reference (June 2026):
- `userConfig` values reach hook subprocesses as `CLAUDE_PLUGIN_OPTION_<KEY>` env vars, and are substitutable as `${user_config.KEY}` in `.mcp.json`. ✅ documented
- `SessionStart` and `UserPromptSubmit` accept **plain stdout** as injected context. ✅ documented
- `PreCompact` requires **JSON** `hookSpecificOutput.additionalContext` (plain stdout is not honored). ✅ documented
- `Stop` does **not** support `additionalContext` injection — so the journal nudge is implemented as a throttled `UserPromptSubmit` hook instead. ✅ verified (Stop is absent from the additionalContext placement list)
- `claude plugin install` installs from **marketplaces** only (no `--plugin-dir` flag). Persistent install therefore requires a bundled `marketplace.json`. ✅ verified against `claude plugin install --help`

## Requirements

### Functional Requirements

- **FR1** The `SessionStart` hook injects the LEARNINGS pre-response guard (first, so it survives truncation), then vault tags, today's and yesterday's daily notes, and recent log activity into Claude's context at every session start (including `resume` and after `/compact`).
- **FR2** The `PreCompact` hook injects a compaction snapshot (recent log tail + today's daily note + journal nudge) as JSON `additionalContext` before context is wiped.
- **FR3** A **throttled `UserPromptSubmit` hook** injects a concise journal nudge — re-surfacing the standing LEARNINGS instruction so it isn't forgotten deep into a long session. It fires at most once per throttle window (default 15 minutes) per session, keyed on `session_id`, so it is not per-turn noise. The nudge asks Claude to record any learning, challenge, or notable result concisely, and to skip when there is nothing noteworthy.
- **FR4** The `SessionEnd` hook appends a `## Session end — HH:MM` timestamp to today's daily note (a file side-effect; SessionEnd cannot inject context or re-prompt the model).
- **FR5** The plugin bundles the duckbrain MCP server config so it starts automatically when the plugin is enabled — no separate MCP wiring step.
- **FR6** The plugin prompts the user for their vault path via `userConfig` at enable time — no manual `VAULT_PATH` env var setup.
- **FR7** All hook scripts handle WSL vault paths transparently (Windows path → `/mnt/...` via `wslpath`, with a sed fallback).
- **FR8** A `/journal` slash command triggers end-of-session journaling equivalent to the OpenCode `/journal` command.
- **FR9** The plugin ships a `marketplace.json` so users install it with `claude plugin marketplace add` + `claude plugin install duckbrain@<marketplace>`.
- **FR10** The Claude Code section of `README.md` is updated with the validated marketplace install flow, and documents `pip install duckbrain` as a hard prerequisite for the MCP server.

### Non-Functional Requirements

- Hook scripts must run on both Linux and macOS — date helpers handle both GNU (`date -d`) and BSD (`date -v`) syntax.
- All file I/O gracefully no-ops when the vault path is unset or target files do not exist (never crash a session).
- Hook context output stays within Claude Code's documented 10,000-character cap. Truncation, when needed, happens on **line boundaries** (not mid-byte, which would split multibyte glyphs like `—` / `📅`), and the LEARNINGS guard is emitted first so it is never the block that gets dropped.
- No new Python or Node runtime dependencies — hooks are pure shell. `jq` is required (used for safe JSON construction in hooks and for tests); it is already part of the toolchain.
- Plugin passes `claude plugin validate ./claude/` with zero errors.

## Scope

### In Scope

- New plugin directory: `claude/` at the repo root
  - `claude/.claude-plugin/plugin.json` — manifest with `userConfig` for vault path
  - `claude/.claude-plugin/marketplace.json` — marketplace manifest listing the duckbrain plugin
  - `claude/.mcp.json` — duckbrain MCP server wiring (`command: "duckbrain"`, reads `${user_config.vault_path}`)
  - `claude/hooks/hooks.json` — SessionStart, UserPromptSubmit, PreCompact, SessionEnd registrations
  - `claude/commands/journal.md` — `/journal` slash command
  - `claude/scripts/lib.sh` — shared sourced helper (path resolution, date helpers, safe file reads, line-boundary truncation)
  - `claude/scripts/vault-context.sh` — SessionStart (LEARNINGS-first + vault context)
  - `claude/scripts/vault-nudge.sh` — UserPromptSubmit (throttled journal nudge)
  - `claude/scripts/vault-precompact.sh` — PreCompact (snapshot + nudge, JSON)
  - `claude/scripts/vault-journal.sh` — SessionEnd (timestamp append)
  - `claude/LEARNINGS.md` — source for learning-guard content injected by SessionStart
- Update `README.md` Claude Code section with the validated marketplace install flow
- Leave existing `scripts/claude-vault-*.sh` untouched as the documented manual-wiring fallback

### Out of Scope

- Tiered injection (tags always, session context first-call-only): requires persistent per-call state — complexity not justified. The throttled nudge (FR3) already provides the one stateful behavior worth having.
- OpenCode plugin files — no changes to `opencode/`.
- Python/server-side changes — no changes to `src/duckbrain/`.
- Cursor/Hermes integration — no changes to those scripts.

## Approach

### Technical Approach

**Plugin structure:**

```
claude/
├── .claude-plugin/
│   ├── plugin.json          # manifest, userConfig for vault_path
│   └── marketplace.json     # marketplace manifest (enables persistent install)
├── .mcp.json                # duckbrain MCP server, reads ${user_config.vault_path}
├── hooks/
│   └── hooks.json           # SessionStart, UserPromptSubmit, PreCompact, SessionEnd
├── commands/
│   └── journal.md           # /journal slash command
├── scripts/
│   ├── lib.sh               # shared sourced helper
│   ├── vault-context.sh     # SessionStart
│   ├── vault-nudge.sh       # UserPromptSubmit (throttled)
│   ├── vault-precompact.sh  # PreCompact
│   └── vault-journal.sh     # SessionEnd
└── LEARNINGS.md             # learning-guard source (injected by vault-context.sh)
```

**`plugin.json`:**

```json
{
  "name": "duckbrain",
  "displayName": "DuckBrain",
  "description": "Obsidian vault awareness for Claude Code — tags, daily notes, and learning capture",
  "userConfig": {
    "vault_path": {
      "type": "directory",
      "title": "Vault path",
      "description": "Absolute path to your Obsidian vault (Windows or WSL path accepted)",
      "required": true
    }
  }
}
```

The vault path reaches hook subprocesses as `CLAUDE_PLUGIN_OPTION_VAULT_PATH` and is substituted in `.mcp.json` as `${user_config.vault_path}`.

**`marketplace.json`:** Lists the duckbrain plugin so it is installable by name. Exact schema to be confirmed against `claude plugin marketplace add --help` during implementation; minimally a `name` and a `plugins` array with `{ "name": "duckbrain", "source": "./" }` (relative to the marketplace root).

**`.mcp.json`:**

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "duckbrain",
      "env": { "VAULT_PATH": "${user_config.vault_path}" }
    }
  }
}
```

`command: "duckbrain"` matches the repo's primary documented MCP config (README lines 38, 77, 178) and assumes `pip install duckbrain` (documented as a prerequisite in FR10).

**`hooks/hooks.json`:**

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/vault-context.sh" } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/vault-nudge.sh" } ] }
    ],
    "PreCompact": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/vault-precompact.sh" } ] }
    ],
    "SessionEnd": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/vault-journal.sh" } ] }
    ]
  }
}
```

**WSL path handling:** Centralized in `lib.sh::resolve_vault_path`, called by every script before any `[ -f … ]` test. Uses `wslpath` when available; otherwise a sed fallback (backslashes → `/`, `C:` → `/mnt/c`, lowercase drive letter).

**`lib.sh` (shared, sourced):**
- `resolve_vault_path(raw)` — WSL/Windows → POSIX path
- `safe_cat(path)` / `tail_lines(path, n)` — no-op when the file is absent
- `today()` / `yesterday()` — GNU/BSD `date` fallbacks
- `truncate_lines(max_chars)` — reads stdin, emits whole lines until the byte budget is hit (never splits a line or a multibyte glyph)

**`vault-context.sh` (SessionStart — plain stdout):** resolve vault path (exit 0 if unset); emit `LEARNINGS.md` from `$CLAUDE_PLUGIN_ROOT` **first**; then `## Vault topic tags` + `wiki/tags.md`; then today's & yesterday's daily notes if present; then `### Recent vault writes` + last 20 log lines; pipe the whole thing through `truncate_lines 9500`.

**`vault-nudge.sh` (UserPromptSubmit — throttled, plain stdout):** read `session_id` from the hook's stdin JSON (`jq -r .session_id`); marker file `${TMPDIR:-/tmp}/duckbrain-nudge-$session_id`; if the marker is missing or older than the throttle window (`find "$marker" -mmin +15`), print the concise nudge to stdout and `touch` the marker; otherwise print nothing and exit 0. Nudge text (single line, dynamic date): *"If this turn produced a learning, a challenge, or a notable result, journal it concisely: vault_write(kind=\"daily\", title=\"<today>\", content=\"## Topic\\n\\nDetails\"). Caveman-concise — cut filler. If nothing noteworthy, skip."*

**`vault-precompact.sh` (PreCompact — JSON):** resolve vault path; build snapshot (last 15 log lines + today's daily + journal-checkpoint nudge with dynamic date); emit `{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"…"}}` built with `jq -n --arg` (correct escaping). When the vault path is unset, still emit valid JSON carrying just the nudge.

**`vault-journal.sh` (SessionEnd):** resolve vault path; if today's daily note exists, append `\n## Session end — $(date +%H:%M)\n`; otherwise no-op. Output is ignored by Claude Code; this is a pure file side-effect.

**`commands/journal.md`:** instruct Claude to review the session (code changes, debugging, decisions), search today's daily note, and write a concise Progress / Learnings / Open summary via `vault_write(kind="daily", title="YYYY-MM-DD", …)`, then confirm what was saved. Mirrors OpenCode `/journal`.

**`LEARNINGS.md`:** mirrors `opencode/LEARNINGS.md` adapted to Claude Code language. Not installed separately — read and emitted by `vault-context.sh` at session start.

### User Experience

Setup (after `pip install duckbrain`):

```bash
claude plugin marketplace add /path/to/duckbrain/claude/
claude plugin install duckbrain@duckbrain
```

Claude Code prompts for the vault path at enable time, then the plugin is live. Session flow:

```
Enable plugin → prompted for vault path once
     ↓
Session start → SessionStart injects LEARNINGS guard + tags + daily notes
     ↓
During session → guard prompts Claude to journal after non-trivial work
     ↓
Every ~15 min → UserPromptSubmit re-surfaces the concise journal nudge (throttled)
     ↓
Context full → PreCompact injects snapshot + journal nudge
     ↓
Session end → user types /journal → Claude writes summary to daily note
     ↓
SessionEnd hook → appends "Session end — HH:MM" timestamp
```

## Dependencies

- Claude Code version with plugin + marketplace support (verified against the installed CLI: `plugin install`, `plugin marketplace`, `plugin validate` all present)
- `pip install duckbrain` — the MCP server `command: "duckbrain"` requires the package on PATH (matches README's primary config)
- `jq` — for hook JSON construction and tests
- `wslpath` on WSL2; sed fallback elsewhere
- Vault directory structure: `wiki/tags.md`, `wiki/log.md`, `daily/YYYY-MM-DD.md`

## Success Criteria

- `claude plugin validate ./claude/` passes with zero errors.
- `claude plugin marketplace add ./claude/` then `claude plugin install duckbrain@<marketplace>` completes and prompts for the vault path.
- `SessionStart` output (LEARNINGS first, then tags + daily notes) is visible in a fresh session transcript and stays under 10k chars without a broken trailing glyph.
- `UserPromptSubmit` nudge appears on the first prompt of a session and is **suppressed** on a rapid second prompt within the throttle window (verified via the marker-file test).
- `PreCompact` `additionalContext` appears in the post-compaction context.
- `SessionEnd` appends the timestamp to the daily note (verified by checking the file).
- All scripts exit 0 when `CLAUDE_PLUGIN_OPTION_VAULT_PATH` is unset and when vault files do not exist.
- `/journal` triggers a vault write to today's daily note.
- duckbrain MCP tools load in a session after install (no separate MCP wiring).
- README Claude Code section updated; "not validated" disclaimer removed only after the manual smoke test passes.

## Notes

- **Stop vs UserPromptSubmit**: the `Stop` hook cannot inject `additionalContext` (verified — it is absent from the documented placement list; its only lever is `decision: "block"`). Using `UserPromptSubmit` with a `session_id`-keyed throttle is the faithful, working equivalent of OpenCode's once-per-idle-segment nudge, and avoids per-turn token cost.
- **SessionEnd parity gap**: OpenCode's end-of-session capture is a model *re-prompt* that writes a full journal. Claude Code's `SessionEnd` hook cannot invoke the model, so it only appends a timestamp; the actual end-of-session journal write relies on the user (or the throttled nudge) triggering `/journal`. This is inherent to hooks being non-agentic, not a defect — documented here so it isn't mistaken for full equivalence.
- **SessionStart re-fires** on `startup`, `resume`, `clear`, and `compact`, so vault context + LEARNINGS re-inject automatically after `/compact` without a separate plugin.
- **Dynamic dates**: `vault-nudge.sh` and `vault-precompact.sh` compute `$(date +%Y-%m-%d)` at runtime — never hardcode the date.
- **JSON-emitting hooks** build output with `jq -n --arg`, never string interpolation, so vault content containing quotes/newlines is escaped correctly.
- **Executable bits**: hooks fail silently if scripts are not `chmod +x`. Every script ships executable; e2e validation re-verifies.
- **The existing `scripts/claude-vault-*.sh` are left untouched** as the manual-wiring fallback; the README documents both paths.
