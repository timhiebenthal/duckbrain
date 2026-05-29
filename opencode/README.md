# OpenCode + DuckBrain Setup

Recommended OpenCode configuration for DuckBrain users. Copy these files to your local OpenCode config directory to enable automatic learning capture and session journaling.

## Quick setup

1. **Copy the instruction file:**

   ```bash
   cp opencode/LEARNINGS.md ~/.config/opencode/LEARNINGS.md
   ```

2. **Copy the journal command:**

   ```bash
   cp opencode/commands/journal.md ~/.config/opencode/commands/journal.md
   ```

3. **Wire the instruction file into your `opencode.json`:**

   Add the LEARNINGS.md path to the `instructions` array:

   ```json
   {
     "instructions": ["/home/your-user/.config/opencode/LEARNINGS.md"]
   }
   ```

   Alternatively, use the full `opencode.json` template below (adjust paths).

## Files

| File | Purpose | Destination |
|---|---|---|
| `LEARNINGS.md` | Pre-response learning guard, triggers, session rituals | `~/.config/opencode/LEARNINGS.md` |
| `commands/journal.md` | `/journal` slash command to dump session progress + learnings | `~/.config/opencode/commands/journal.md` |
| `opencode.json` | Full config template with MCP wiring | `~/.config/opencode/opencode.json` or project-level `.opencode/opencode.json` |

## How it works

```
Session start: LEARNINGS.md prompts AI to read today's daily note
       ↓
During session: Pre-response guard checks for learnings before every reply
       ↓
Session end:   User types /journal → AI dumps full summary to daily note
       ↓
Next session:  AI reads previous daily → loads context → continues where they left off
```

## MCP configuration

The `opencode.json` template includes a ready-to-use DuckBrain MCP definition. Update `VAULT_PATH` to point at your Obsidian vault, and `directory` to where you cloned DuckBrain:

```json
{
  "duckbrain": {
    "type": "local",
    "command": ["uv", "run", "--directory", "/path/to/duckbrain", "duckbrain"],
    "enabled": true,
    "environment": {
      "VAULT_PATH": "/path/to/your/vault"
    }
  }
}
```
