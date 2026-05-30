"""Tests for vault_audit diagnostic tool."""

from pathlib import Path


def test_vault_audit_standard_vault(temp_vault: Path) -> None:
    """vault_audit detects standard vault structure from temp_vault fixture."""
    from duckbrain.tools.vault_audit import handle_vault_audit

    result = handle_vault_audit(str(temp_vault))

    assert result["config_exists"] is False
    assert result["summary"]["total_pages"] == 8  # 5 wiki + 1 daily + index + log
    assert result["summary"]["has_dailies"] is True

    dirs = {d["path"]: d for d in result["directories"]}
    # daily/ has date-pattern filenames
    assert "daily/" in dirs
    assert dirs["daily/"]["filename_pattern"] == "YYYY-MM-DD.md"
    assert dirs["daily/"]["file_count"] == 1

    # wiki/entities/ has frontmatter
    assert "wiki/entities/" in dirs
    assert dirs["wiki/entities/"]["frontmatter"]["pct_with_frontmatter"] == 100
    assert dirs["wiki/"]["file_count"] == 2  # index.md + log.md


def test_vault_audit_no_frontmatter(tmp_path: Path) -> None:
    """Directory with .md files but no frontmatter → pct=0, common_fields=[]."""
    from duckbrain.tools.vault_audit import handle_vault_audit

    vault = tmp_path / "vault"
    (vault / "notes").mkdir(parents=True)
    (vault / "notes" / "a.md").write_text("just text")
    (vault / "notes" / "b.md").write_text("more text")

    result = handle_vault_audit(str(vault))

    dirs = {d["path"]: d for d in result["directories"]}
    assert dirs["notes/"]["frontmatter"]["pct_with_frontmatter"] == 0
    assert dirs["notes/"]["frontmatter"]["common_fields"] == []


def test_vault_audit_unknown_dirs(tmp_path: Path) -> None:
    """Directory with files but no item-type → listed in unknown_dirs."""
    from duckbrain.tools.vault_audit import handle_vault_audit

    vault = tmp_path / "vault"
    (vault / "wiki").mkdir(parents=True)
    (vault / "stuff").mkdir(parents=True)
    (vault / "stuff" / "readme.md").write_text("# Readme\n\nNo frontmatter")

    result = handle_vault_audit(str(vault))

    assert "stuff/" in result["summary"]["unknown_dirs"]


def test_vault_audit_custom_dates(tmp_path: Path) -> None:
    """Files with YYYY-MM-DD filenames → filename_pattern detected."""
    from duckbrain.tools.vault_audit import handle_vault_audit

    vault = tmp_path / "vault"
    journal = vault / "journal"
    journal.mkdir(parents=True)
    (journal / "2026-03-15.md").write_text("entry")
    (journal / "2026-03-16.md").write_text("entry")

    result = handle_vault_audit(str(vault))

    dirs = {d["path"]: d for d in result["directories"]}
    assert dirs["journal/"]["filename_pattern"] == "YYYY-MM-DD.md"
    assert dirs["journal/"]["heuristic_kinds"] == ["daily"]


def test_vault_audit_already_configured(tmp_path: Path) -> None:
    """If duckbrain.config.json exists → config_exists=true."""
    from duckbrain.tools.vault_audit import handle_vault_audit

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "duckbrain.config.json").write_text("{}")

    result = handle_vault_audit(str(vault))

    assert result["config_exists"] is True
    assert result["summary"]["has_config"] is True
