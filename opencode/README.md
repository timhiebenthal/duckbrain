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

    Alternatively, use the full `opencode.example.json` template below (adjust paths).

## Files

| File | Purpose | Destination |
|---|---|---|
| `LEARNINGS.md` | Pre-response learning guard, triggers, session rituals | `~/.config/opencode/LEARNINGS.md` |
| `commands/journal.md` | `/journal` slash command to dump session progress + learnings | `~/.config/opencode/commands/journal.md` |
| `plugins/vault-context.ts` | Session plugin (V1 + V2 dual entrypoint) — system prompt injection, compaction snapshot, idle journal nudge | `~/.config/opencode/plugins/vault-context.ts` |
| `plugins/vault-context-helpers.ts` | Pure, testable helpers shared by both runtimes | `~/.config/opencode/plugins/vault-context-helpers.ts` |
| `opencode.example.json` | Full config template with MCP wiring (rename to `opencode.json` to use) | `~/.config/opencode/opencode.json` or project-level `.opencode/opencode.json` |

## Plugin: OpenCode 1 and 2

`plugins/vault-context.ts` supports both OpenCode versions from one default export:

- **OpenCode 2** reads `Plugin.define({ id, setup })` and registers hooks on the context.
- **OpenCode 1** reads the `server` entrypoint (needs **OpenCode >= 1.18.29**).

Install with `duckbrain install-plugin --editor opencode`, or copy the files as shown in the root README.

The two hook wirings are separate code; the injected text comes from shared helpers so the runtimes cannot drift.

### Config key

OpenCode 1 used `plugin`; OpenCode 2 renamed it to `plugins` and moved package-and-options tuples to objects:

```jsonc
// V1
{ "plugin": ["opencode-example-plugin", ["./plugin/local.ts", { "enabled": true }]] }

// V2
{ "plugins": ["opencode-example-plugin", { "package": "./plugin/local.ts", "options": { "enabled": true } }] }
```

DuckBrain's plugin is dropped into `~/.config/opencode/plugins/` and auto-discovered, so no config entry is required on either version. OpenCode 2 auto-migrates supported V1 config, so an existing `opencode.json` keeps working.

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

The `opencode.example.json` template includes a ready-to-use DuckBrain MCP definition. Update `VAULT_PATH` to point at your Obsidian vault, and `directory` to where you cloned DuckBrain:

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
