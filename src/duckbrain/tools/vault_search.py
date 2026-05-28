"""MCP tool: vault_search — search the vault using FTS."""

from typing import Any

from duckbrain.indexer import build_fts_index, search
from duckbrain.scanner import scan_vault


def handle_vault_search(
    vault_path: str,
    query: str,
    kind: str | None = None,
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search the vault for pages matching *query* using full-text search.

    Parameters
    ----------
    vault_path:
        Root path of the Obsidian vault.
    query:
        Search text (used for BM25 matching on title, tags, and body).
    kind:
        Optional kind filter (e.g. ``"concept"``).
    tags:
        Optional list of tag substrings to filter by.

    Returns
    -------
    list[dict]
        Each dict has keys ``title``, ``kind``, ``filepath``, ``snippet``.
    """
    pages = scan_vault(vault_path)
    conn = build_fts_index(pages)
    try:
        return search(conn, query, kind, tags)
    finally:
        conn.close()
