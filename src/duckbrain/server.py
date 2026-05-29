"""DuckBrain MCP server — stdio transport."""

import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import Icon

from duckbrain.tools.vault_info import handle_vault_info
from duckbrain.tools.vault_read import handle_vault_read
from duckbrain.tools.vault_search import handle_vault_search
from duckbrain.tools.vault_write import handle_vault_write

# Load .env from project root (or current working directory).
load_dotenv()

# Handle the case where MCP config sets VAULT_PATH to empty string
# (e.g. OpenCode's {env:VAULT_PATH} when the var is not in shell),
# which blocks load_dotenv from loading the .env value.
if os.environ.get("VAULT_PATH", "").strip() == "":
    os.environ.pop("VAULT_PATH", None)
    load_dotenv()


def get_vault_path() -> str:
    """Return vault path from VAULT_PATH env var."""
    vault_path = os.environ.get("VAULT_PATH")
    if not vault_path:
        print(
            "VAULT_PATH is empty or not set.\n"
            "\n"
            "Fix: copy .env.example → .env and set VAULT_PATH to your vault.\n"
            "    cp .env.example .env\n"
            "    # edit .env with your vault path\n"
            "\n"
            "If using {env:VAULT_PATH} in MCP config, either:\n"
            "  a) Set VAULT_PATH in your shell (~/.bashrc, ~/.zshrc etc.)\n"
            "  b) Remove the 'environment' block from the MCP config so .env is used",
            file=sys.stderr,
        )
        sys.exit(1)
    return vault_path


def main() -> None:
    """Entry point: start MCP server on stdio."""
    vault_path = get_vault_path()
    server = FastMCP(
        "duckbrain",
        icons=[
            Icon(
                src="https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/logo/favicon.png",
                mimeType="image/png",
                sizes=["64x64"],
            )
        ],
    )

    @server.tool()
    def vault_info() -> dict:
        """Get vault structure stats: page counts by kind, available tags, last modified date."""
        return handle_vault_info(vault_path)

    @server.tool()
    def vault_read(title: str | None = None, filepath: str | None = None) -> dict:
        """Read a wiki or daily page. Pass either title or filepath (from vault_search results)."""
        return handle_vault_read(vault_path, title=title, filepath=filepath)

    @server.tool()
    def vault_search(
        query: str,
        kind: str | None = None,
        tags: list[str] | None = None,
        limit: int | None = 20,
    ) -> list[dict]:
        """Full-text search over vault wiki pages. Returns ranked results with snippets."""
        return handle_vault_search(vault_path, query, kind, tags, limit=limit)

    @server.tool()
    def vault_write(kind: str, title: str, content: str, tags: list[str]) -> dict:
        """Create a new wiki page or append to today's daily note.

        Args:
            kind: entity | concept | source | synthesis | daily
            title: Page title (or daily section heading)
            content: Markdown body (without frontmatter)
            tags: List of tag strings
        """
        return handle_vault_write(vault_path, kind, title, content, tags)

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
