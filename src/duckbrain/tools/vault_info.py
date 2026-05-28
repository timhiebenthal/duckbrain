"""MCP tool: vault_info — vault structure summary."""

from typing import Any

from duckbrain.indexer import build_fts_index, get_stats
from duckbrain.scanner import scan_vault


def handle_vault_info(vault_path: str) -> dict[str, Any]:
    """Return vault structure statistics.

    Scans the vault, builds an in-memory FTS index, and returns
    counts per kind (entities, concepts, sources, synthesis),
    the sorted list of all unique tags, and the last-modified date.

    Args:
        vault_path: Root path of the Obsidian vault.

    Returns:
        A dict with keys: ``entities``, ``concepts``, ``sources``,
        ``synthesis``, ``daily``, ``available_tags``, ``last_modified``.
    """
    pages = scan_vault(vault_path)
    conn = build_fts_index(pages)
    try:
        stats = get_stats(conn)
    finally:
        conn.close()
    return stats
