# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Vault context plugin v2** (`opencode/plugins/vault-context.ts`):
  - **Tiered injection**: tags always (~2K), session context (log + dailies)
    first-call-only (~4K). Cuts token overhead ~60% after first model call.
  - **Compaction improvements**: stronger journal nudge ("⚠️ Journal
    checkpoint"), resets session context for re-injection, compact snapshot
    (15 log lines not 30).
  - **Today/yesterday labeling**: daily notes get dedicated labeled sections
    instead of being buried in a batch.

## [0.3.1] - 2026-05-30

### Fixed

- **Daily note deduplication**: `_write_daily` now detects duplicate `## {title}`
  headings and merges in-place instead of appending a second copy.
- **`target_date` parameter**: `_write_daily`, `write_page`, and `handle_vault_write`
  accept optional `target_date: str | None = None` to write to a specific date's
  daily file instead of always targeting today.

## [0.3.0] - 2026-05-29

### Added

- **`vault_context` tool**: New MCP tool that bundles today's + yesterday's daily
  notes and keyword-based vault search into a single call. Reduces session-start
  round-trips from 3 to 1.
- **Session plugin** (`opencode/plugins/duckbrain-session-init.js`): OpenCode plugin
  that injects daily notes and the learnings ritual at `session.created` — no AI
  action needed. The learnings ritual moves out of AGENTS.md into the plugin payload.

## [0.2.0] - 2026-05-29

### Added

- **BM25 score exposure**: `vault_search` results now include a numeric `score` field
  from DuckDB's BM25 ranking, letting agents judge result relevance.
- **Context-aware snippets**: Snippets extracted from ~200 characters around the
  first query term match rather than the first 100 characters of body text.
  Snippet containment improved from 45% to 81%.
- **Result limit parameter**: `vault_search("memory", limit=10)` caps results,
  defaulting to 20. Pass `limit=None` for unlimited.
- **`matched_tags` populated**: The existing `matched_tags` field on search
  results is now filled with the tag filter used in the query.
- **Search quality benchmark**: `tests/benchmarks/search_quality.py` with
  `--label` flag for versioned snapshot archiving.
- **Marimo benchmark dashboard**: `uv run marimo edit notebooks/benchmark_dashboard.py`
  visualizes benchmark snapshots across versions.

### Changed

- **Page count bump**: test fixtures updated from 6 to 7 pages (added knowledge
  graph concept page with long body for snippet testing).
## [0.1.2] - 2026-05-29

### Added

- **OpenCode config templates** in `opencode/`: pre-response learning guard, trigger table, session rituals, `/journal` slash command, and example MCP config. Copy into `~/.config/opencode/` to enable automatic learning capture and session journaling.

### Fixed

- **MCP server name** renamed from `"duckbrain-vault"` to `"duckbrain"` to match the MCP config key users configure.

## [0.1.0] - 2026-05-28

### Added

- **vault_info**: MCP tool returning vault structure stats (page counts by kind, tags, last modified).
- **vault_search**: Full-text search over vault wiki pages via DuckDB BM25, with kind and tag filters, plus per-page created/updated dates.
- **vault_read**: Read a page by title or filepath, returning full markdown content.
- **vault_write**: Create wiki pages (entity, concept, source, synthesis) with YAML frontmatter and auto index/log updates. Append to daily notes (kind=daily).
- **DuckDB FTS index**: Lazy, in-memory full-text search built on first query — no persistent database.
- **Daily note scanning**: vault_search indexes daily/*.md files as kind=daily.
- **MCP stdio transport**: FastMCP server registered as `duckbrain` CLI command.
- **E2E tests**: Subprocess-based MCP client tests covering all 4 tools.
- **Error handling**: Graceful handling of log/index write failures, non-UTF8 files, missing sections.
