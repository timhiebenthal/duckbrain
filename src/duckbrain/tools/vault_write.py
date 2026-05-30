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
    target_date: str | None = None,
) -> dict[str, Any]:
    """Create a new wiki page in the vault.

    When *config* is active, validates *kind* against configured kinds
    and includes a warning for unknown kinds.

    Args:
        vault_path: Root path of the Obsidian vault.
        kind: Page kind — ``entity``, ``concept``, ``source``, or ``synthesis``.
        title: Page title.
        content: Markdown body content (without frontmatter).
        tags: List of tag strings.
        config: Optional vault configuration for custom page kinds.
        target_date: Override target date for daily notes (``YYYY-MM-DD``).

    Returns:
        A dict with keys ``success`` (bool), ``filepath`` (str, relative),
        and ``warnings`` (list of str).
    """
    if config is not None:
        known_kinds = {p.kind for p in config.scan_patterns}
        if kind not in known_kinds:
            result = write_page(vault_path, kind, title, content, tags, config=config, target_date=target_date)
            result.setdefault("warnings", []).append(
                f"Unknown kind '{kind}' — not configured in scan patterns"
            )
            return result

    return write_page(vault_path, kind, title, content, tags, config=config, target_date=target_date)
