"""MCP tool: vault_search — search the vault using FTS."""

from typing import Any

from duckbrain.config import VaultConfig
from duckbrain.indexer import build_fts_index, search
from duckbrain.scanner import scan_vault


def handle_vault_search(
    vault_path: str,
    query: str,
    kind: str | None = None,
    tags: list[str] | None = None,
    limit: int | None = 20,
    config: VaultConfig | None = None,
) -> list[dict[str, Any]]:
    """Search the vault for pages matching *query* using full-text search."""
    pages = scan_vault(vault_path, config=config)
    conn = build_fts_index(pages)
    try:
        return search(conn, query, kind, tags, limit=limit)
    finally:
        conn.close()
