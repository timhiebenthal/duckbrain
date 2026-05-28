# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
