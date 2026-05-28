"""MCP tool: vault_read — read a page by title or filepath."""

from pathlib import Path
from typing import Any

from duckbrain.scanner import scan_vault


def handle_vault_read(
    vault_path: str,
    title: str | None = None,
    filepath: str | None = None,
) -> dict[str, Any]:
    """Read a wiki or daily page by title or filepath.

    When *filepath* is given (e.g. from :func:`vault_search` results),
    the file is read directly. When *title* is given, the vault is
    scanned to locate the matching page.

    Args:
        vault_path: Root path of the Obsidian vault.
        title: Page title to look up (case-insensitive).
        filepath: Relative path within the vault (e.g. ``wiki/concepts/foo.md``).

    Returns:
        A dict with ``title``, ``kind``, ``filepath``, ``content``,
        ``tags``, ``created``, ``updated`` — or an ``error`` key if not found.
    """
    # filepath takes priority — direct read, no scan needed
    if filepath:
        full_path = Path(vault_path) / filepath
        if not full_path.is_file():
            return {"error": f"File not found: {filepath}"}

        content = full_path.read_text(encoding="utf-8")
        # Try to extract title from frontmatter for metadata, but don't fail
        # if the file has no frontmatter (e.g. daily notes).
        title_from_file = filepath.rsplit("/", 1)[-1].removesuffix(".md")
        kind = "daily" if filepath.startswith("daily/") else "wiki"

        return {
            "title": title_from_file,
            "kind": kind,
            "filepath": filepath,
            "content": content,
            "tags": [],
            "created": "",
            "updated": "",
        }

    # title lookup — scan and find match
    if title:
        pages = scan_vault(vault_path)
        title_lower = title.strip().lower()

        for page in pages:
            if page.title.lower() == title_lower:
                full_path = Path(vault_path) / page.filepath
                if full_path.is_file():
                    return {
                        "title": page.title,
                        "kind": page.kind,
                        "filepath": page.filepath,
                        "content": full_path.read_text(encoding="utf-8"),
                        "tags": page.tags,
                        "created": page.created,
                        "updated": page.updated,
                    }

        return {"error": f"Page not found: {title}"}

    return {"error": "Provide either title or filepath"}
