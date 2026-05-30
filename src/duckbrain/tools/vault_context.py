"""MCP tool: vault_context — get context about the vault (dailies + search)."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from duckbrain.config import VaultConfig
from duckbrain.tools.vault_search import handle_vault_search


def _read_daily(vault_path: str, day: date, daily_dir: str = "daily") -> dict[str, str] | None:
    """Read a daily note file and return title/filepath/content or None."""
    date_str = day.isoformat()
    filepath = f"{daily_dir}/{date_str}.md"
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
    config: VaultConfig | None = None,
) -> dict[str, Any]:
    """Get vault context: today's and yesterday's daily notes, plus optional search results."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Determine daily directory from config or default
    daily_dir = "daily"
    if config is not None:
        for pattern in config.scan_patterns:
            if pattern.kind == "daily":
                # Extract directory from glob: "daily/*.md" → "daily"
                daily_dir = pattern.glob.rsplit("/", 1)[0].rstrip("/")
                break
        else:
            # No daily pattern found — skip dailies
            include_dailies = False

    result: dict[str, Any] = {
        "today_daily": None,
        "yesterday_daily": None,
        "search_results": [],
    }

    if include_dailies:
        result["today_daily"] = _read_daily(vault_path, today, daily_dir)
        result["yesterday_daily"] = _read_daily(vault_path, yesterday, daily_dir)

    if include_search and keywords:
        query = " ".join(keywords)
        result["search_results"] = handle_vault_search(
            vault_path,
            query,
            limit=search_limit,
            config=config,
        )

    return result
