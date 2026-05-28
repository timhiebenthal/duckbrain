"""Tests for vault_read tool."""

import json
from pathlib import Path

from duckbrain.tools.vault_read import handle_vault_read


def test_vault_read_finds_existing_page(temp_vault: Path):
    """Read an existing page by title."""
    result = handle_vault_read(str(temp_vault), "Claude Mem")
    assert result["title"] == "Claude Mem"
    assert result["kind"] == "entity"
    assert "Claude Mem" in result["content"]
    assert "MCP-based" in result["content"]
    assert "open-source" in result["tags"]


def test_vault_read_daily_page(temp_vault: Path):
    """Read a daily page by title (date)."""
    result = handle_vault_read(str(temp_vault), "2026-05-28")
    assert result["title"] == "2026-05-28"
    assert result["kind"] == "daily"
    assert "duckbrain" in result["content"].lower()


def test_vault_read_not_found(temp_vault: Path):
    """Non-existent page returns error."""
    result = handle_vault_read(str(temp_vault), "Nonexistent Page")
    assert "error" in result
