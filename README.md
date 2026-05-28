# duckbrain

DuckDB-backed MCP memory server for Obsidian vaults. Gives AI coding agents structured read and write access to your personal wiki — with full-text search, frontmatter-aware indexing, and automatic index/log updates.

## What it solves

Existing agent memory tools (MemSearch, Open Brain, Mem0, Supermemory) treat memory as unstructured text blobs. If you maintain a [Karpathy-style LLM wiki](https://x.com/karpathy/status/1889054630119760374) in Obsidian with typed pages (entities, concepts, sources, synthesis), YAML frontmatter, tags, and wikilinks — none of those tools understand your vault's structure.

duckbrain fills that gap. It reads your vault as-is and writes new pages following your vault's schema, so your wiki stays a single source of truth on the filesystem.

## How it works

```
AI Agent (Claude Code / OpenCode / Hermes)
        │
        │ MCP stdio
        ▼
┌─────────────────────┐
│   duckbrain server  │
│                     │
│  vault_info   ──►   │──► DuckDB FTS (in-memory)
│  vault_search ──►   │
│  vault_write  ──►   │──► Filesystem writes
└─────────────────────┘
        │
        ▼
   Your Obsidian vault
   (plain markdown on disk)
```

- **Reads** your vault files directly — no index to sync, no watchers, no duplicate storage
- **Searches** via DuckDB full-text search (BM25 ranking), built lazily in-memory on the first query
- **Writes** new pages with correct YAML frontmatter, auto-updating your index and log

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Obsidian vault structured with a `wiki/` directory containing:
  - `wiki/entities/` — people, orgs, products, tools
  - `wiki/concepts/` — ideas, frameworks, theories
  - `wiki/sources/` — one summary per ingested source
  - `wiki/synthesis/` — cross-cutting analysis
  - `wiki/index.md` — page catalog with `## Entities`, `## Concepts`, `## Sources`, `## Synthesis` sections
  - `wiki/log.md` — append-only chronological record
- Pages should use YAML frontmatter: `title`, `item-type`, `tags`, `created`, `updated`

This follows the schema defined in [AGENTS.md](https://x.com/karpathy/status/1889054630119760374). If your vault uses a different structure, duckbrain works with it — but index/log updates expect the section headers above.

## Quick Start

```bash
git clone https://github.com/your-org/duckbrain.git
cd duckbrain
uv sync
```

That's the install. To use it, **you don't run the server yourself** — your AI agent does. Add the config below, then just launch your agent as normal.

*(Optional: to verify the install, run `VAULT_PATH="/path/to/your/vault" uv run duckbrain`. It will appear to hang — that's correct, it's waiting on stdio. Press Ctrl+C to stop.)*

## Connecting to Agents

MCP stdio transport means the agent spawns duckbrain as a child process when it starts. You don't need a separate terminal or a running server. Just add this to your MCP config:

## Connecting to Agents

Add this to your MCP config (replace the vault path):

```json
{
  "duckbrain": {
    "command": "uv",
    "args": ["run", "duckbrain"],
    "env": {
      "VAULT_PATH": "/path/to/your/obsidian/vault"
    }
  }
}
```

Where to put it:

| Agent | Config file | Top-level key |
|-------|-------------|---------------|
| Claude Code | `~/.claude/claude_desktop_config.json` or `.mcp.json` | `mcpServers` |
| OpenCode | `opencode.json` | `mcp` |
| Hermes Agent | `mcp.json` | `mcpServers` |

Example for Claude Code:
```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "uv",
      "args": ["run", "duckbrain"],
      "env": {
        "VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

Make sure `uv` is on your `PATH` and the working directory is the `duckbrain` project root. The `env` field in the config is all you need — no system-wide `VAULT_PATH` required.

## Tools

### `vault_info`

Get a summary of your vault's structure.

```
> vault_info()
→ {
    entities: 38,
    concepts: 38,
    sources: 33,
    synthesis: 9,
    available_tags: ["agent-memory", "ai", "duckdb", "mcp", ...],
    last_modified: "2026-05-28"
  }
```

No parameters. Useful for agents to discover what's in the vault before searching.

### `vault_search`

Full-text search over all wiki pages.

```
> vault_search("agent memory", kind="concept")
→ [
    { title: "Agent Memory Systems", kind: "concept",
      filepath: "wiki/concepts/agent-memory-systems.md",
      snippet: "A 6-level taxonomy of Claude Code memory approaches..." },
    ...
  ]
```

Parameters:
- `query` (required) — search text, BM25-ranked
- `kind` (optional) — filter to `entity`, `concept`, `source`, or `synthesis`
- `tags` (optional) — filter by tag substring matches

### `vault_write`

Create a new wiki page with correct frontmatter, auto-updating the index and log.

```
> vault_write(
    kind="concept",
    title="DuckDB FTS Memory",
    content="# DuckDB FTS Memory\n\nHow DuckDB serves as a memory layer...",
    tags=["agent-memory", "duckdb"]
  )
→ { success: true, filepath: "wiki/concepts/duckdb-fts-memory.md" }
```

This automatically:
1. Writes the markdown file to the correct wiki subdirectory
2. Appends an entry to `wiki/index.md` in the right section
3. Appends a dated entry to `wiki/log.md`

Parameters:
- `kind` (required) — `entity`, `concept`, `source`, or `synthesis`
- `title` (required) — page title
- `content` (required) — markdown body (without frontmatter)
- `tags` (required) — list of tag strings

## Vault Path

Set via the `VAULT_PATH` environment variable (or the `env` field in your MCP config — no need for both). Falls back to:

```
/mnt/c/Users/timhi/Documents/obsidian/brain-workbench
```

If you use WSL2 with your vault on Windows, set it to the WSL mount path (e.g., `/mnt/c/Users/you/Documents/obsidian/my-vault`).

## Performance

- First query builds the FTS index (~90 pages scans in under a second)
- Subsequent queries return in <200ms
- Write operations complete in <500ms
- Everything is in-memory — no persistent DuckDB database file
- Zero network calls, zero external services

## Limitations (v1)

- Read-only search covers `wiki/` only (not `daily/` or other vault files)
- No update or delete operations (only create)
- No vector embeddings or semantic search
- No file watchers — the FTS index is rebuilt from scratch on server restart
- No page deduplication check before writing

## License

MIT
