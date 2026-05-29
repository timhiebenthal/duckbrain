# DuckBrain

<p align="center">
  <img src="https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/logo/logo_writing_white_bg.png" alt="DuckBrain" width="500" />
</p>

DuckDB-backed MCP memory server for Obsidian vaults. Gives AI coding agents read/write access to your personal wiki — structured pages, full-text search, automatic indexing.

## Installation

Pick your agent:

- [OpenCode](#opencode) — MCP server + session plugin (recommended)
- [Claude Code](#claude-code) — MCP server + CLAUDE.md + SessionStart hook
- [Cursor](#cursor) — MCP server + rules + hooks
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

> **Prototype** — based on Claude Code docs, not yet validated end-to-end. Scripts work, but hook → injection pipeline needs manual verification.

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

#### SessionEnd hook (optional — auto-journal)

Auto-stamp session end in today's daily note:

```bash
curl -o ~/.claude/hooks/vault-journal.sh \
  https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/scripts/claude-vault-journal.sh
chmod +x ~/.claude/hooks/vault-journal.sh
```

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/full/path/to/.claude/hooks/vault-journal.sh"
          }
        ]
      }
    ]
  }
}
```

Appends `## Session end — HH:MM` to today's daily note when the session ends.

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

Optionally add `.cursor/rules/duckbrain.mdc` with `alwaysApply: true`:

```yaml
---
description: DuckBrain vault knowledge base integration
alwaysApply: true
---
# DuckBrain vault
Call vault_info() at session start to discover vault topics.
Use vault_search() when the query matches vault content.
```

#### SessionStart hook (prototype — context injection)

> **Prototype** — Cursor's `additional_context` from `sessionStart` hooks has a confirmed bug (dropped due to timing). The `env` output works, but context injection does not yet. Track: [Cursor forum](https://forum.cursor.com/t/sessionstart-hook-additional-context-is-never-injected-into-agents-initial-system-context/158452)

```bash
mkdir -p ~/.cursor/hooks/
curl -o ~/.cursor/hooks/vault-context.sh \
  https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/scripts/cursor-vault-context.sh
chmod +x ~/.cursor/hooks/vault-context.sh
```

Add to `~/.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "command": "/full/path/to/.cursor/hooks/vault-context.sh" }
    ]
  }
}
```

#### SessionEnd hook (auto-journal)

```bash
curl -o ~/.cursor/hooks/vault-journal.sh \
  https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/scripts/cursor-vault-journal.sh
chmod +x ~/.cursor/hooks/vault-journal.sh
```

Add to `~/.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "sessionEnd": [
      { "command": "/full/path/to/.cursor/hooks/vault-journal.sh" }
    ]
  }
}
```

Appends `## Session end — HH:MM` to today's daily note when a session ends.

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

## Nerdy Details

Implementation internals — not needed for installation.

### Architecture

```
┌──────────────────┐     MCP stdio     ┌─────────────────────────────────┐
│    AI Agent      │ ◄──────────────►  │      DuckBrain MCP Server       │
│                  │                   │                                 │
│  Claude Code     │                   │  vault_info  ──┐                │
│  OpenCode        │                   │  vault_search ─┤  DuckDB FTS    │
│  Cursor          │                   │  vault_read  ──┤  Filesystem    │
│  Hermes          │                   │  vault_write ──┘  Filesystem    │
└──────────────────┘                   └────────┬────────┬───────────────┘
                                                │        │
                    query ┌─────────────────────┘        └── read/write ──┐
             (full index) ▼                                               ▼  (single file)
         ┌──────────────────────┐                              ┌───────────────────────────┐
         │  DuckDB (in-memory)  │                              │    Your Obsidian Vault    │
         │                      │                              │                           │
         │  pages (in-memory    │    rebuilt from scratch      │  wiki/entities/           │
         │  rebuilt every search)│    on every query           │  wiki/concepts/           │
         │  ┌───────────────┐   │                              │  wiki/sources/            │
         │  │ filepath      │   │                              │  wiki/synthesis/          │
         │  │ title         │   │                              │  daily/                   │
         │  │ kind          │   │                              │  wiki/index.md            │
         │  │ tags          │   │                              │  wiki/log.md              │
         │  │ body          │   │                              │                           │
         │  │ created       │   │                              │                           │
         │  │ updated       │   │                              │                           │
         │  └───────────────┘   │                              │                           │
         │                      │                              │                           │
         │  BM25 search query:  │                              │                           │
         │  SELECT ...          │                              │                           │
         │  FROM pages p        │                              │                           │
         │  WHERE fts_match_bm25│                              │                           │
         │    (p.filepath,      │                              │                           │
         │     'segfault')      │                              │                           │
         │  AND kind='concept'  │                              │                           │
         │  ORDER BY score DESC │                              │                           │
         └──────────────────────┘                              └───────────────────────────┘
```

- **Reads** vault files directly — no index to sync, no watchers, no duplicate storage
- **Searches** via DuckDB FTS (BM25 ranking), rebuilt fresh from disk on every query
- **Writes** new pages with YAML frontmatter, auto-updating index, log, and tags

---

## Building from Source

```bash
git clone https://github.com/timhiebenthal/duckbrain.git
cd duckbrain
uv sync
uv run duckbrain  # will hang waiting on stdio — that's correct
```
