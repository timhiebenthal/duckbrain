# DuckBrain — Cursor Integration

Brings DuckBrain vault awareness to Cursor via `.cursorrules` (always injected into system prompt), MCP server wiring, a `/journal` slash command, and a SessionEnd hook that timestamps your daily note.

## Prerequisites

- [Cursor](https://cursor.com) editor
- [`uv`](https://docs.astral.sh/uv/) on PATH (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `VAULT_PATH` set in `~/.bashrc` pointing to your Obsidian vault root
- Vault directory structure: `daily/YYYY-MM-DD.md`, `wiki/tags.md`, `wiki/log.md`
- This DuckBrain repo cloned locally

## Setup (one-time)

### 1. Copy `.cursorrules` to your project root

```bash
cp cursor/.cursorrules /path/to/your/project/.cursorrules
```

Cursor injects `.cursorrules` into every system prompt automatically. No further configuration needed for vault awareness.

Alternative: use `.cursor/rules/duckbrain.mdc` with `alwaysApply: true` if you prefer the newer rules format. Content is the same.

### 2. Copy `.cursor/mcp.json` to your project

```bash
mkdir -p /path/to/your/project/.cursor
cp cursor/.cursor/mcp.json /path/to/your/project/.cursor/mcp.json
```

Then edit the file and replace `/path/to/duckbrain` with the absolute path to your DuckBrain clone:

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "--directory", "/your/actual/path/to/duckbrain", "duckbrain"],
      "env": {
        "VAULT_PATH": "/mnt/c/Users/YourName/Documents/obsidian/brain"
      }
    }
  }
}
```

**Note on env vars**: Cursor's `.cursor/mcp.json` does not support environment variable interpolation (e.g., `${env:VAULT_PATH}` is not resolved). Both `VAULT_PATH` and the `--directory` path must be hardcoded. Update them whenever your vault or repo moves. Workarounds (wrapper script, `npx envmcp`) are possible but add complexity — hardcoding is the simplest approach for most users.

If you installed DuckBrain via `uv tool install duckbrain`, you can simplify to `"command": "duckbrain"` and remove the `--directory` arg.

### 3. Copy the `/journal` command

```bash
mkdir -p /path/to/your/project/.cursor/commands
cp cursor/commands/journal.md /path/to/your/project/.cursor/commands/journal.md
```

Invoke with `/journal` in Cursor. Type any extra context inline after the command — Cursor may or may not support argument substitution in command files depending on your version.

### 4. Install the SessionEnd hook

```bash
mkdir -p ~/.cursor/hooks/
cp cursor/hooks/vault-journal.sh ~/.cursor/hooks/vault-journal.sh
chmod +x ~/.cursor/hooks/vault-journal.sh
```

Wire it in `~/.cursor/hooks.json` (create the file if it doesn't exist):

```json
{
  "version": 1,
  "hooks": {
    "sessionEnd": [
      { "command": "/home/youruser/.cursor/hooks/vault-journal.sh" }
    ]
  }
}
```

Use the full absolute path to the script. Appends `## Session end — HH:MM` to today's daily note when a Cursor session ends.

### 5. Set VAULT_PATH

Add to `~/.bashrc` (or `~/.zshrc`):

```bash
export VAULT_PATH="/mnt/c/Users/YourName/Documents/obsidian/brain"
```

Reload: `source ~/.bashrc`

## Session flow

```
Session start → .cursorrules injected into every system prompt
     ↓
AI reads guard + session start instructions
     ↓
AI calls vault_context(keywords=[...]) — loads today's + yesterday's daily notes + search
AI calls vault_read("wiki/tags.md") — loads tag routing signal
     ↓
During session → guard prompts AI to journal after non-trivial work
     ↓               (AI must self-initiate — no unsolicited nudge)
     ↓
User types /journal → AI writes summary to daily note
     ↓
SessionEnd hook → appends "Session end — HH:MM" timestamp
     ↓
Next session → .cursorrules re-injected → AI calls vault_context → continues
```

## Known gaps

- **No unsolicited journal nudge**: OpenCode has `session.idle`, Claude Code has `UserPromptSubmit`. Cursor has neither. The guard in `.cursorrules` tells the AI to journal proactively, but it must self-initiate.
- **No automatic context injection at session start**: The AI must call `vault_context()` itself. `.cursorrules` instructions make this explicit and it works reliably.
- **No compaction awareness**: Not needed — `.cursorrules` is re-injected into the fresh system prompt after every compaction.
- **SessionStart hook is broken**: Cursor's `additional_context` from SessionStart hooks is confirmed dropped. This integration avoids it entirely — `.cursorrules` fills the gap.

## Troubleshooting

**MCP tools not available in Cursor**
- Check `.cursor/mcp.json` is in the project root (not `~/.cursor/`)
- Verify `uv` is on PATH: `which uv`
- Verify `VAULT_PATH` is exported: `echo $VAULT_PATH`
- Try restarting Cursor after editing `mcp.json`

**vault_context returns no search results**
- Keywords are required for search. The AI must pass `keywords=[...]` — omitting them returns dailies only.

**SessionEnd hook not appending timestamp**
- Check `VAULT_PATH` is set in your shell environment (not just `.bashrc` — Cursor may need a full shell restart)
- Verify the hook is executable: `ls -la ~/.cursor/hooks/vault-journal.sh`
- Check `~/.cursor/hooks.json` has the correct absolute path

## File reference

| File | Purpose | Copy to |
|------|---------|---------|
| `.cursorrules` | Vault awareness + learning guard (injected every turn) | Project root |
| `.cursor/mcp.json` | MCP server wiring | Project `.cursor/` |
| `commands/journal.md` | `/journal` slash command | Project `.cursor/commands/` |
| `hooks/vault-journal.sh` | SessionEnd timestamp hook | `~/.cursor/hooks/` |
