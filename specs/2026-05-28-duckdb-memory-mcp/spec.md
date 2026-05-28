# DuckDB Memory MCP Server — Specification

## Overview

A minimal MCP server that gives AI coding agents (Hermes Agent, OpenCode, Claude Code) structured read and write access to an Obsidian vault. Uses DuckDB full-text search over markdown files for retrieval, and filesystem writes for content creation. Agents search the vault and create new wiki pages with correct YAML frontmatter, auto-updating the index and log.

**Why**: Existing agent memory tools (MemSearch, Open Brain, Mem0, Supermemory) treat memory as unstructured text blobs. None understand that this vault has typed pages (entities, concepts, sources, synthesis) with YAML frontmatter, tags, wikilinks, and an append-only log. This server fills that gap.

**Reference**: [[duckdb-memory-mcp-build-decision]], Vault [[AGENTS.md]] schema.

## Requirements

### Functional Requirements

- **FR-1**: `vault_search` tool — Accepts `query` (required), `tags` (optional list), `kind` (optional: entity|concept|source|synthesis). Returns ranked results with title, kind, tag matches, and a relevance snippet from the body.
- **FR-2**: `vault_write` tool — Accepts `kind` (entity|concept|source|synthesis), `title`, `content` (markdown body), `tags` (list). Creates a new markdown file in the correct wiki subdirectory with YAML frontmatter.
- **FR-3**: On `vault_write`, auto-append a dated entry to `wiki/log.md` describing the operation.
- **FR-4**: On `vault_write`, auto-update `wiki/index.md` by appending a new entry in the correct section (Entities, Concepts, Sources, or Synthesis).
- **FR-3**: `vault_info` tool — Returns vault structure summary: page counts by kind (`entities`, `concepts`, `sources`, `synthesis`), list of all unique tags in use, and last modified date across the wiki. Uses the same in-memory data loaded for FTS.
- **FR-5**: DuckDB FTS index over all `wiki/**/*.md` files, built lazily (in-memory) on the first `vault_search` or `vault_info` call. Subsequent calls reuse the in-memory index.
- **FR-6**: YAML frontmatter parsing — extract `title`, `item-type`, `tags`, `sources`, `created`, `updated` from each page for FTS indexing and filtering.
- **FR-7**: YAML frontmatter generation — for `vault_write`, produce correct frontmatter with `title`, `item-type`, `tags`, `created` (today's date), `updated` (today's date).
- **FR-8**: MCP stdio transport — the server speaks the Model Context Protocol over stdin/stdout.
- **FR-9**: Vault path is configurable — passed via environment variable `VAULT_PATH`.

### Non-Functional Requirements

- **NFR-1**: FTS query response <2s (including first-query index build). Subsequent queries <200ms.
- **NFR-2**: Write operations complete in <1s for file + index + log update.
- **NFR-3**: Zero external services, databases, or network calls. Python stdlib + DuckDB only.
- **NFR-4**: Writes are filesystem-first — the markdown file is the source of truth. If index/log update fails, the file is still created; a warning is logged, and the next agent-driven lint can detect index drift.
- **NFR-5**: Reads are non-destructive — the server never modifies the vault filesystem except through `vault_write`.

## Scope

### In Scope

- `vault_search` with DuckDB FTS over vault/wiki/**/\*.md
- `vault_info` returning vault structure stats (counts, tags, last modified)
- `vault_write` creating entity, concept, source, or synthesis pages
- Auto-update of `wiki/index.md` and `wiki/log.md` on write
- YAML frontmatter parsing and generation per AGENTS.md schema
- Lazy in-memory FTS index (no persistent index file)
- MCP stdio transport
- Python project with `uv` for dependency management (DuckDB, `mcp` library)
- Page slug derivation from title (lowercase, dashes, no special chars)

### Out of Scope (v1)

- `vault_read`, `vault_update`, `vault_delete` tools
- Vector embeddings or semantic search (MemSearch integration deferred to v2)
- File watchers or auto-refresh of the FTS index
- Wikilink resolution / graph navigation
- Write error retries (agent handles retry)
- HTTP/SSE transport
- Fact extraction or automatic content generation
- Temporal decay or relevance scoring beyond FTS ranking
- Page deduplication (checking if a page with the same title already exists)
- Daily log files (`daily/`) — FTS covers `wiki/` only

## Approach

### Technical Approach

**Language & Dependencies**

- Python 3.11+ with `uv` for package management
- `duckdb` — embedded OLAP database, used only for FTS
- `mcp` — Python MCP SDK for the stdio server

**Architecture**

```
Agent (OpenCode/Hermes/Claude Code)
        │
        │ MCP stdio
        ▼
┌──────────────────────────────┐
│     MCP Server (Python)      │
│                              │
│  vault_search ──► DuckDB     │
│  vault_info   ──► DuckDB     │
│  vault_write  ──► filesystem │
└──────────────────────────────┘
        │                    │
        │ DuckDB FTS         │ file write
        ▼                    ▼
   /vault/wiki/         /vault/wiki/
   (read only)          (write)
```

**FTS Strategy: Lazy In-Memory Index**

1. Server starts. No DuckDB work happens.
2. First `vault_search` or `vault_info` call triggers index build:
   - Glob all `*.md` files under `wiki/entities/`, `wiki/concepts/`, `wiki/sources/`, `wiki/synthesis/`
   - For each file: extract YAML frontmatter + body text
   - Create DuckDB in-memory table with columns: `filepath`, `title`, `kind`, `tags` (as text), `body`
   - Create DuckDB FTS index on `title`, `tags`, `body`
3. Execute the FTS query.
4. Subsequent `vault_search` calls use the in-memory index directly.
5. `vault_write` does NOT rebuild the index (writes are visible to the agent immediately via filesystem; the FTS index will pick up the new page on the next search after a server restart, or on an explicit re-index tool in v2).

**Write Strategy: File-First, Append-Then-Verify**

```
vault_write("entity", "Claude Mem", "# Claude Mem\n\n...", ["ai", "memory"])
  │
  ├─► 1. Derive filename: wiki/entities/claude-mem.md
  ├─► 2. Generate frontmatter + body
  ├─► 3. Write file to disk
  ├─► 4. Append log entry to wiki/log.md
  ├─► 5. Append index entry to wiki/index.md (right section)
  └─► 6. Return success (or partial success with warnings)
```

If steps 4 or 5 fail, the file still exists on disk. The server returns success with a warning string describing what failed. The agent or user can run a lint/audit to fix index drift.

**Frontmatter Schema per Kind**

| Field | entity | concept | source | synthesis |
|-------|--------|---------|--------|-----------|
| `title` | page title | page title | page title | page title |
| `item-type` | "entity" | "concept" | "source" | "synthesis" |
| `tags` | user-provided list | user-provided list | user-provided list | user-provided list |
| `sources` | — | — | — | — |
| `created` | today's date | today's date | today's date | today's date |
| `updated` | today's date | today's date | today's date | today's date |

Note: sources and concepts do not include a `sources` field in v1. Entities optionally can if provided, but the write API doesn't accept it in v1 (only tags and content).

**Slug Derivation**

Title → filename: lowercase, replace spaces with dashes, strip non-alphanumeric (keep dashes). Append `.md`.

Examples:
- `"Claude Mem"` → `claude-mem.md`
- `"Agent Memory Systems"` → `agent-memory-systems.md`
- `"BI's Second Unbundling"` → `bis-second-unbundling.md`

**Index.md Update Format**

Each section has entries as bullet lists: `- [[Page Name]] - One-line summary`. The server appends a new entry line at the end of the correct `## Entities / ## Concepts / ## Sources / ## Synthesis` section. It identifies the section by `## ` header marker, then inserts before the next `## ` header or end of file.

**Log.md Update Format**

Appended entry: `## [YYYY-MM-DD] ingest | <title>` — follows the existing log format defined in AGENTS.md.

### User Experience

The end user is an AI agent calling MCP tools. Example interactions:

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

> vault_search("agent memory systems")
→ [
    { title: "Agent Memory Systems", kind: "concept", snippet: "6-level taxonomy..." },
    { title: "Claude Mem", kind: "entity", snippet: "MCP-based memory plugin..." },
    { title: "duckdb-memory-mcp-build-decision", kind: "synthesis", snippet: "Build minimal..." }
  ]

> vault_search("agent memory", kind="concept")
→ [
    { title: "Agent Memory Systems", kind: "concept", snippet: "..." }
  ]

> vault_write("concept", "DuckDB FTS Memory", "# DuckDB FTS Memory\n\n...", ["agent-memory", "duckdb"])
→ { success: true, file: "wiki/concepts/duckdb-fts-memory.md" }
```

## Dependencies

### Prerequisites
- Python 3.11+ with `uv` installed
- Vault filesystem accessible at configured `VAULT_PATH` (default: WSL 9p mount)

### External Dependencies
- `duckdb` — embedded database, no server process
- `mcp` — Python MCP SDK for stdio transport and tool registration

### Related Systems
- Obsidian vault (configurable via `VAULT_PATH`)
- Hermes Agent, OpenCode, Claude Code — all clients via MCP
- `wiki/AGENTS.md` — defines the vault schema this server must match
- `wiki/index.md` and `wiki/log.md` — special files the server updates

## Success Criteria

1. **Agent can discover the vault**: `vault_info()` returns accurate counts, tags, and last modified date.
2. **Agent can search the vault**: `vault_search("FTS")` returns relevant wiki pages with titles, kinds, and snippets.
3. **Agent can write a new page**: `vault_write("concept", "Test Concept", "# Test\n\nBody content.", ["test"])` creates `wiki/concepts/test-concept.md` with correct frontmatter.
4. **Index is auto-updated**: After a write, `wiki/index.md` includes the new page in the correct section.
5. **Log is auto-appended**: After a write, `wiki/log.md` has a new dated entry.
6. **FTS is lazy and fast**: First search builds the index, subsequent searches are sub-200ms.

## Notes

- The WSL 9p mount performance for DuckDB file scanning is unmeasured. If startup scan latency exceeds ~3s for the current vault size (~90 wiki pages), switch to a simpler approach: glob + Python `re` for FTS-like search, skip DuckDB entirely. This should be benchmarked before building the FTS component, or the build should be structured so the FTS backend is swappable.
- Write consistency is eventual: the file is created first; index/log updates may be slightly behind, but the filesystem is always the source of truth.
- This spec intentionally excludes any persistent DuckDB database file. Everything is in-memory, rebuilt from the filesystem. This avoids cache invalidation entirely.
- Vault structure (wiki/ subdirectories, frontmatter fields, index/log format) is currently hardcoded to match the `brain-workbench` vault per AGENTS.md. A future `vault_init` tool could auto-detect vault structure and make these configurable for non-tim vaults — but not until v1 is proven feasible.
