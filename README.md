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

Download the session plugin (you need [bun](https://bun.sh) for the install):

```bash
mkdir -p ~/.config/opencode/plugins/
cd ~/.config/opencode/plugins

for f in vault-context.ts vault-context-helpers.ts package.json; do
  curl -O "https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/opencode/plugins/$f"
done

bun install
```

Restart OpenCode. The plugin gives your AI automatic vault awareness and a few useful defaults:

- **Vault-aware context** — your AI sees your vault's topics, recent notes, and today's daily entry automatically. No need to ask "what's in my vault" or paste paths.
- **Daily note journaling** — the AI captures session progress, decisions, and discoveries into your daily note as you work, so you don't lose context between sessions.
- **Real local-time timestamps** — entries are timestamped with your actual local time, not whatever the AI guesses.
- **End-of-session save** — when you finish a session, the AI is prompted to journal anything new before the conversation closes. (Window close is still a loss — use `/journal` for guaranteed save.)

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
┌──────────────────────────────────────────────────────────────┐
│                      AI Agent                                │
│  ┌──────────────────────────┐  ┌──────────────────────────┐  │
│  │ MCP Client (stdio)       │  │ Hooks / Plugins          │  │
│  │  vault_search,           │  │ (SessionStart, system    │  │
│  │  vault_read, vault_write │  │  transform — inject      │  │
│  │  vault_context, vault_info│  │  vault context into      │  │
│  │                          │  │  system prompt)          │  │
│  └──────────┬───────────────┘  └──────────┬───────────────┘  │
└─────────────│──────────────────────────────│──────────────────┘
              │ MCP stdio                    │ reads directly
              ▼                              ▼ from vault
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  DuckBrain MCP Server        │  │ Side channel:                │
│  vault_info   ──► DuckDB FTS │  │  wiki/tags.md                │
│  vault_search ──► DuckDB FTS │  │  daily/YYYY-MM-DD.md         │
│  vault_read   ──► Filesystem │  │  wiki/log.md                 │
│  vault_write  ──► Filesystem │  │                              │
└──────────────┬───────────────┘  └──────────────────────────────┘
               │ reads/writes
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Your Obsidian Vault                              │
│  wiki/entities/  wiki/concepts/  wiki/sources/  wiki/synthesis/      │
│  daily/          wiki/index.md   wiki/log.md    wiki/tags.md         │
└──────────────────────────────────────────────────────────────────────┘
```

- **Reads** vault files directly — no index to sync, no watchers, no duplicate storage
- **Searches** via DuckDB FTS (BM25 ranking), rebuilt fresh from disk on every query
- **Writes** new pages with YAML frontmatter, auto-updating index, log, and tags

### Inspirations

This project stands on the shoulders of several ideas and tools:

- **[Andrej Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — the idea that a personal markdown wiki, co-maintained by humans and AI agents, compounds into a persistent knowledge base. The vault schema (entities, concepts, sources, synthesis, daily log) is directly inspired by this.
- **[DuckDB](https://duckdb.org/)** — the embedded analytical database that makes full-text search over flat files viable without a server, index sync, or persistent storage. The decision to use in-memory FTS instead of a vector database was a deliberate trade-off for simplicity.
- **[Obsidian](https://obsidian.md/)** — the local-first, markdown-native note-taking tool that treats your files as the truth. DuckBrain exists because Obsidian vaults deserve tooling that respects the filesystem.
- **[MemSearch](https://github.com/zilliztech/memsearch)** and **[Open Brain (OB1)](https://github.com/NateBJones-Projects/OB1)** — early experiments in cross-tool agent memory that demonstrated the *need* for structured vault write-back while choosing different architectures. Their strengths and gaps directly informed DuckBrain's design.
- **[Agent Memory Systems (6-level taxonomy)](https://www.youtube.com/watch?v=UHVFcUzAGlM)** — Simon Scrapes' comprehensive comparison of Claude Code memory approaches provided the framework for understanding where DuckBrain fits in the ecosystem (Level 6: cross-tool MCP with dedicated server).
- **[trellis-datamodel](https://github.com/timhiebenthal/trellis-datamodel)** — the same author's data modeling tool whose CI/CD patterns (trusted PyPI publishing, version-diff release detection, Keep a Changelog) were borrowed for this project's repository readiness.
- **[mondayDB 3 — Solving HTAP for a Trillion-Table System](https://engineering.monday.com/mondaydb-3-solving-htap-for-a-trillion-table-system/)** — monday.com's engineering blog on their DuckDB-powered CQRS read serving layer at production scale. Proved that DuckDB in-process with per-tenant file isolation is a viable architecture — the same pattern DuckBrain applies at personal-wiki scale.

The core decision — **build, don't integrate** — came from a [structured comparison](https://github.com/timhiebenthal/duckbrain/blob/main/specs/2026-05-28-duckdb-memory-mcp/spec.md) of 7 existing tools. All failed on one requirement: vault schema-aware write-back. Rather than fork or extend, DuckBrain started from first principles: what's the simplest thing that gives agents structured read/write access to an Obsidian vault? The answer was DuckDB + MCP + ~500 lines of Python.

---

## Building from Source

```bash
git clone https://github.com/timhiebenthal/duckbrain.git
cd duckbrain
uv sync
uv run duckbrain  # will hang waiting on stdio — that's correct
```
