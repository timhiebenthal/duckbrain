# DuckBrain

<p align="center">
  <img src="https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/logo/logo_writing_white_bg.png" alt="DuckBrain" width="500" />
</p>

DuckDB-backed MCP memory server for Obsidian vaults. Gives AI coding agents read/write access to your personal wiki — structured pages, full-text search, automatic indexing.

## Installation

Install DuckBrain:

```bash
pip install duckbrain
```

... or with the dependency manager of your choice (uv, poetry, ...)

Then pick your agent:

- [OpenCode](#opencode) — MCP server + session plugin (recommended)
- [Claude Code](#claude-code) — MCP server + CLAUDE.md + SessionStart hook
- [Cursor](#cursor) — MCP server + rules + hooks
- [Hermes](#hermes) — MCP server + AGENTS.md
- Other Agents (e.g. Codex, Gemini) will follow after testing

---

### OpenCode

**Best experience** (as I use OpenCode myself) — session plugin gives the AI automatic vault awareness.

Add to `opencode.json`:

```json
{
  "mcp": {
    "duckbrain": {
      "command": "duckbrain",
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

**Prerequisite:** `uv` or `uvx` on your PATH — the plugin runs the MCP server via `uvx duckbrain` (no manual `pip install` needed; uvx fetches and caches it automatically)

#### Install via plugin marketplace

```bash
claude plugin marketplace add /path/to/duckbrain/claude/
claude plugin install duckbrain@duckbrain-local
# Claude Code prompts for your vault path, or pass it non-interactively:
# claude plugin install duckbrain@duckbrain-local --config vault_path=/path/to/vault
```

Claude Code prompts for your vault path at enable time — no manual `VAULT_PATH` env var needed.

#### What you get

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
Session end → type /journal → Claude writes summary to daily note
     ↓
SessionEnd hook → appends "Session end — HH:MM" timestamp
```

The plugin bundles four hooks (SessionStart, UserPromptSubmit, PreCompact, SessionEnd), the duckbrain MCP server config, and a `/journal` slash command. No manual `settings.json` editing.

#### Manual wiring (advanced)

If you prefer wiring hooks yourself without the plugin, the standalone scripts in `scripts/claude-vault-*.sh` still work — see the comments in each file for the required `settings.json` entries.

---

### Cursor

**Disclaimer:** Not tested yet

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "duckbrain",
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

### Hermes Agent

Has been tested and validated.

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
