"""MCP tool: vault_info — vault structure summary."""

from typing import Any

from duckbrain.config import VaultConfig
from duckbrain.indexer import build_fts_index, get_stats
from duckbrain.scanner import scan_vault


def handle_vault_info(
    vault_path: str,
    config: VaultConfig | None = None,
) -> dict[str, Any]:
    """Return vault structure statistics.

    When *config* is provided, includes config status in output.
    """
    pages = scan_vault(vault_path, config=config)
    conn = build_fts_index(pages)
    try:
        # Only pass config to get_stats when user has a real config file.
        # Default config (from missing file) still uses old hardcoded plural keys.
        stats_config = config if (config and config.config_path) else None
        stats = get_stats(conn, config=stats_config)
    finally:
        conn.close()

    # Add config status
    if config is not None and config.config_path is not None:
        stats["config_active"] = True
        stats["config_file"] = config.config_path
        stats["config_kinds"] = [p.kind for p in config.scan_patterns]
    else:
        stats["config_active"] = False
        stats["config_kinds"] = ["entity", "concept", "source", "synthesis", "daily"]

    return stats
