"""MCP tool: vault_context — get context about the vault (dailies + search)."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from duckbrain.tools.vault_search import handle_vault_search


def _read_daily(vault_path: str, day: date) -> dict[str, str] | None:
    """Read a daily note file and return title/filepath/content or None."""
    date_str = day.isoformat()
    filepath = f"daily/{date_str}.md"
    full_path = Path(vault_path) / filepath
    if not full_path.is_file():
        return None
    return {
        "title": date_str,
        "filepath": filepath,
        "content": full_path.read_text(encoding="utf-8"),
    }


def handle_vault_context(
    vault_path: str,
    keywords: list[str] | None = None,
    include_dailies: bool = True,
    include_search: bool = True,
    search_limit: int = 10,
) -> dict[str, Any]:
    """Get vault context: today's and yesterday's daily notes, plus optional search results.

    Parameters
    ----------
    vault_path:
        Root path of the Obsidian vault.
    keywords:
        Optional list of search keywords. Joined with spaces for FTS query.
    include_dailies:
        Whether to include today's and yesterday's daily notes.
    include_search:
        Whether to perform keyword search.
    search_limit:
        Maximum number of search results to return (default 10).

    Returns
    -------
    dict
        Keys: ``today_daily``, ``yesterday_daily``, ``search_results``.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    result: dict[str, Any] = {
        "today_daily": None,
        "yesterday_daily": None,
        "search_results": [],
    }

    if include_dailies:
        result["today_daily"] = _read_daily(vault_path, today)
        result["yesterday_daily"] = _read_daily(vault_path, yesterday)

    if include_search and keywords:
        query = " ".join(keywords)
        result["search_results"] = handle_vault_search(vault_path, query, limit=search_limit)

    return result
