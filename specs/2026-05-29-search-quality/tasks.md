# Search Quality Improvements — Implementation Tasks

## Overview

Improve `vault_search` results: context-aware snippets, BM25 score exposure, and
result limit parameter. No new dependencies. Four sequential sprints following
TDD (test first, then implementation).

Baseline benchmark: snippet containment **45.2%**, precision@5 **0.82**, recall@5
**0.96**, scores **not exposed**.

---

## Tasks

### SPRINT 1: Score exposure + matched_tags fix

Touches `__init__.py` (dataclass) and `indexer.py` (result dict). Single stream.

- [ ] **Write failing test** for score + matched_tags in results

  Add `test_search_result_includes_score` and `test_search_result_includes_matched_tags`
  to `tests/test_indexer.py`:

  ```python
  def test_search_result_includes_score(fts_conn) -> None:
      """Each result dict includes a numeric 'score' key."""
      from duckbrain.indexer import search

      results = search(fts_conn, "memory")
      assert len(results) >= 1
      for r in results:
          assert "score" in r, f"Missing 'score' in result keys: {set(r.keys())}"
          assert isinstance(r["score"], (int, float)), (
              f"score should be numeric, got {type(r['score'])}: {r['score']!r}"
          )


  def test_search_result_includes_matched_tags(fts_conn) -> None:
      """Each result dict includes a 'matched_tags' key (was already in
      SearchResult dataclass but never populated)."""
      from duckbrain.indexer import search

      results = search(fts_conn, "memory", tags=["agent-memory"])
      assert len(results) >= 1
      for r in results:
          assert "matched_tags" in r, (
              f"Missing 'matched_tags' in result keys: {set(r.keys())}"
          )
          assert isinstance(r["matched_tags"], list), (
              f"matched_tags should be a list, got {type(r['matched_tags'])}"
          )
  ```

  Also update `test_search_result_structure` expected keys to include `"score"`
  and `"matched_tags"`.

- [ ] **Run to verify failure**: `uv run pytest tests/test_indexer.py::test_search_result_includes_score tests/test_indexer.py::test_search_result_includes_matched_tags tests/test_indexer.py::test_search_result_structure -v` → 3 FAIL

- [ ] **Add `score` to SearchResult** in `src/duckbrain/__init__.py`:

  ```python
  @dataclass
  class SearchResult:
      title: str
      kind: str
      filepath: str
      snippet: str
      score: float | None = None          # ← new
      created: str = ""
      updated: str = ""
      matched_tags: list[str] = field(default_factory=list)
  ```

- [ ] **Expose `score` in `search()`** results in `src/duckbrain/indexer.py`:

  Add `p.score` to the outer `SELECT` clause and include `round(score, 2)` in
  the result dict. Populate `matched_tags` from the tag filter (the tags the
  caller asked to filter by, since FTS doesn't score per-tag individually).
  
  Key changes to `search()`:
  ```python
  # SQL: add p.score to outer SELECT
  sql = f"""
      SELECT p.title, p.kind, p.filepath, p.body, p.created, p.updated, p.score
      FROM ( ... ) p
      WHERE score IS NOT NULL{where_clause}
      ORDER BY score DESC
  """

  # Result dict: add score and matched_tags
  results.append({
      "title": title,
      "kind": kind_val,
      "filepath": filepath,
      "snippet": snippet,
      "score": round(score, 2),          # ← new
      "created": created,
      "updated": updated,
      "matched_tags": tags if tags else [], # ← populated
  })
  ```

- [ ] **Run to verify pass**: `uv run pytest tests/test_indexer.py -v` → all PASS;
  `uv run pytest` → all 17 existing tests still pass

- [ ] **Commit**: `feat: expose BM25 score and populate matched_tags in search results`

---

### SPRINT 2: Context-aware snippets

Touches `indexer.py` (new helper + wiring). Single stream.

- [ ] **Write failing test** for `_extract_snippet` in `tests/test_indexer.py`:

  ```python
  def test_extract_snippet_term_early() -> None:
      """Snippet shows context around first query term match."""
      from duckbrain.indexer import _extract_snippet
      body = "The quick brown fox jumps over the lazy dog. Memory is fascinating."
      snippet = _extract_snippet(body, "Memory")
      assert "fascinating" in snippet
      assert "…" not in snippet  # match is at body end, no suffix needed


  def test_extract_snippet_term_buried() -> None:
      """Snippet extracts context around a term deep in the body."""
      from duckbrain.indexer import _extract_snippet
      prefix = "Lorem ipsum dolor sit amet. " * 20  # ~500 chars of padding
      body = prefix + "The graph database stores relationships as first-class entities."
      snippet = _extract_snippet(body, "graph")
      assert "graph" in snippet.lower()
      assert snippet.startswith("…")
      assert snippet.endswith("…")


  def test_extract_snippet_no_match() -> None:
      """Fall back to body start when no query term found verbatim."""
      from duckbrain.indexer import _extract_snippet
      body = "This is a page about data modeling."
      snippet = _extract_snippet(body, "graph")
      assert snippet.startswith("This is a page")
      assert snippet.endswith("…")


  def test_extract_snippet_short_body() -> None:
      """Short body — no ellipsis needed."""
      from duckbrain.indexer import _extract_snippet
      body = "Short."
      snippet = _extract_snippet(body, "Short")
      assert "…" not in snippet


  def test_extract_snippet_multiple_terms() -> None:
      """First matching term wins for snippet position."""
      from duckbrain.indexer import _extract_snippet
      body = "Alpha beta gamma. Later: delta graph epsilon."
      snippet = _extract_snippet(body, "beta graph")
      assert "beta" in snippet.lower()  # "beta" appears before "graph"


  def test_search_uses_context_snippets(fts_conn) -> None:
      """search() results use _extract_snippet, not body[:100]."""
      from duckbrain.indexer import search
      # Knowledge Graph Architecture has "graph" at position ~535
      results = search(fts_conn, "graph")
      kg_result = [r for r in results if r["title"] == "Knowledge Graph Architecture"]
      assert len(kg_result) == 1
      snippet = kg_result[0]["snippet"]
      # Should show context around the matched term, not the body start
      assert "knowledge" in snippet.lower() or "graph" in snippet.lower()
      # Should NOT be the body opening ("This document explores...")
      assert "document explores" not in snippet.lower()
  ```

- [ ] **Run to verify failure**: `uv run pytest tests/test_indexer.py -k "extract_snippet or search_uses_context" -v` → 6 FAIL

- [ ] **Implement `_extract_snippet()`** in `src/duckbrain/indexer.py`:

  ```python
  def _extract_snippet(body: str, query: str, context: int = 100) -> str:
      """Extract ~context chars around first occurrence of any query term."""
      if not body or not query:
          return body

      body_lower = body.lower()
      best_pos = len(body)

      for term in query.lower().split():
          pos = body_lower.find(term)
          if pos != -1 and pos < best_pos:
              best_pos = pos

      if best_pos == len(body):
          # No verbatim match — fall back to body start
          if len(body) > context * 2:
              return body[: context * 2] + "…"
          return body

      start = max(0, best_pos - context)
      end = min(len(body), best_pos + context)
      snippet = body[start:end]

      prefix = "…" if start > 0 else ""
      suffix = "…" if end < len(body) else ""
      return f"{prefix}{snippet}{suffix}"
  ```

- [ ] **Wire `_extract_snippet` into `search()`** in `src/duckbrain/indexer.py`:

  Replace `snippet = body[:100] + "..." if len(body) > 100 else body`
  with `snippet = _extract_snippet(body, query)`.

- [ ] **Run to verify pass**: `uv run pytest tests/test_indexer.py -v` → all PASS;
  `uv run pytest` → all PASS

- [ ] **Commit**: `feat: context-aware snippet extraction around first query term match`

---

### SPRINT 3: Result limit parameter

Touches `indexer.py` (SQL), `vault_search.py` (passthrough), `server.py` (tool
signature). Single stream — changes cascade top-down.

- [ ] **Write failing test** for limit in `tests/test_indexer.py` and
  `tests/test_vault_search.py`:

  ```python
  # In test_indexer.py
  def test_search_limit(fts_conn) -> None:
      """search(limit=N) returns at most N results."""
      from duckbrain.indexer import search

      results = search(fts_conn, "memory", limit=2)
      assert len(results) <= 2


  def test_search_limit_none(fts_conn) -> None:
      """search(limit=None) returns all results (preserves old behavior)."""
      from duckbrain.indexer import search

      all_results = search(fts_conn, "memory")
      unlimited = search(fts_conn, "memory", limit=None)
      assert len(unlimited) == len(all_results)


  def test_search_default_limit(fts_conn) -> None:
      """search() without explicit limit uses default (20 or unlimited?).

      With 8 pages in our test dataset, no query returns >8 results,
      so the default limit of 20 should return all results.
      """
      from duckbrain.indexer import search

      results = search(fts_conn, "memory")
      assert len(results) >= 3  # At minimum we know 3 relevant pages exist
  ```

  ```python
  # In test_vault_search.py (add)
  def test_vault_search_limit(temp_vault: Path) -> None:
      """vault_search with limit returns at most N results."""
      from duckbrain.tools.vault_search import handle_vault_search

      results = handle_vault_search(str(temp_vault), "memory", limit=1)
      assert len(results) == 1


  def test_vault_search_limit_none(temp_vault: Path) -> None:
      """vault_search with limit=None returns all results."""
      from duckbrain.tools.vault_search import handle_vault_search

      all_results = handle_vault_search(str(temp_vault), "memory")
      unlimited = handle_vault_search(str(temp_vault), "memory", limit=None)
      assert len(unlimited) == len(all_results)
  ```

- [ ] **Run to verify failure**:

  ```
  uv run pytest tests/test_indexer.py::test_search_limit \
      tests/test_indexer.py::test_search_limit_none \
      tests/test_indexer.py::test_search_default_limit \
      tests/test_vault_search.py::test_vault_search_limit \
      tests/test_vault_search.py::test_vault_search_limit_none -v
  ```
  → 5 FAIL (TypeError: unexpected keyword argument 'limit')

- [ ] **Add `limit` to `search()`** in `src/duckbrain/indexer.py`:

  ```python
  def search(
      conn: duckdb.DuckDBPyConnection,
      query: str,
      kind: str | None = None,
      tags: list[str] | None = None,
      limit: int | None = 20,  # ← new parameter
  ) -> list[dict[str, Any]]:
  ```

  Add `LIMIT $limit` to SQL when limit is not None:

  ```python
  if limit is not None:
      sql += " LIMIT $limit"
      params["limit"] = limit
  ```

- [ ] **Add `limit` to `handle_vault_search()`** in `src/duckbrain/tools/vault_search.py`:

  ```python
  def handle_vault_search(
      vault_path: str,
      query: str,
      kind: str | None = None,
      tags: list[str] | None = None,
      limit: int | None = 20,  # ← new parameter
  ) -> list[dict[str, Any]]:
      ...
      return search(conn, query, kind, tags, limit=limit)
  ```

- [ ] **Add `limit` to server tool** in `src/duckbrain/server.py`:

  ```python
  @server.tool()
  def vault_search(
      query: str,
      kind: str | None = None,
      tags: list[str] | None = None,
      limit: int | None = 20,  # ← new parameter
  ) -> list[dict]:
      return handle_vault_search(vault_path, query, kind, tags, limit=limit)
  ```

- [ ] **Run to verify pass**: `uv run pytest tests/test_indexer.py tests/test_vault_search.py -v` → all PASS;
  `uv run pytest` → all PASS

- [ ] **Commit**: `feat: add limit parameter to search, vault_search, and server tool`

---

### SPRINT 4: Quality gates + benchmark delta

Verify everything together. Single stream.

- [ ] **Run full test suite**: `uv run pytest -v`
  → all 17 (existing) + ~13 (new) = ~30 tests PASS, 0 FAIL

- [ ] **Run linter**: `uv run ruff check src/duckbrain/`
  → 0 errors

- [ ] **Run formatter check**: `uv run ruff format --check src/duckbrain/`
  → "1 file already formatted" (or similar, no changes needed)

- [ ] **Run type checker**: `uv run mypy src/duckbrain/`
  → 0 errors

- [ ] **Run benchmark delta**:

  ```
  uv run python tests/benchmarks/search_quality.py
  ```
  
  Expected improvements vs. baseline:
  - Snippet containment: **45.2% → ≥90%** (context-aware extraction)
  - Score column: **N/A → numeric values** (score exposure)
  - P@5, R@5, MRR: **unchanged or slightly better** (limit=20 default
    matches current unlimited behavior for small dataset)

- [ ] **Update baseline**: copy `tests/benchmarks/baseline.json` →
  `tests/benchmarks/baseline.before.json`, then re-run benchmark to overwrite
  with new baseline.

- [ ] **Commit**: `chore: verify search quality improvements, update benchmark baseline`

---

## Summary

### Sprint Overview

| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| 1 | Score exposure + matched_tags | 5 | 1 |
| 2 | Context-aware snippets | 5 | 1 |
| 3 | Result limit parameter | 5 | 1 |
| 4 | Quality gates + benchmark | 7 | 1 |

### Total Effort

- SPRINTS: 4
- STREAMS: 4 (one per sprint, sequential)
- Tasks: 22
- Files changed: 6
- New tests: ~13

### Files Changed

| File | Sprint | What |
|---|---|---|
| `src/duckbrain/__init__.py` | 1 | `score` field on `SearchResult` |
| `src/duckbrain/indexer.py` | 1, 2, 3 | Score in results, `_extract_snippet()`, `limit` param |
| `src/duckbrain/tools/vault_search.py` | 3 | Pass through `limit` |
| `src/duckbrain/server.py` | 3 | `limit` in tool signature |
| `tests/test_indexer.py` | 1, 2, 3 | Score, matched_tags, snippet, limit tests |
| `tests/test_vault_search.py` | 3 | Tool-level limit tests |

## Notes

- **Why sequential, not parallel**: All changes converge on `indexer.py` and
  `tests/test_indexer.py`. Per the 1-file-1-stream rule, they must be sequential
  to avoid merge conflicts and ensure each TDD cycle completes cleanly.
- **`matched_tags` piggyback fix**: The `SearchResult` dataclass already has
  `matched_tags` but `search()` never populated it. SPRINT 1 populates it from
  the tag filter passed by the caller. This is metadata about *which* tags were
  used to filter, not which tags matched — useful for callers to understand why
  a result was included.
- **Default limit of 20**: Balances giving callers enough results without
  overwhelming them. For vaults with hundreds of pages, the unlimited behavior
  was a problem. `limit=None` preserves backward compatibility.
- **Snippet fallback**: When no query term is found verbatim in the body (BM25
  matched via stemming on title/tags), the snippet shows body start with
  trailing `"…"`. This is better than an empty snippet and clearly signals
  "match was not in the body."
- **Baseline migration**: Sprint 4 preserves the old baseline as
  `baseline.before.json` so you can diff the JSON to see exact metric changes.

### Quality Standards

- [x] No placeholders — all tasks have specific implementation detail
- [x] Complete integration — all 4 files wired together by Sprint 3
- [x] User-facing quality — snippets show context, scores inform decisions
- [x] TDD enforced — every sprint opens with a failing test
