"""MCP tool: vault_write — create new wiki pages with index/log updates."""

from typing import Any

from duckbrain.config import VaultConfig
from duckbrain.writer import write_page


def handle_vault_write(
    vault_path: str,
    kind: str,
    title: str,
    content: str,
    tags: list[str],
    config: VaultConfig | None = None,
) -> dict[str, Any]:
    """Create a new wiki page in the vault.

    When *config* is active, validates *kind* against configured kinds
    and includes a warning for unknown kinds.
    """
    if config is not None:
        known_kinds = {p.kind for p in config.scan_patterns}
        if kind not in known_kinds:
            result = write_page(vault_path, kind, title, content, tags, config=config)
            result.setdefault("warnings", []).append(
                f"Unknown kind '{kind}' — not configured in scan patterns"
            )
            return result

    return write_page(vault_path, kind, title, content, tags, config=config)
