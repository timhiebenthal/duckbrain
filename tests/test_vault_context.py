"""Tests for duckbrain.tools.vault_context — vault_context MCP tool logic.

These tests will FAIL until the implementation is written in
src/duckbrain/tools/vault_context.py.
"""

from datetime import date, timedelta
from pathlib import Path


def _create_daily_file(vault: Path, day: date, content: str) -> Path:
    """Create a daily note file at vault/daily/{day}.md."""
    daily_dir = vault / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    filepath = daily_dir / f"{day}.md"
    filepath.write_text(content)
    return filepath


def test_vault_context_keyword_search(temp_vault: Path) -> None:
    """Search with keywords returns matching pages plus today+yesterday dailies."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Create daily files for today and yesterday
    _create_daily_file(temp_vault, today, f"# {today}\n\nDaily notes for today.\n")
    _create_daily_file(
        temp_vault, yesterday, f"# {yesterday}\n\nDaily notes for yesterday.\n"
    )

    from duckbrain.tools.vault_context import handle_vault_context

    result = handle_vault_context(str(temp_vault), keywords=["memory"])

    # search_results should contain pages mentioning "memory"
    assert "search_results" in result
    titles = [r["title"] for r in result["search_results"]]
    assert "Claude Mem" in titles, (
        f"Expected 'Claude Mem' in search_results, got {titles}"
    )
    assert "Agent Memory Systems" in titles, (
        f"Expected 'Agent Memory Systems' in search_results, got {titles}"
    )

    # today_daily should be populated
    assert result["today_daily"] is not None, "Expected today_daily to have content"
    assert result["today_daily"]["title"] == str(today)
    assert result["today_daily"]["filepath"] == f"daily/{today}.md"

    # yesterday_daily should be populated
    assert result["yesterday_daily"] is not None, (
        "Expected yesterday_daily to have content"
    )
    assert result["yesterday_daily"]["title"] == str(yesterday)
    assert result["yesterday_daily"]["filepath"] == f"daily/{yesterday}.md"


def test_vault_context_skip_dailies(temp_vault: Path) -> None:
    """With include_dailies=False, both daily entries are None but search works."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    _create_daily_file(temp_vault, today, f"# {today}\n\nDaily notes.\n")
    _create_daily_file(temp_vault, yesterday, f"# {yesterday}\n\nDaily notes.\n")

    from duckbrain.tools.vault_context import handle_vault_context

    result = handle_vault_context(
        str(temp_vault), include_dailies=False, keywords=["memory"]
    )

    assert result["today_daily"] is None
    assert result["yesterday_daily"] is None
    assert len(result["search_results"]) >= 1


def test_vault_context_skip_search(temp_vault: Path) -> None:
    """With include_search=False, search_results is empty but dailies are populated."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    _create_daily_file(temp_vault, today, f"# {today}\n\nDaily notes.\n")
    _create_daily_file(temp_vault, yesterday, f"# {yesterday}\n\nDaily notes.\n")

    from duckbrain.tools.vault_context import handle_vault_context

    result = handle_vault_context(str(temp_vault), include_search=False)

    assert result["search_results"] == []
    assert result["today_daily"] is not None
    assert result["yesterday_daily"] is not None


def test_vault_context_missing_daily(temp_vault: Path) -> None:
    """When today's daily file doesn't exist, today_daily is None; search still works."""
    # Intentionally do NOT create today's daily file.
    # The fixture only creates 2026-05-28; today's date will not match that.

    from duckbrain.tools.vault_context import handle_vault_context

    result = handle_vault_context(str(temp_vault), keywords=["memory"])

    assert result["today_daily"] is None, (
        "Expected today_daily to be None when file is missing"
    )
    assert len(result["search_results"]) >= 1


def test_vault_context_empty_keywords(temp_vault: Path) -> None:
    """With keywords=[], search_results is empty."""
    today = date.today()
    _create_daily_file(temp_vault, today, f"# {today}\n\nDaily notes.\n")

    from duckbrain.tools.vault_context import handle_vault_context

    result = handle_vault_context(str(temp_vault), keywords=[])

    assert result["search_results"] == []


def test_vault_context_search_limit(temp_vault: Path) -> None:
    """search_limit caps the number of search results."""
    today = date.today()
    _create_daily_file(temp_vault, today, f"# {today}\n\nDaily notes.\n")

    from duckbrain.tools.vault_context import handle_vault_context

    result = handle_vault_context(
        str(temp_vault), keywords=["memory"], search_limit=1
    )

    assert len(result["search_results"]) == 1
