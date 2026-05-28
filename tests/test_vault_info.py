"""Tests for duckbrain.tools.vault_info — vault structure summary."""

from pathlib import Path


def test_vault_info_returns_counts(temp_vault: Path) -> None:
    """handle_vault_info returns correct counts per kind matching temp_vault."""
    from duckbrain.tools.vault_info import handle_vault_info

    info = handle_vault_info(str(temp_vault))

    assert info["entities"] == 1
    assert info["concepts"] == 2
    assert info["sources"] == 1
    assert info["synthesis"] == 1
    assert info["daily"] == 1


def test_vault_info_includes_tags(temp_vault: Path) -> None:
    """available_tags is non-empty and matches tags in fixture pages."""
    from duckbrain.tools.vault_info import handle_vault_info

    info = handle_vault_info(str(temp_vault))

    tags = info["available_tags"]
    assert isinstance(tags, list)
    assert len(tags) > 0
    assert tags == sorted(tags)

    # All expected tags from the fixture should be present
    expected_tags = {
        "open-source", "ai", "memory", "mcp",
        "agent-memory", "taxonomy",
        "llm", "capability",
        "duckdb", "comparison",
        "metrics-layer", "mds",
    }
    for tag in expected_tags:
        assert tag in tags, f"Missing expected tag: {tag}"
    assert len(tags) == 12


def test_vault_info_last_modified(temp_vault: Path) -> None:
    """last_modified matches the max updated date from fixture pages."""
    from duckbrain.tools.vault_info import handle_vault_info

    info = handle_vault_info(str(temp_vault))
    assert info["last_modified"] == "2026-05-28"


def test_vault_info_empty_vault(tmp_path: Path) -> None:
    """An empty vault returns all zero counts and empty tags."""
    from duckbrain.tools.vault_info import handle_vault_info

    info = handle_vault_info(str(tmp_path))

    assert info["entities"] == 0
    assert info["concepts"] == 0
    assert info["sources"] == 0
    assert info["synthesis"] == 0
    assert info["available_tags"] == []
    assert info["last_modified"] is None
