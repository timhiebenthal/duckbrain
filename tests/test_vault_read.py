"""Tests for vault_read tool."""

import json
from pathlib import Path

from duckbrain.tools.vault_read import handle_vault_read


def test_vault_read_finds_existing_page_by_title(temp_vault: Path):
    """Read an existing page by title."""
    result = handle_vault_read(str(temp_vault), title="Claude Mem")
    assert result["title"] == "Claude Mem"
    assert result["kind"] == "entity"
    assert "Claude Mem" in result["content"]
    assert "MCP-based" in result["content"]
    assert "open-source" in result["tags"]


def test_vault_read_daily_page_by_title(temp_vault: Path):
    """Read a daily page by title (date)."""
    result = handle_vault_read(str(temp_vault), title="2026-05-28")
    assert result["title"] == "2026-05-28"
    assert result["kind"] == "daily"
    assert "duckbrain" in result["content"].lower()


def test_vault_read_by_filepath(temp_vault: Path):
    """Read a page directly by filepath (as returned by vault_search)."""
    result = handle_vault_read(
        str(temp_vault),
        filepath="wiki/concepts/agent-memory-systems.md",
    )
    assert "6-level taxonomy" in result["content"]
    assert result["filepath"] == "wiki/concepts/agent-memory-systems.md"


def test_vault_read_by_daily_filepath(temp_vault: Path):
    """Read a daily page by filepath."""
    result = handle_vault_read(
        str(temp_vault),
        filepath="daily/2026-05-28.md",
    )
    assert result["kind"] == "daily"
    assert "duckbrain" in result["content"].lower()


def test_vault_read_not_found_by_title(temp_vault: Path):
    """Non-existent title returns error."""
    result = handle_vault_read(str(temp_vault), title="Nonexistent Page")
    assert "error" in result


def test_vault_read_not_found_by_filepath(temp_vault: Path):
    """Non-existent filepath returns error."""
    result = handle_vault_read(str(temp_vault), filepath="wiki/fake/file.md")
    assert "error" in result


def test_vault_read_missing_both(temp_vault: Path):
    """Calling with neither title nor filepath returns error."""
    result = handle_vault_read(str(temp_vault))
    assert "error" in result
