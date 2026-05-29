# DuckBrain

<p align="center">
  <img src="https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/logo/logo_writing_white_bg.png" alt="DuckBrain" width="500" />
</p>

DuckDB-backed MCP memory server for Obsidian vaults. Gives AI coding agents read/write access to your personal wiki — structured pages, full-text search, automatic indexing. Your vault filesystem is the single source of truth.

## Table of Contents

- [OpenCode (Installation)](#opencode) — MCP + session plugin (recommended)
- [Claude Code (Installation)](#claude-code) — MCP + CLAUDE.md
- [Cursor (Installation)](#cursor) — MCP + rules
- [Hermes (Installation)](#hermes) — MCP + AGENTS.md
- [Tools](#tools) — vault_search, vault_read, vault_write, vault_context, vault_info
- [Vault Schema](#vault-schema) — required directory structure
- [Installing from Source](#installing-from-source)

---

## OpenCode

**Best experience** — session plugin injects vault context automatically.

### 1. MCP server

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
      "env": {
        "VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### 2. Session plugin

Download the plugin from GitHub (you don't need the repo cloned):

```bash
mkdir -p ~/.config/opencode/plugins/
curl -o ~/.config/opencode/plugins/vault-context.ts \
  https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/opencode/plugins/vault-context.ts
```

**What the plugin does** (invisible to you, visible to the AI):
- Injects vault tags (topic routing) into system prompt
- Loads today's + yesterday's daily notes
- Adds learnings ritual (when to save, how to format)
- Adds journaling rule (save after non-trivial work)
- Preserves context through compaction

### 3. Done

Restart OpenCode. The AI loads vault tags and recent daily notes into context automatically — no manual vault_info() needed.

---

## Claude Code

### 1. MCP server

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
      "env": {
        "VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### 2. Context injection

Add to `.claude/CLAUDE.md`:

```markdown
# DuckBrain vault

Call vault_info() at session start to discover vault topics.
Use vault_search() or vault_read() when the query matches vault content.
Use vault_context() to load daily notes and search in one call.

After non-trivial work, save learnings with vault_write().
```

### 3. Done

Restart Claude Code. The AI has vault tools and instructions.

---

## Cursor

### 1. MCP server

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
      "env": {
        "VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### 2. Rules (optional)

Add to `.cursor/rules/duckbrain.md`:

```markdown
# DuckBrain vault

Call vault_info() at session start to discover vault topics.
Use vault_search() when the query matches vault content.
```

### 3. Done

Restart Cursor. The AI has vault tools.

---

## Hermes

### 1. MCP server

Add to `mcp.json`:

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "duckbrain"],
      "env": {
        "VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### 2. Instructions

Add to `AGENTS.md`:

```markdown
# DuckBrain vault

Call vault_info() at session start to discover vault topics.
Use vault_search() when the query matches vault content.
After non-trivial work, save learnings with vault_write().
```

### 3. Done

Restart Hermes. The AI has vault tools.

---

## Tools

| Tool | What it does |
|------|-------------|
| `vault_search` | Full-text search over vault pages (BM25 ranking) |
| `vault_read` | Read a page by title or filepath |
| `vault_write` | Create a new page or append to today's daily note |
| `vault_context` | Load daily notes + keyword search in one call |
| `vault_info` | Vault stats: page counts, tags, last modified |

### vault_search

```python
vault_search("memory", kind="concept", limit=10)
```

### vault_read

```python
vault_read(title="Claude Mem")
vault_read(filepath="wiki/entities/claude-mem.md")
```

### vault_write

```python
vault_write(kind="entity", title="New Tool", content="Description...", tags=["ai", "tool"])
vault_write(kind="daily", title="Session notes", content="What I learned...", tags=["learning"])
```

### vault_context

```python
vault_context(keywords=["memory", "mcp"])  # daily notes + search
vault_context(include_dailies=False, keywords=["memory"])  # search only
vault_context(include_search=False)  # daily notes only
```

---

## Vault Schema

Your vault needs this structure:

```
your-vault/
├── wiki/
│   ├── entities/       # people, orgs, tools
│   ├── concepts/       # ideas, frameworks
│   ├── sources/        # summaries of ingested content
│   ├── synthesis/      # cross-cutting analysis
│   ├── index.md        # page catalog (auto-updated by DuckBrain)
│   ├── log.md          # write history (auto-updated)
│   └── tags.md         # topic tags with frequency (auto-updated)
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

## Installing from Source

```bash
git clone https://github.com/timhiebenthal/duckbrain.git
cd duckbrain
uv sync
uv run duckbrain  # will hang waiting on stdio — that's correct
```
