# duckbrain

DuckDB-backed MCP memory server for Obsidian vaults. Gives AI coding agents structured read and write access to your personal wiki — with full-text search, frontmatter-aware indexing, and automatic index/log updates. Built on the principle that your vault filesystem should be the single source of truth, not a database hidden behind an API.

## What it solves

Existing agent memory tools (MemSearch, Open Brain, Mem0, Supermemory) treat memory as unstructured text blobs. If you maintain a [Karpathy-style LLM wiki](https://x.com/karpathy/status/1889054630119760374) in Obsidian with typed pages (entities, concepts, sources, synthesis), YAML frontmatter, tags, and wikilinks — none of those tools understand your vault's structure.

duckbrain fills that gap. It reads your vault as-is and writes new pages following your vault's schema, so your wiki stays a single source of truth on the filesystem.

## How it works

```
AI Agent (Claude Code / OpenCode / Hermes)
        │
        │ MCP stdio
        ▼
┌──────────────────────┐
│   duckbrain server   │
│                      │
│  vault_info   ──►    │──► DuckDB FTS (in-memory)
│  vault_search ──►    │
│  vault_read   ──►    │──► Filesystem reads
│  vault_write  ──►    │──► Filesystem writes
└──────────────────────┘
        │
        ▼
   Your Obsidian vault
   (plain markdown on disk)
```

- **Reads** your vault files directly — no index to sync, no watchers, no duplicate storage
- **Searches** via DuckDB full-text search (BM25 ranking), built lazily in-memory on the first query
- **Writes** new pages with correct YAML frontmatter, auto-updating your index and log

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Obsidian vault structured with a `wiki/` directory containing:
  - `wiki/entities/` — people, orgs, products, tools
  - `wiki/concepts/` — ideas, frameworks, theories
  - `wiki/sources/` — one summary per ingested source
  - `wiki/synthesis/` — cross-cutting analysis
  - `wiki/index.md` — page catalog with `## Entities`, `## Concepts`, `## Sources`, `## Synthesis` sections
  - `wiki/log.md` — append-only chronological record
- Pages should use YAML frontmatter: `title`, `item-type`, `tags`, `created`, `updated`

This follows the schema defined for [LLM wikis](https://x.com/karpathy/status/1889054630119760374). If your vault uses a different structure, duckbrain works with it — but index/log updates expect the section headers above.

## Quick Start

```bash
pip install duckbrain
```

That's it. Now connect your AI agent (see below) — you don't run duckbrain yourself, the agent spawns it as needed.

*(Optional: verify the install by running `duckbrain` — it'll fail with "VAULT_PATH not set", which confirms it's working.)*

### Installing from source (for contributors)

```bash
git clone https://github.com/timhiebenthal/duckbrain.git
cd duckbrain
uv sync         # installs project + dev dependencies in a virtual environment
```

This requires [uv](https://docs.astral.sh/uv/) (the Python package manager used for development). End users should use `pip install duckbrain` above.

*(Optional: to verify the install, run `VAULT_PATH="/path/to/your/vault" uv run duckbrain`. It will appear to hang — that's correct, it's waiting on stdio. Press Ctrl+C to stop.)*

## Connecting to Agents

MCP stdio transport means the agent spawns duckbrain as a child process when it starts. You don't need a separate terminal or a running server. Just add this to your MCP config:

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
| Cursor | `.cursor/mcp.json` | `mcpServers` |
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

> **Tip:** Instead of hardcoding the path in every config, set `VAULT_PATH` once in your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.config/fish/config.fish`) and reference it in the config with your agent's env-var syntax:
>
> - OpenCode: `"VAULT_PATH": "{env:VAULT_PATH}"`
> - Claude Code: `"VAULT_PATH": "${env:VAULT_PATH}"`

Make sure `uv` is on your `PATH`.

### Auto-Writing Session Learnings

There are two ways to make your agent write learnings to the vault: instructions (works everywhere) or hooks (automatic, agent-native).

#### Approach 1: Instructions (all agents)

Add this to the appropriate instructions file. The agent reads it on startup and follows it during the session. **Tested with OpenCode.**

**Claude Code** — add to `CLAUDE.md`:

```markdown
## Session Learnings

After debugging, diving into rabbit holes, or completing significant work,
save what you learned so you don't repeat mistakes:

- Use vault_write(kind="daily", title="...", content="...", tags=["..."])
  to append to today's daily note.
- For reusable knowledge, use vault_write(kind="concept", title="...",
  content="...", tags=["..."]) to create a wiki page.
```

**OpenCode** — add to your config's `instructions` field (`opencode.json`):

```json
"instructions": ["/path/to/duckbrain/LEARNINGS.md"]
```

**Cursor** — add to `.cursorrules`:

```markdown
## Session Learnings

After debugging or completing work, save learnings via duckbrain:
- vault_write(kind="daily", title="<summary>", content="<details>", tags=[])
- Use kind="concept" for reusable knowledge.
```

#### Approach 2: Hooks (automatic, no prompt engineering needed)

Hooks run shell commands at specific lifecycle points — no instructions needed, they fire deterministically. **⚠️ Not tested with duckbrain yet.**

**Claude Code** — supports a full [hooks system](https://code.claude.com/docs/en/hooks) including `SessionEnd` (fires when a session terminates). Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "type": "command",
        "command": "duckbrain-save-session --transcript-from-stdin"
      }
    ]
  }
}
```

The `SessionEnd` hook receives the full transcript on stdin. A wrapper script could pipe it through an LLM to extract learnings, then call `vault_write`. See [`agent-memory-mcp`](https://github.com/ipiton/agent-memory-mcp) for a production example of this pattern.

**Cursor** — supports [hooks](https://cursor.com/docs/hooks.md) including `sessionEnd`, `postToolUse`, and `stop` via `.cursor/hooks.json`. However, `sessionEnd` is **not available in cloud agents** (local IDE only), and MCP execution hooks (`beforeMCPExecution`/`afterMCPExecution`) are **not yet wired for cloud agents**. Usable for local development, not for cloud-based Cursor sessions.

**.cursor/hooks.json** (local IDE only):
```json
{
  "hooks": {
    "stop": [
      {
        "type": "command",
        "command": "duckbrain-save-session --reason stop"
      }
    ]
  }
}
```

### How It Works

During a session, the agent encounters a problem, debugs it, and resolves it:

```
> vault_search("duckbrain daily write")
> vault_read(filepath="wiki/...")

Agent debugs, fixes, learns something...

> vault_write(
    kind="daily",
    title="vault_write daily kind doesn't support filepath-based reads",
    content="When vault_search returns filepaths, the agent may try to Read files
    directly. vault_read should accept filepath as well as title to close this gap.",
    tags=["duckbrain", "debugging", "learned"]
  )
```

The learning is now in `daily/2026-05-28.md`. Tomorrow when you ask "how do I read vault pages by path?", the agent searches the vault, finds your note, and recalls the solution.

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
- `kind` (optional) — filter to `entity`, `concept`, `source`, `synthesis`, or `daily`
- `tags` (optional) — filter by tag substring matches

### `vault_read`

Read a page by title or filepath. Returns full markdown content with metadata.

```
> vault_read(title="Agent Memory Systems")
→ {
    title: "Agent Memory Systems", kind: "concept",
    filepath: "wiki/concepts/agent-memory-systems.md",
    content: "# Agent Memory Systems\n\nA 6-level taxonomy...",
    tags: ["agent-memory", "taxonomy", "ai"],
    created: "2026-05-28", updated: "2026-05-28"
  }
```

Parameters:
- `title` (optional) — page title to look up (case-insensitive)
- `filepath` (optional) — relative path from vault_search results (e.g. `wiki/concepts/foo.md`)

Use after `vault_search` to get full page content. Pass `filepath` from search results directly.

### `vault_write`

Create a new wiki page or append to today's daily note, with automatic index and log updates.

```
> vault_write(
    kind="concept",
    title="DuckDB FTS Memory",
    content="# DuckDB FTS Memory\n\nHow DuckDB serves as a memory layer...",
    tags=["agent-memory", "duckdb"]
  )
→ { success: true, filepath: "wiki/concepts/duckdb-fts-memory.md" }
```

For daily notes (session learnings, debugging logs):
```
> vault_write(
    kind="daily",
    title="Debugging vault_read filepath",
    content="When search returns filepaths, agents try to Read files directly.",
    tags=["duckbrain", "debugging"]
  )
→ { success: true, filepath: "daily/2026-05-28.md" }
```

For wiki pages (entity|concept|source|synthesis), this automatically:
1. Writes the markdown file to the correct wiki subdirectory
2. Generates YAML frontmatter with title, item-type, tags, dates
3. Appends an entry to `wiki/index.md` in the right section
4. Appends a dated entry to `wiki/log.md`

For daily notes, this automatically:
1. Appends to `daily/YYYY-MM-DD.md` (creates the file if today's doesn't exist yet)
2. No YAML frontmatter — just a `## heading` + content
3. Does NOT update index.md (daily notes aren't wiki pages)
4. Appends a dated entry to `wiki/log.md`

Parameters:
- `kind` (required) — `entity`, `concept`, `source`, `synthesis`, or `daily`
- `title` (required) — page title (or section heading for daily entries)
- `content` (required) — markdown body (without frontmatter)
- `tags` (required) — list of tag strings

## Vault Path

Set via the `VAULT_PATH` environment variable (or the `env` field in your MCP config — no need for both). 

For local development, copy `.env.example` to `.env` and set your path:

```
VAULT_PATH=/path/to/your/obsidian/vault
```

If you use WSL2 with your vault on Windows, set it to the WSL mount path (e.g., `/mnt/c/Users/you/Documents/obsidian/my-vault`).

## Performance

- First query builds the FTS index (~90 pages scans in under a second)
- Subsequent queries return in <200ms
- Write operations complete in <500ms
- Everything is in-memory — no persistent DuckDB database file
- Zero network calls, zero external services

## Limitations (v1)

- No update or delete operations (only create)
- No vector embeddings or semantic search (see [abbreviation expansion](specs/2026-05-28-abbreviation-expansion/spec.md) for planned FTS improvements)
- No file watchers — the FTS index is rebuilt from scratch on server restart
- No page deduplication check before writing

## Inspirations

This project stands on the shoulders of several ideas and tools:

- **[Andrej Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — the idea that a personal markdown wiki, co-maintained by humans and AI agents, compounds into a persistent knowledge base. The vault schema (entities, concepts, sources, synthesis, daily log) is directly inspired by this.
- **[DuckDB](https://duckdb.org/)** — the embedded analytical database that makes full-text search over flat files viable without a server, index sync, or persistent storage. The decision to use in-memory FTS instead of a vector database was a deliberate trade-off for simplicity.
- **[Obsidian](https://obsidian.md/)** — the local-first, markdown-native note-taking tool that treats your files as the truth. duckbrain exists because Obsidian vaults deserve tooling that respects the filesystem.
- **[MemSearch](https://github.com/zilliztech/memsearch)** and **[Open Brain (OB1)](https://github.com/NateBJones-Projects/OB1)** — early experiments in cross-tool agent memory that demonstrated the *need* for structured vault write-back while choosing different architectures. Their strengths and gaps directly informed duckbrain's design.
- **[Agent Memory Systems (6-level taxonomy)](https://www.youtube.com/watch?v=UHVFcUzAGlM)** — Simon Scrapes' comprehensive comparison of Claude Code memory approaches provided the framework for understanding where duckbrain fits in the ecosystem (Level 6: cross-tool MCP with dedicated server).
- **[trellis-datamodel](https://github.com/timhiebenthal/trellis-datamodel)** — the same author's data modeling tool whose CI/CD patterns (trusted PyPI publishing, version-diff release detection, Keep a Changelog) were borrowed for this project's repository readiness.

The core decision — **build, don't integrate** — came from a [structured comparison](https://github.com/timhiebenthal/duckbrain/blob/main/specs/2026-05-28-duckdb-memory-mcp/spec.md) of 7 existing tools. All failed on one requirement: vault schema-aware write-back. Rather than fork or extend, duckbrain started from first principles: what's the simplest thing that gives agents structured read/write access to an Obsidian vault? The answer was DuckDB + MCP + ~500 lines of Python.

## License

MIT
