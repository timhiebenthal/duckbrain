# DuckBrain

<p align="center">
  <img src="https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/logo/logo_writing_white_bg.png" alt="DuckBrain" width="500" />
</p>

DuckDB-backed MCP memory server for Obsidian vaults. Gives AI coding agents read/write access to your personal wiki — structured pages, full-text search, automatic indexing.

## Installation

Pick your agent:

- [OpenCode](#opencode) — MCP server + session plugin (recommended)
- [Claude Code](#claude-code) — MCP server + CLAUDE.md + SessionStart hook
- [Cursor](#cursor) — MCP server + rules
- [Hermes](#hermes) — MCP server + AGENTS.md

---

### OpenCode

**Best experience** — session plugin gives the AI automatic vault awareness.

```bash
pip install duckbrain
```

Add to `opencode.json`:

```json
{
  "mcp": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "duckbrain"],
      "env": { "VAULT_PATH": "/path/to/your/vault" }
    }
  }
}
```

Download the session plugin (no repo clone needed):

```bash
mkdir -p ~/.config/opencode/plugins/
curl -o ~/.config/opencode/plugins/vault-context.ts \
  https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/opencode/plugins/vault-context.ts
```

The plugin makes the AI aware of your vault topics and recent daily notes automatically — no manual tool calls needed. It also adds a learnings ritual and journaling rule so the AI saves session progress on its own.

Restart OpenCode.

---

### Claude Code

```bash
pip install duckbrain
```

Add to `.claude/settings.json` (project) or `~/.claude/settings.json` (global):

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "duckbrain"],
      "env": { "VAULT_PATH": "/path/to/your/vault" }
    }
  }
}
```

#### CLAUDE.md

Add to `.claude/CLAUDE.md`:

```markdown
# DuckBrain vault

Call vault_info() at session start to discover vault topics.
Use vault_search() or vault_read() when the query matches vault content.
Use vault_context() to load daily notes and search in one call.
After non-trivial work, save learnings with vault_write().
```

#### SessionStart hook (optional — auto-context)

For automatic vault awareness without manual tool calls, add a SessionStart hook.
Download the script (no repo clone needed):

```bash
mkdir -p ~/.claude/hooks/
curl -o ~/.claude/hooks/vault-context.sh \
  https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/scripts/claude-vault-context.sh
chmod +x ~/.claude/hooks/vault-context.sh
```

Add to the same `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "/full/path/to/.claude/hooks/vault-context.sh"
          }
        ]
      }
    ]
  }
}
```

The hook injects vault tags and recent daily notes into Claude's context at session start — no manual `vault_info()` needed.

Restart Claude Code.

---

### Cursor

```bash
pip install duckbrain
```

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "duckbrain"],
      "env": { "VAULT_PATH": "/path/to/your/vault" }
    }
  }
}
```

Optionally add `.cursor/rules/duckbrain.md`:

```markdown
# DuckBrain vault
Call vault_info() at session start to discover vault topics.
Use vault_search() when the query matches vault content.
```

Restart Cursor.

---

### Hermes

Add to `mcp.json`:

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "duckbrain"],
      "env": { "VAULT_PATH": "/path/to/your/vault" }
    }
  }
}
```

Add to `AGENTS.md`:

```markdown
# DuckBrain vault
Call vault_info() at session start to discover vault topics.
Use vault_search() when the query matches vault content.
After non-trivial work, save learnings with vault_write().
```

Restart Hermes.

---

## Tools

| Tool | What it does |
|------|-------------|
| `vault_search` | Full-text search over vault pages |
| `vault_read` | Read a page by title or filepath |
| `vault_write` | Create a page or append to today's daily note |
| `vault_context` | Load daily notes + keyword search in one call |
| `vault_info` | Vault stats: page counts, tags, last modified |

---

## Vault Schema

```
your-vault/
├── wiki/
│   ├── entities/       # people, orgs, tools
│   ├── concepts/       # ideas, frameworks
│   ├── sources/        # summaries of ingested content
│   ├── synthesis/      # cross-cutting analysis
│   ├── index.md        # page catalog (auto-updated)
│   ├── log.md          # write history (auto-updated)
│   └── tags.md         # topic index (auto-updated)
├── daily/              # daily notes (YYYY-MM-DD.md)
└── .env                # VAULT_PATH (optional)
```

Pages use YAML frontmatter:

```yaml
---
title: Claude Mem
item-type: entity
tags: [ai, memory, mcp]
created: 2026-05-28
updated: 2026-05-28
---
```

---

## Building from Source

```bash
git clone https://github.com/timhiebenthal/duckbrain.git
cd duckbrain
uv sync
uv run duckbrain  # will hang waiting on stdio — that's correct
```
