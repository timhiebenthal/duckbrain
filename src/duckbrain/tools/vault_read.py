"""MCP tool: vault_read — read a page by title."""

from pathlib import Path
from typing import Any

from duckbrain.scanner import scan_vault


def handle_vault_read(vault_path: str, title: str) -> dict[str, Any]:
    """Read a wiki or daily page by title.

    Scans the vault to find the page matching *title* (case-insensitive),
    then reads its full markdown content from disk.

    Args:
        vault_path: Root path of the Obsidian vault.
        title: Page title to look up.

    Returns:
        A dict with ``title``, ``kind``, ``filepath``, ``content``,
        ``tags``, ``created``, ``updated`` — or an ``error`` key if not found.
    """
    pages = scan_vault(vault_path)
    title_lower = title.strip().lower()

    for page in pages:
        if page.title.lower() == title_lower:
            filepath = Path(vault_path) / page.filepath
            if filepath.is_file():
                return {
                    "title": page.title,
                    "kind": page.kind,
                    "filepath": page.filepath,
                    "content": filepath.read_text(encoding="utf-8"),
                    "tags": page.tags,
                    "created": page.created,
                    "updated": page.updated,
                }

    return {"error": f"Page not found: {title}"}
