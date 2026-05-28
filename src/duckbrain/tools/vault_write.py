"""MCP tool: vault_write — create new wiki pages with index/log updates."""

from typing import Any

from duckbrain.writer import write_page


def handle_vault_write(
    vault_path: str,
    kind: str,
    title: str,
    content: str,
    tags: list[str],
) -> dict[str, Any]:
    """Create a new wiki page in the vault.

    Delegates to :func:`duckbrain.writer.write_page` which handles
    frontmatter generation, file creation, and index/log updates.

    Args:
        vault_path: Root path of the Obsidian vault.
        kind: Page kind — ``entity``, ``concept``, ``source``, or ``synthesis``.
        title: Page title.
        content: Markdown body content (without frontmatter).
        tags: List of tag strings.

    Returns:
        A dict with keys ``success`` (bool), ``filepath`` (str, relative),
        and ``warnings`` (list of str).
    """
    return write_page(vault_path, kind, title, content, tags)
