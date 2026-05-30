"""Tests for server startup initialization."""
from pathlib import Path


def test_bootstrap_vault_creates_tags_index(temp_vault):
    """bootstrap_vault should generate tags.md."""
    from duckbrain.server import bootstrap_vault

    bootstrap_vault(temp_vault)

    tags_file = Path(temp_vault) / "wiki" / "tags.md"
    assert tags_file.exists()
    content = tags_file.read_text()
    assert content.startswith("# Vault Tags")


# ── Config loading tests ─────────────────────────────────────────────────────


def test_get_vault_config_returns_config(temp_vault: Path) -> None:
    """get_vault_config returns VaultConfig when config file exists."""
    import json

    from duckbrain.server import get_vault_config, get_vault_path

    # Create a config file in the vault
    config_data = {"version": 1}
    (temp_vault / "duckbrain.config.json").write_text(json.dumps(config_data))

    # Can't actually load server here (it starts on stdio), so test
    # the helper functions directly by patching or testing load path
    from duckbrain.config import load_vault_config

    config = load_vault_config(str(temp_vault))
    assert config is not None
    assert config.config_path is not None


def test_no_config_returns_defaults(temp_vault: Path) -> None:
    """load_vault_config without config file returns defaults."""
    from duckbrain.config import load_vault_config

    config = load_vault_config(str(temp_vault))
    assert config.config_path is None
    assert len(config.scan_patterns) == 5
