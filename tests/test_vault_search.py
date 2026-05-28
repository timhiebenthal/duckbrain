"""Tests for duckbrain.tools.vault_search — vault_search MCP tool logic."""

from pathlib import Path


def test_vault_search_finds_content(temp_vault: Path) -> None:
    """Search for 'memory' returns pages containing that word in body text."""
    from duckbrain.tools.vault_search import handle_vault_search

    results = handle_vault_search(str(temp_vault), "memory")

    assert len(results) >= 1
    # "memory" appears in "Claude Mem" and "Agent Memory Systems" bodies
    titles = [r["title"] for r in results]
    assert "Claude Mem" in titles, f"Expected 'Claude Mem' in results, got {titles}"
    assert "Agent Memory Systems" in titles, (
        f"Expected 'Agent Memory Systems' in results, got {titles}"
    )


def test_vault_search_kind_filter(temp_vault: Path) -> None:
    """Search with kind='concept' returns only concept-type results."""
    from duckbrain.tools.vault_search import handle_vault_search

    results = handle_vault_search(str(temp_vault), "memory", kind="concept")

    assert len(results) >= 1
    for r in results:
        assert r["kind"] == "concept", f"Expected kind 'concept', got '{r['kind']}'"


def test_vault_search_no_results(temp_vault: Path) -> None:
    """Search for a non-existent term returns an empty list."""
    from duckbrain.tools.vault_search import handle_vault_search

    results = handle_vault_search(str(temp_vault), "zzzxyz")
    assert results == []
