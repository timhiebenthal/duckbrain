"""Tests for server startup initialization."""
from pathlib import Path


def test_bootstrap_vault_creates_tags_index(temp_vault):
    """bootstrap_vault should generate tags.md so the OpenCode plugin has content to read on first session."""
    from duckbrain.server import bootstrap_vault

    bootstrap_vault(temp_vault)

    tags_file = Path(temp_vault) / "wiki" / "tags.md"
    assert tags_file.exists()
    content = tags_file.read_text()
    assert content.startswith("# Vault Tags")
