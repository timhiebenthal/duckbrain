# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
