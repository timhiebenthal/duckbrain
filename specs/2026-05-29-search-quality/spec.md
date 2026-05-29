# Search Quality Improvements - Specification

## Overview

Improve the signal-to-noise ratio of `vault_search` results for AI agent callers.
The current implementation returns first-100-char snippets (often YAML frontmatter)
and discards the BM25 relevance score. Three targeted changes make search results
actionable without adding new dependencies or changing the FTS engine.

## Requirements

### Functional Requirements

1. **Context-aware snippets**: Snippets extracted from ~200 characters around the
   first occurrence of any query term in the body. If no term found verbatim
   (BM25 can match via stemming), fall back to body start.
2. **BM25 score exposed**: The `match_bm25` score already computed in SQL must be
   included in each result dict as `"score"`.
3. **Result limit parameter**: `search()` and `handle_vault_search()` accept an
   optional `limit` parameter (default 20). Results returned are capped at the
   top-N by BM25 score. `limit=None` preserves current behavior (all results).
4. **Snippet truncation indicator**: Snippets use `"…"` (U+2026) prefix/suffix
   when the match context doesn't start/end at the body boundary.

### Non-Functional Requirements

- **No new dependencies** — zero changes to `pyproject.toml`
- **No DB schema change** — FTS index and table structure unchanged
- **Backward compatible** — caller that ignores new `"score"` field still works;
  existing `SearchResult` dataclass gets new fields with sensible defaults
- **Testable** — all four improvements have explicit test coverage
- **Performance** — snippet extraction runs in Python O(|body| + |terms|) after
  DB query; no measurable regression for vaults < 1000 pages

## Scope

### In Scope

- Snippet extraction logic in `indexer.py` (`_extract_snippet` helper)
- Add `score` field to `SearchResult` dataclass in `__init__.py`
- Add `limit` parameter to `search()`, `handle_vault_search()`, and server tool
- Update `search()` to include `score` in result dicts and apply limit
- Update tests to cover new functionality (snippet context, score presence,
  limit behavior)
- Fix pre-existing mismatch: `SearchResult.matched_tags` field exists but is
  never populated by `search()` — populate it from actual tag match data

### Out of Scope

- Vector embeddings or semantic search (separate idea, deferred)
- Hybrid BM25+vector ranking
- Match highlighting in snippets (DuckDB FTS has no built-in highlighting)
- Persistent DuckDB database file
- Stemmer or stopword configuration changes (already adequate defaults)
- `matched_fields` tracking (title vs. body hit) — adds complexity for marginal
  gain; defer to a future spec if needed

## Approach

### Technical Approach

All changes live within the existing pipeline: `scan_vault → build_fts_index → search`.

**1. Snippet extraction** (`indexer.py`, new helper):

```
_extract_snippet(body, query, context=100) → str
```

Algorithm:
- Lowercase body, split query into terms
- Find position of first occurring term in body
- If found: extract `[pos - context, pos + context]` with `"…"` boundary markers
- If not found: fall back to `body[:context*2]` with trailing `"…"`
- Use `"…"` (U+2026 single-character ellipsis) as boundary marker

**2. Score exposure** (`indexer.py` `search()`):

SQL already selects `score` via `fts_main_pages.match_bm25` in the subquery but
the outer SELECT discards it. Add `p.score` to the outer `SELECT` and include
`round(score, 2)` in the result dict.

**3. Result limit** (`indexer.py` `search()`, `vault_search.py`, `server.py`):

Add `limit: int | None = 20` parameter. Apply `LIMIT` in SQL query. Pass `None`
(meaning no limit) to preserve existing behavior for callers that need all results.

**4. `SearchResult` dataclass** (`__init__.py`):

Add `score: float | None = None` field. The `matched_tags` field already exists
but was never populated — fix this by populating it with the tags that matched
the tag filter (not FTS-scored, but useful metadata).

### Files Changed

| File | Change |
|---|---|
| `src/duckbrain/__init__.py` | Add `score` field to `SearchResult` dataclass |
| `src/duckbrain/indexer.py` | Add `_extract_snippet()`, expose score, add limit |
| `src/duckbrain/tools/vault_search.py` | Pass through `limit` parameter |
| `src/duckbrain/server.py` | Add `limit` parameter to `vault_search` tool |
| `tests/test_indexer.py` | Add snippet, score, limit test cases |
| `tests/test_vault_search.py` | Add tool-level tests for new params |

### User Experience

The `vault_search` MCP tool gains a `limit` parameter:

```python
# Before (implicit all results, bad snippets)
vault_search("memory")

# After (top 20 by BM25, context-aware snippets, scores visible)
vault_search("memory", limit=10)
```

Result dict gains `"score"`:

```python
{
    "title": "Claude Mem",
    "kind": "entity",
    "filepath": "wiki/entities/claude-mem.md",
    "snippet": "…is an MCP-based memory plugin that provides persistent memory…",
    "score": 3.45,
    "created": "2026-05-28",
    "updated": "2026-05-28",
}
```

## Dependencies

- DuckDB `fts` extension (already in use)
- No new external dependencies

## Success Criteria

- `uv run pytest` passes with updated tests
- `uv run ruff check src/duckbrain/` — 0 errors
- `uv run ruff format --check src/duckbrain/` — all formatted
- `uv run mypy src/duckbrain/` — 0 errors
- Snippets for a query matching body text show context around match (not just
  body start)
- Search results include a numeric `score` field
- `limit=5` returns at most 5 results
- `limit=None` returns all results (preserves existing behavior)
- Existing vault search behavior (kind filter, tag filter, no-match) unchanged

## Notes

- DuckDB FTS has no built-in `snippet()` function — we implement it in Python.
  This is the same approach SQLite FTS5 callers use when they need custom
  snippet formatting.
- The `matched_tags` field on `SearchResult` currently exists in the dataclass
  but was never populated by `search()`. This spec includes populating it from
  the tag filter data as a piggyback fix.
- Stemming is already active (porter stemmer) — "memory" already matches
  "memories", "memorization". The quality gap was not recall but result
  presentation.
