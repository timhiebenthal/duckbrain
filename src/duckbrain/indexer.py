"""DuckDB FTS index build, search, and stats for DuckBrain."""

from typing import Any

import duckdb

from duckbrain import PageMetadata


def _extract_snippet(body: str, query: str, context: int = 100) -> str:
    """Extract ~context chars around the first occurrence of any query term.

    If no term found verbatim (BM25 can match via stemming), falls back to
    the body start. Uses ``"…"`` (U+2026) as a boundary marker when the
    extracted context doesn't start/end at the body boundary.
    """
    if not body or not query:
        return body

    body_lower = body.lower()
    best_pos = len(body)

    for term in query.lower().split():
        pos = body_lower.find(term)
        if pos != -1 and pos < best_pos:
            best_pos = pos

    if best_pos == len(body):
        # No verbatim term match — fall back to body start
        if len(body) > context * 2:
            return body[: context * 2] + "…"
        return body

    start = max(0, best_pos - context)
    end = min(len(body), best_pos + context)
    snippet = body[start:end]

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(body) else ""
    return f"{prefix}{snippet}{suffix}"


def build_fts_index(pages: list[PageMetadata]) -> duckdb.DuckDBPyConnection:
    """Build a DuckDB in-memory FTS index from a list of PageMetadata.

    Creates an in-memory DuckDB connection, creates a ``pages`` table,
    inserts all pages, and builds an FTS index on title, tags, and body.
    Returns the connection (caller must close it).
    """
    conn = duckdb.connect(":memory:")

    # Load FTS extension
    conn.execute("INSTALL fts")
    conn.execute("LOAD fts")

    # Create the pages table
    conn.execute(
        "CREATE TABLE pages ("
        "  filepath VARCHAR,"
        "  title    VARCHAR,"
        "  kind     VARCHAR,"
        "  tags     VARCHAR,"
        "  body     VARCHAR,"
        "  created  VARCHAR,"
        "  updated  VARCHAR"
        ")"
    )

    # Insert all pages (tags joined as comma-separated string for FTS)
    for p in pages:
        conn.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                p.filepath,
                p.title,
                p.kind,
                ",".join(p.tags),
                p.body,
                p.created,
                p.updated,
            ],
        )

    # Build FTS index on title, tags, body — using filepath as the document id
    conn.execute("PRAGMA create_fts_index('pages', 'filepath', 'title', 'tags', 'body')")

    return conn


def search(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    kind: str | None = None,
    tags: list[str] | None = None,
    limit: int | None = 20,
) -> list[dict[str, Any]]:
    """Search the FTS index and return matching results.

    Parameters
    ----------
    conn:
        DuckDB connection with a built FTS index.
    query:
        Search text (used for BM25 matching).
    kind:
        Optional kind filter (e.g. ``"concept"``).
    tags:
        Optional list of tag substrings to filter by.
    limit:
        Maximum number of results to return. Pass ``None`` for all results.
        Defaults to 20.

    Returns
    -------
    list[dict]
        Each dict has keys ``title``, ``kind``, ``filepath``, ``snippet``,
        ``created``, ``updated``.
    """
    # Build the query dynamically.
    # The FTS match uses the fts_main_pages.match_bm25 function.
    conditions: list[str] = []
    params: dict[str, Any] = {"query": query}

    if kind is not None:
        conditions.append("p.kind = $kind")
        params["kind"] = kind

    if tags:
        tag_clauses: list[str] = []
        for i, tag in enumerate(tags):
            param = f"tag_{i}"
            tag_clauses.append(f"p.tags LIKE ${param}")
            params[param] = f"%{tag}%"
        conditions.append("(" + " OR ".join(tag_clauses) + ")")

    where_clause = ""
    if conditions:
        where_clause = " AND " + " AND ".join(conditions)

    sql = f"""
        SELECT p.title, p.kind, p.filepath, p.body, p.created, p.updated, p.score
        FROM (
            SELECT *, fts_main_pages.match_bm25(p.filepath, $query) AS score
            FROM pages p
        ) p
        WHERE score IS NOT NULL{where_clause}
        ORDER BY score DESC
    """

    if limit is not None:
        sql += " LIMIT $limit"
        params["limit"] = limit

    rows = conn.execute(sql, params).fetchall()

    results: list[dict[str, Any]] = []
    tag_list = tags if tags else []
    for row in rows:
        title, kind_val, filepath, body, created, updated, score = row
        snippet = _extract_snippet(body, query)
        results.append(
            {
                "title": title,
                "kind": kind_val,
                "filepath": filepath,
                "snippet": snippet,
                "score": round(score, 2),
                "created": created,
                "updated": updated,
                "matched_tags": tag_list,
            }
        )

    return results


def get_stats(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, Any]:
    """Get statistics from the indexed pages.

    Returns
    -------
    dict
        Keys: ``entities``, ``concepts``, ``sources``, ``synthesis``,
        ``daily``, ``available_tags``, ``last_modified``.
    """
    # Count by kind
    kind_counts: dict[str, int] = {
        "entity": 0,
        "concept": 0,
        "source": 0,
        "synthesis": 0,
        "daily": 0,
    }
    rows = conn.execute("SELECT kind, COUNT(*) FROM pages GROUP BY kind").fetchall()
    for kind_val, count in rows:
        kind_counts[kind_val] = count

    # Collect unique tags
    tag_rows = conn.execute("SELECT DISTINCT tags FROM pages").fetchall()
    all_tags: set[str] = set()
    for (tag_str,) in tag_rows:
        if tag_str:
            for t in tag_str.split(","):
                t_stripped = t.strip()
                if t_stripped:
                    all_tags.add(t_stripped)

    # Max updated date
    row = conn.execute("SELECT MAX(updated) FROM pages").fetchone()
    max_updated = row[0] if row else None
    last_modified: str | None = str(max_updated) if max_updated else None

    return {
        "entities": kind_counts["entity"],
        "concepts": kind_counts["concept"],
        "sources": kind_counts["source"],
        "synthesis": kind_counts["synthesis"],
        "daily": kind_counts["daily"],
        "available_tags": sorted(all_tags),
        "last_modified": last_modified,
    }
