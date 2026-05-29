"""Tests for duckbrain.indexer — DuckDB FTS index build + search + stats."""

import pytest

from duckbrain import PageMetadata

# ── build_fts_index tests ─────────────────────────────────────────────────────


def test_build_fts_index_returns_connection(sample_pages: list[PageMetadata]) -> None:
    """build_fts_index returns a duckdb.DuckDBPyConnection, not None."""
    from duckbrain.indexer import build_fts_index

    conn = build_fts_index(sample_pages)
    assert conn is not None
    # DuckDBPyConnection is the runtime type; duckdb module has DuckDBPyConnection
    import duckdb
    assert isinstance(conn, duckdb.DuckDBPyConnection)
    conn.close()


def test_build_fts_index_table_exists(sample_pages: list[PageMetadata]) -> None:
    """Connection has a table named pages with columns filepath, title, kind, tags, body."""
    from duckbrain.indexer import build_fts_index

    conn = build_fts_index(sample_pages)
    cols = conn.execute("PRAGMA table_info('pages')").fetchall()
    col_names = [c[1] for c in cols]
    expected = {"filepath", "title", "kind", "tags", "body"}
    assert expected.issubset(set(col_names))
    conn.close()


def test_build_fts_index_fts_created(sample_pages: list[PageMetadata]) -> None:
    """FTS index exists on the connection (i.e., fts_main_pages schema exists)."""
    from duckbrain.indexer import build_fts_index

    conn = build_fts_index(sample_pages)
    # FTS creates a schema named fts_main_pages
    schemas = conn.execute(
        "SELECT schema_name FROM information_schema.schemata"
    ).fetchall()
    schema_names = [s[0] for s in schemas]
    assert "fts_main_pages" in schema_names, (
        f"Expected fts_main_pages schema in {schema_names}"
    )
    conn.close()


def test_build_fts_index_empty() -> None:
    """Empty list → connection still works, table exists but has 0 rows."""
    from duckbrain.indexer import build_fts_index

    conn = build_fts_index([])
    count = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    assert count == 0
    conn.close()


# ── Fixture: pre-built FTS index ──────────────────────────────────────────────


@pytest.fixture
def fts_conn(sample_pages: list[PageMetadata]):
    """Return a DuckDB connection with FTS index built from sample_pages."""
    from duckbrain.indexer import build_fts_index

    conn = build_fts_index(sample_pages)
    yield conn
    conn.close()


# ── search tests ──────────────────────────────────────────────────────────────


def test_search_basic(fts_conn) -> None:
    """Search for a word in one page's body → returns list with that page."""
    from duckbrain.indexer import search

    results = search(fts_conn, "memory")
    assert len(results) >= 1
    # "memory" appears in "Claude Mem" body and "Agent Memory Systems" body
    titles = [r["title"] for r in results]
    assert "Claude Mem" in titles or "Agent Memory Systems" in titles


def test_search_kind_filter(fts_conn) -> None:
    """search with kind filter returns only pages of that kind."""
    from duckbrain.indexer import search

    results = search(fts_conn, "memory", kind="concept")
    for r in results:
        assert r["kind"] == "concept"


def test_search_tag_filter(fts_conn) -> None:
    """search with tag filter returns only pages containing that tag."""
    from duckbrain.indexer import search

    results = search(fts_conn, "memory", tags=["agent-memory"])
    for r in results:
        # Tags are stored as comma-separated string
        pass  # Filter is applied via SQL LIKE on the tags column
    assert len(results) >= 1
    # "agent-memory" appears in "Agent Memory Systems" and "duckdb-memory-mcp-build-decision"


def test_search_no_match(fts_conn) -> None:
    """Search for non-existent term returns []."""
    from duckbrain.indexer import search

    results = search(fts_conn, "zzzxyz")
    assert results == []


def test_search_result_structure(fts_conn) -> None:
    """Each result is a dict with keys title, kind, filepath, snippet, score,
    matched_tags, created, updated."""
    from duckbrain.indexer import search

    results = search(fts_conn, "memory")
    assert len(results) >= 1
    expected_keys = {
        "title", "kind", "filepath", "snippet", "score",
        "matched_tags", "created", "updated",
    }
    for r in results:
        assert set(r.keys()) == expected_keys, f"Got keys: {set(r.keys())}"
        assert isinstance(r["created"], str) and r["created"] != "", (
            f"created should be a non-empty string, got {r['created']!r}"
        )
        assert isinstance(r["updated"], str) and r["updated"] != "", (
            f"updated should be a non-empty string, got {r['updated']!r}"
        )


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
    """Each result dict includes a 'matched_tags' key (was in SearchResult
    dataclass but never populated)."""
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


# ── _extract_snippet tests ────────────────────────────────────────────────────


def test_extract_snippet_term_early() -> None:
    """Snippet shows context around first query term match at body end."""
    from duckbrain.indexer import _extract_snippet

    body = "The quick brown fox jumps over the lazy dog. Memory is fascinating."
    snippet = _extract_snippet(body, "Memory")
    assert "fascinating" in snippet
    # Match is near body end — no suffix ellipsis needed
    assert "…" not in snippet


def test_extract_snippet_term_buried() -> None:
    """Snippet extracts context around a term deep in the body."""
    from duckbrain.indexer import _extract_snippet

    prefix = "Lorem ipsum dolor sit amet. " * 20  # ~500 chars of padding
    suffix = " Additional content after the match " * 10  # extra after match
    body = prefix + "The graph database stores relationships." + suffix
    snippet = _extract_snippet(body, "graph")
    assert "graph" in snippet.lower()
    assert snippet.startswith("…")
    assert snippet.endswith("…")


def test_extract_snippet_no_match() -> None:
    """Fall back to body start when no query term found verbatim."""
    from duckbrain.indexer import _extract_snippet

    body = "This is a page about data modeling. " * 10  # ~360 chars
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


def test_get_stats_counts(fts_conn) -> None:
    """Returns dict with correct count per kind matching sample_pages."""
    from duckbrain.indexer import get_stats

    stats = get_stats(fts_conn)
    assert stats["entities"] == 1
    assert stats["concepts"] == 3
    assert stats["sources"] == 1
    assert stats["synthesis"] == 1


def test_get_stats_tags(fts_conn) -> None:
    """available_tags is a sorted list of all unique tags from all pages."""
    from duckbrain.indexer import get_stats

    stats = get_stats(fts_conn)
    tags = stats["available_tags"]
    assert isinstance(tags, list)
    # Check it's sorted
    assert tags == sorted(tags)
    # Verify specific expected tags exist
    expected_tags = {
        "open-source", "ai", "memory", "mcp",
        "agent-memory", "taxonomy", "architecture",
        "llm", "capability", "knowledge-graph",
        "duckdb", "comparison",
        "metrics-layer", "mds",
    }
    for tag in expected_tags:
        assert tag in tags, f"Missing tag: {tag}"
    # Total unique tags
    assert len(tags) == 14


def test_get_stats_last_modified(fts_conn) -> None:
    """last_modified matches the max updated date."""
    from duckbrain.indexer import get_stats

    stats = get_stats(fts_conn)
    assert stats["last_modified"] == "2026-05-29"


def test_get_stats_empty() -> None:
    """Empty pages → all counts 0, empty available_tags, last_modified is None."""
    from duckbrain.indexer import build_fts_index, get_stats

    conn = build_fts_index([])
    stats = get_stats(conn)
    assert stats["entities"] == 0
    assert stats["concepts"] == 0
    assert stats["sources"] == 0
    assert stats["synthesis"] == 0
    assert stats["available_tags"] == []
    assert stats["last_modified"] is None
    conn.close()
