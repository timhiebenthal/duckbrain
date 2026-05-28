# DuckDB Memory MCP Server — Implementation Tasks

## Overview

Build a minimal MCP stdio server with 3 tools: `vault_info`, `vault_search`, `vault_write`. Python 3.11+, DuckDB FTS (in-memory, lazy), `uv` for deps. TDD throughout: write failing test → run to verify failure → implement → run to verify pass → commit.

**Package name**: `duckbrain`  
**Module layout**: `src/duckbrain/` with `scanner.py`, `indexer.py`, `writer.py`, `server.py`, `tools/*.py`

---

## SPRINT 1: Foundation — Scanner + Indexer

### Setup (sequential, no stream)

- [ ] **SP1-T0: Project scaffolding**
  - Run `uv init --lib duckbrain` in `/home/tim_ubuntu/git_repos/duckbrain`
  - Run `uv add duckdb "mcp[cli]" pyyaml` from the duckbrain dir (use `uv add` through bash, never manual pyproject.toml edits)
  - Create package structure:
    ```
    src/duckbrain/__init__.py
    src/duckbrain/scanner.py
    src/duckbrain/indexer.py
    src/duckbrain/writer.py
    src/duckbrain/server.py
    src/duckbrain/tools/__init__.py
    tests/__init__.py
    tests/conftest.py
    ```
  - In `src/duckbrain/__init__.py`: define shared dataclasses — `PageMetadata(filepath, title, kind, tags, body, created, updated)`, `SearchResult(title, kind, filepath, snippet, matched_tags)`, `WriteResult(success, filepath, warnings)`
  - In `tests/conftest.py`: create a `temp_vault` fixture that creates a temporary directory with `wiki/index.md` (with all 4 section headers: `## Entities`, `## Concepts`, `## Sources`, `## Synthesis`), `wiki/log.md` (empty), and a few sample entity/concept/synthesis markdown files with valid YAML frontmatter matching the AGENTS.md schema. Also add a fixture `sample_pages` that returns a list of `PageMetadata` objects.

- [ ] **SP1-T0-Verify**: `uv run python -c "from duckbrain import PageMetadata; print('OK')"` → prints OK

---

### Stream A: `scanner.py` — Vault file discovery + frontmatter parsing

- [x] **SP1-A1: Write failing test for `scan_vault`**
  - Create `tests/test_scanner.py`
  - Test: `test_scan_vault_finds_all_pages(temp_vault)` — asserts the fixture has 3+ pages; returns list of `PageMetadata` with correct `filepath`, `kind` inferred from parent dir (`wiki/entities/` → `"entity"`, `wiki/concepts/` → `"concept"`, etc.)
  - Test: `test_scan_vault_excludes_non_wiki(temp_vault)` — create a `wiki/junk.md` with no frontmatter in the temp vault, assert it's skipped (no `item-type` in frontmatter)
  - Test: `test_scan_vault_empty_dir(tmp_path)` — empty vault returns `[]`
  - **Run**: `uv run pytest tests/test_scanner.py -v` → FAIL (confirmed)

- [x] **SP1-A2: Implement `scan_vault(path) -> list[PageMetadata]`**
  - In `src/duckbrain/scanner.py`:
    - `scan_vault(vault_path: str) -> list[PageMetadata]`
    - Glob `wiki/{entities,concepts,sources,synthesis}/*.md` under vault_path
    - For each file: read content, call `parse_frontmatter(content)`
    - Return list of `PageMetadata` for files that have valid `item-type` frontmatter
  - **Run**: `uv run pytest tests/test_scanner.py -v` → PASS

- [x] **SP1-A3: Write failing test for `parse_frontmatter`**
  - In `tests/test_scanner.py`, add:
  - Test: `test_parse_frontmatter_with_yaml()` — markdown string with `---\ntitle: Foo\nitem-type: entity\ntags: [a, b]\n---\n# Foo\n\nBody text.` → returns `(dict, "body text")` with correct title, item-type, tags
  - Test: `test_parse_frontmatter_no_yaml()` — markdown with no `---` → returns `({}, full_content)`
  - Test: `test_parse_frontmatter_malformed_yaml()` — broken YAML → returns `({}, full_content)`, no crash
  - **Run**: `uv run pytest tests/test_scanner.py::test_parse_frontmatter* -v` → FAIL (confirmed)

- [x] **SP1-A4: Implement `parse_frontmatter(content) -> tuple[dict, str]`**
  - In `src/duckbrain/scanner.py`:
    - If content starts with `---`, split on second `---`, parse YAML block
    - Return `(frontmatter_dict, body_text)`
    - On YAML parse error: return `({}, content)` gracefully
  - **Run**: `uv run pytest tests/test_scanner.py -v` → all PASS

- [x] **SP1-A5: Implement `scanner.scan_daily(path)` (bonus if time)**
  - Same pattern but for `daily/*.md`. Not required for v1 tools but useful for future. Skip tests for now — add a placeholder function that returns `[]` and is called but not wired to any tool.

---

### Stream B: `indexer.py` — DuckDB FTS index build + search + stats

⚠️ Depends on: SP1-T0 (shared types defined)

- [x] **SP1-B1: Write failing test for `build_fts_index`**
  - `tests/test_indexer.py` created with 4 tests
  - **Run**: `uv run pytest tests/test_indexer.py -v` → FAIL (expected, `ImportError`)

- [x] **SP1-B2: Implement `build_fts_index(pages) -> duckdb.DuckDBPyConnection`**
  - Uses `PRAGMA create_fts_index('pages', 'filepath', 'title', 'tags', 'body')` with DuckDB 1.5.3 FTS API
  - Returns in-memory DuckDB connection with `pages` table and FTS index
  - **Run**: `uv run pytest tests/test_indexer.py -v` → PASS (4 tests)

- [x] **SP1-B3: Write failing test for `search`**
  - 5 tests added: basic, kind filter, tag filter, no match, result structure
  - Uses `fts_conn` fixture building index from `sample_pages`
  - **Run**: `uv run pytest tests/test_indexer.py -k search -v` → 5 FAIL (ParserException: `:query` syntax)

- [x] **SP1-B4: Implement `search(conn, query, kind, tags) -> list[dict]`**
  - Uses `fts_main_pages.match_bm25(filepath, $query)` subquery pattern
  - `$name` DuckDB named param syntax; kind/tag filters via SQL WHERE clauses
  - Body substring used as snippet (DuckDB FTS has no built-in `snippet()`)
  - **Run**: `uv run pytest tests/test_indexer.py -v` → all PASS (13 tests)

- [x] **SP1-B5: Write failing test for `get_stats`**
  - 4 tests: counts, tags, last_modified, empty
  - **Run**: `uv run pytest tests/test_indexer.py -k stats -v` → 4 PASS (implemented alongside search)

- [x] **SP1-B6: Implement `get_stats(conn) -> dict`**
  - SQL `GROUP BY kind` for counts, `SELECT DISTINCT tags` flattened + deduplicated, `MAX(updated)` for last_modified
  - **Run**: `uv run pytest tests/test_indexer.py -v` → 13 PASS; `uv run pytest` → 20 PASS (no regressions)

---

## SPRINT 2: Core Tools — vault_info, vault_search, vault_write

⚠️ All streams depend on SPRINT 1 being complete (scanner + indexer exist).

### Stream A: `tools/vault_info.py` — MCP tool for vault structure summary

- [x] **SP2-A1: Write failing test**
  - Create `tests/test_vault_info.py`
  - Use `temp_vault` fixture. Call scanner + indexer to build the index, then test the info output.
  - Test: `test_vault_info_returns_counts(temp_vault)` — scan vault, build index, call function that returns info dict; verify counts match actual files in temp_vault
  - Test: `test_vault_info_includes_tags(temp_vault)` — available_tags list is non-empty, matches tags in fixture pages
  - **Run**: `uv run pytest tests/test_vault_info.py -v` → FAIL (confirmed: 4 failed with ModuleNotFoundError)

- [x] **SP2-A2: Implement `vault_info` tool logic**
  - In `src/duckbrain/tools/vault_info.py`:
    - Function `handle_vault_info(vault_path: str) -> dict`:
      - Calls `scan_vault(vault_path)` → `build_fts_index(pages)` → `get_stats(conn)` → returns the dict
    - DuckDB connection is properly closed after get_stats to avoid resource leaks.
  - **Run**: `uv run pytest tests/test_vault_info.py -v` → PASS (4 passed)
  - **Run**: `uv run pytest` → 27 passed (no regressions)

---

### Stream B: `tools/vault_search.py` — MCP tool for FTS queries

- [x] **SP2-B1: Write failing test**
  - Create `tests/test_vault_search.py`
  - Use `temp_vault` fixture with pages containing "agent memory" in body text.
  - Test: `test_vault_search_finds_content(temp_vault)` — search for "memory" returns pages containing that word
  - Test: `test_vault_search_kind_filter(temp_vault)` — search with `kind="concept"` returns only concept-type results
  - Test: `test_vault_search_no_results(temp_vault)` — search for "zzzxyz" returns empty list
  - **Run**: `uv run pytest tests/test_vault_search.py -v` → FAIL (confirmed, ModuleNotFoundError)

- [x] **SP2-B2: Implement `vault_search` tool logic**
  - In `src/duckbrain/tools/vault_search.py`:
    - Function `handle_vault_search(vault_path, query, kind, tags) -> list[dict]`:
      - Calls `scan_vault(vault_path)` → `build_fts_index(pages)` → `search(conn, query, kind, tags)` → returns results
      - IMPORTANT: close the DuckDB connection after search to avoid resource leaks
  - **Run**: `uv run pytest tests/test_vault_search.py -v` → PASS (3/3)
  - **Run**: `uv run pytest` → 27 passed (no regressions)

---

### Stream C: `writer.py` + `tools/vault_write.py` — Page creation + index/log update

- [x] **SP2-C1: Write failing test for `slugify`**
  - In `tests/test_writer.py` (create it):
  - Test: `test_slugify_basic()` — `"Claude Mem"` → `"claude-mem"`
  - Test: `test_slugify_special_chars()` — `"BI's Second Unbundling"` → `"bis-second-unbundling"`
  - Test: `test_slugify_parens()` — `"Open Brain (OB1)"` → `"open-brain-ob1"`
  - Test: `test_slugify_multiple_spaces()` — `"Agent   Memory"` → `"agent-memory"`
  - **Run**: `uv run pytest tests/test_writer.py::test_slugify* -v` → FAIL

- [x] **SP2-C2: Implement `slugify(title) -> str`**
  - In `src/duckbrain/writer.py`:
    - lowercase, replace non-alphanumeric (except spaces) with `-`, collapse multiple dashes/spaces to single dash, strip leading/trailing dashes
  - **Run**: `uv run pytest tests/test_writer.py::test_slugify* -v` → PASS

- [x] **SP2-C3: Write failing test for `generate_frontmatter`**
  - In `tests/test_writer.py`:
  - Test: `test_generate_frontmatter_entity()` — `generate_frontmatter("entity", "Claude Mem", ["ai", "memory"])` → YAML block with title, item-type: entity, tags: [ai, memory], created, updated
  - Test: `test_generate_frontmatter_concept()` — kind "concept" → item-type: concept
  - Test: `test_generate_frontmatter_numeric_tag()` — tags with numbers handled correctly (tags are strings in YAML)
  - **Run**: `uv run pytest tests/test_writer.py::test_generate_frontmatter* -v` → FAIL

- [x] **SP2-C4: Implement `generate_frontmatter(kind, title, tags) -> str`**
  - In `src/duckbrain/writer.py`:
    - Build YAML dict with keys: title, item-type, tags, created, updated
    - Use today's date (YYYY-MM-DD) for created/updated
    - Wrap in `---\n...\n---`
    - Use `yaml.dump` with `default_flow_style=None` for readable output
  - **Run**: `uv run pytest tests/test_writer.py::test_generate_frontmatter* -v` → PASS

- [x] **SP2-C5: Write failing test for `write_page`**
  - In `tests/test_writer.py`:
  - Test: `test_write_page_creates_file(temp_vault)` — write entity "Test Entity" → `wiki/entities/test-entity.md` exists with correct frontmatter and content body
  - Test: `test_write_page_updates_index(temp_vault)` — after write, `wiki/index.md` contains `[[Test Entity]]` in the Entities section
  - Test: `test_write_page_updates_log(temp_vault)` — after write, `wiki/log.md` contains `## [2026-05-28] ingest | Test Entity`
  - Test: `test_write_page_concept_section(temp_vault)` — write concept "Test Concept" → index updated under `## Concepts` section, not Entities
  - Test: `test_write_page_synthesis_section(temp_vault)` — write synthesis page → index updated under `## Synthesis`
  - Test: `test_write_page_index_append_not_overwrite(temp_vault)` — existing index entries survive; new entry is appended
  - **Run**: `uv run pytest tests/test_writer.py::test_write_page* -v` → FAIL

- [x] **SP2-C6: Implement `write_page(vault_path, kind, title, content, tags) -> dict`**
  - In `src/duckbrain/writer.py`:
    1. Derive slug from title → filename
    2. Map kind to subdirectory: `entity` → `wiki/entities/`, `concept` → `wiki/concepts/`, `source` → `wiki/sources/`, `synthesis` → `wiki/synthesis/`
    3. Generate full markdown: `generate_frontmatter(kind, title, tags) + "\n\n" + content`
    4. Write file to disk
    5. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <title>\n- Created {kind}: {title}\n`
    6. Read `wiki/index.md`, find the correct `## ` section header (Entities/Concepts/Sources/Synthesis), find the next `## ` header or EOF, insert `- [[{title}]] - {title}\n` before it (use title as the one-line summary for v1)
    7. Return `{"success": True, "filepath": relative_path, "warnings": []}`
    - If any step after file write fails, include that as a warning in the result but don't roll back the file.
  - **Run**: `uv run pytest tests/test_writer.py -v` → all PASS

- [x] **SP2-C7: Implement `vault_write` tool (thin wrapper)**
  - In `src/duckbrain/tools/vault_write.py`:
    - Function `handle_vault_write(vault_path, kind, title, content, tags) -> dict`
    - Calls `write_page(vault_path, kind, title, content, tags)`
    - Register as MCP tool with schema: `kind` (required, enum), `title` (required str), `content` (required str), `tags` (required list of str)
  - **Run**: `uv run pytest tests/test_writer.py -v` → all still PASS (tool logic is tested inline via write_page tests)
  - **Commit**

---

## SPRINT 3: Integration — MCP Server + E2E + Error Handling

⚠️ All streams depend on SPRINT 2 being complete.

### Stream A: `server.py` — MCP stdio server entry point

- [x] **SP3-A1: Implement MCP server**
  - In `src/duckbrain/server.py`:
    - Create `mcp.Server` instance named "duckbrain"
    - Read `VAULT_PATH` from env
    - Lazy-load the FTS index: module-level `_conn: duckdb.DuckDBPyConnection | None = None` plus `_ensure_index()` that calls `scan_vault` → `build_fts_index` on first use
    - Register 3 tools with their schemas using `@server.tool()` decorator or equivalent `mcp` SDK API:
      - `vault_info` — no params
      - `vault_search` — `query: str`, `kind: Optional[str]`, `tags: Optional[list[str]]`
      - `vault_write` — `kind: str`, `title: str`, `content: str`, `tags: list[str]`
    - Each tool handler calls the corresponding `src/duckbrain/tools/*` function, passing the vault path
    - Run with stdio transport
  - **Run**: manual test — start server with `uv run python -m duckbrain.server`, verify it starts without error and listens on stdio

- [x] **SP3-A2: Add `pyproject.toml` entry point**
  - Add `[project.scripts]` section: `duckbrain = "duckbrain.server:main"` (via `uv add` or manual edit if needed — note: edit pyproject.toml manually since uv doesn't have a `scripts` subcommand, but keep it minimal)
  - Verify: `uv run duckbrain` starts the server

---

### Stream B: E2E tests — Full MCP client against the server

- [x] **SP3-B1: Write E2E test with temp vault**
  - Create `tests/test_e2e.py`
  - Use `temp_vault` fixture. Launch the MCP server as a subprocess with `VAULT_PATH` set to the temp vault path.
  - Test: `test_e2e_vault_info(temp_vault)` — send `vault_info` request via MCP client, verify response has counts matching temp vault
  - Test: `test_e2e_vault_search(temp_vault)` — send `vault_search("memory")`, verify results contain pages with "memory" in body
  - Test: `test_e2e_vault_write_and_search(temp_vault)` — write a new concept page via `vault_write`, then `vault_search` for it, verify it's found; also verify `wiki/index.md` and `wiki/log.md` on disk were updated
  - **Run**: `uv run pytest tests/test_e2e.py -v` → FAIL (expected — no server subprocess launch logic yet)

- [x] **SP3-B2: Implement E2E test infrastructure**
  - In `tests/conftest.py`, add `start_server(temp_vault_path) -> subprocess.Popen` and `stop_server(proc)` fixtures or helpers
  - Use `mcp` client library to connect via stdio to the subprocess
  - **Run**: `uv run pytest tests/test_e2e.py -v` → PASS (all 3 tests)

---

### Stream C: Error handling + edge cases

- [x] **SP3-C1: Write edge case tests**
  - Add to `tests/test_writer.py`:
  - Test: `test_write_page_log_failure(temp_vault, monkeypatch)` — make `wiki/log.md` read-only, write should still succeed (file created) with warning about log
  - Test: `test_write_page_index_failure(temp_vault, monkeypatch)` — make `wiki/index.md` read-only, write succeeds with warning
  - Test: `test_write_page_existing_index_preserved(temp_vault)` — after 3 writes to different sections, all 3 entries appear in index under correct sections, no corruption
  - Add to `tests/test_scanner.py`:
  - Test: `test_scan_vault_frontmatter_no_item_type(temp_vault)` — file with YAML but no `item-type` key → skipped
  - Test: `test_scan_vault_non_utf8(temp_vault)` — binary file in wiki/ → skipped gracefully
  - **Run**: `uv run pytest tests/test_scanner.py tests/test_writer.py -v` → FAIL

- [x] **SP3-C2: Implement edge case handling**
  - In `src/duckbrain/writer.py`:
    - Wrap log append in try/except, append warning to result on failure
    - Wrap index update in try/except, append warning to result on failure
  - In `src/duckbrain/scanner.py`:
    - Wrap file reads in try/except for encoding errors, skip unreadable files
    - Skip files without `item-type` in frontmatter (already handled in SP1-A2, verify)
  - **Run**: `uv run pytest tests/test_scanner.py tests/test_writer.py -v` → all PASS

- [x] **SP3-C3: Run full test suite**
  - `uv run pytest tests/ -v` → all tests PASS, zero failures
  - **Commit**

---

## Summary

### Sprint Overview

| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| 1 | Foundation | 7 (T0 + A1-A5 + B1-B6) | A (scanner), B (indexer) |
| 2 | Core Tools | 7 (A1-A2, B1-B2, C1-C7) | A (vault_info), B (vault_search), C (writer+vault_write) |
| 3 | Integration | 5 (A1-A2, B1-B2, C1-C3) | A (server), B (e2e), C (edge cases) |

### Total Effort
- **SPRINTS**: 3
- **STREAMS**: 8 (2 + 3 + 3)
- **Tasks**: 19

### File Map

| Module | File | Sprint |
|--------|------|--------|
| Shared types | `src/duckbrain/__init__.py` | 1 (setup) |
| Scanner | `src/duckbrain/scanner.py` | 1A |
| Indexer | `src/duckbrain/indexer.py` | 1B |
| Writer | `src/duckbrain/writer.py` | 2C |
| vault_info tool | `src/duckbrain/tools/vault_info.py` | 2A |
| vault_search tool | `src/duckbrain/tools/vault_search.py` | 2B |
| vault_write tool | `src/duckbrain/tools/vault_write.py` | 2C |
| MCP server | `src/duckbrain/server.py` | 3A |
| Test fixtures | `tests/conftest.py` | 1 (setup) |
| Scanner tests | `tests/test_scanner.py` | 1A |
| Indexer tests | `tests/test_indexer.py` | 1B |
| Writer tests | `tests/test_writer.py` | 2C |
| vault_info tests | `tests/test_vault_info.py` | 2A |
| vault_search tests | `tests/test_vault_search.py` | 2B |
| E2E tests | `tests/test_e2e.py` | 3B |

## Notes

- **TDD strictly**: every implementation task is preceded by a failing test task. No code without a failing test first.
- **Commit after each stream completes** (all tests pass for that stream).
- **No mocks for DuckDB** — use the real in-memory database. It's fast enough for unit tests.
- **No mocks for filesystem** — use `temp_vault` fixture with real directories and files. This guarantees the scanner/writer work against real disk.
- **9p mount performance**: the E2E test uses a temp dir on the native Linux filesystem. Real-world 9p perf must be tested manually against the actual vault. If DuckDB file scanning over 9p exceeds 3s for ~90 files, the FTS backend should be swapped to regex-based search instead of DuckDB (the scanner already provides the structured data — the indexer/search could be reimplemented without changing the rest of the system).
- **Left for v2**: `vault_read`, `vault_update`, `vault_delete`, vector embeddings, file watchers, wikilink resolution, HTTP transport, page deduplication, daily log scanning.

### Quality Standards
- No placeholders — every `[x]` means fully functional code
- Tests exercise real DuckDB and real filesystem (temp dirs)
- All frontmatter parsing and generation matches AGENTS.md schema
- Write path is filesystem-first, index/log are best-effort
