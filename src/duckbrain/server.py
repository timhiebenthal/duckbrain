"""duckbrain MCP server — stdio transport."""

import os

from mcp.server.fastmcp import FastMCP

from duckbrain.tools.vault_info import handle_vault_info
from duckbrain.tools.vault_search import handle_vault_search
from duckbrain.tools.vault_write import handle_vault_write


def get_vault_path() -> str:
    """Return vault path from VAULT_PATH env var, with sensible default."""
    return os.environ.get(
        "VAULT_PATH",
        "/mnt/c/Users/timhi/Documents/obsidian/brain-workbench",
    )


def main() -> None:
    """Entry point: start MCP server on stdio."""
    vault_path = get_vault_path()
    server = FastMCP("duckbrain-vault")

    @server.tool()
    def vault_info() -> dict:
        """Get vault structure stats: page counts by kind, available tags, last modified date."""
        return handle_vault_info(vault_path)

    @server.tool()
    def vault_search(
        query: str,
        kind: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Full-text search over vault wiki pages. Returns ranked results with snippets."""
        return handle_vault_search(vault_path, query, kind, tags)

    @server.tool()
    def vault_write(kind: str, title: str, content: str, tags: list[str]) -> dict:
        """Create a new wiki page. Updates index.md and log.md automatically.

        Args:
            kind: entity | concept | source | synthesis
            title: Page title
            content: Markdown body (without frontmatter)
            tags: List of tag strings
        """
        return handle_vault_write(vault_path, kind, title, content, tags)

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
