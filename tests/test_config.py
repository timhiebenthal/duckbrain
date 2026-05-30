"""Tests for duckbrain.config — VaultConfig types and loading."""

from pathlib import Path





def test_default_config_values() -> None:
    """VaultConfig() returns config matching current hardcoded behavior.

    Verifies: 5 scan patterns, daily write rule, default write rule.
    """
    from duckbrain.config import DateSource, VaultConfig

    config = VaultConfig()

    # Version and config_path
    assert config.version == 1
    assert config.config_path is None  # no file loaded

    # ── Scan patterns ──────────────────────────────────────────────────────
    assert len(config.scan_patterns) == 5

    patterns_by_kind = {p.kind: p for p in config.scan_patterns}

    # Entity pattern
    entity = patterns_by_kind["entity"]
    assert entity.glob == "wiki/entities/*.md"
    assert entity.frontmatter_enabled is True
    assert entity.kind_field == "item-type"
    assert entity.date_created == DateSource.FRONTMATTER
    assert entity.date_updated == DateSource.FRONTMATTER
    assert entity.created_field == "created"
    assert entity.updated_field == "updated"

    # Concept pattern
    concept = patterns_by_kind["concept"]
    assert concept.glob == "wiki/concepts/*.md"
    assert concept.frontmatter_enabled is True
    assert concept.kind_field == "item-type"

    # Source pattern
    source = patterns_by_kind["source"]
    assert source.glob == "wiki/sources/*.md"

    # Synthesis pattern
    synthesis = patterns_by_kind["synthesis"]
    assert synthesis.glob == "wiki/synthesis/*.md"

    # Daily pattern
    daily_pattern = patterns_by_kind["daily"]
    assert daily_pattern.glob == "daily/*.md"
    assert daily_pattern.frontmatter_enabled is False
    assert daily_pattern.kind_field is None
    assert daily_pattern.date_created == DateSource.FILENAME
    assert daily_pattern.date_updated == DateSource.FILENAME

    # ── Write rules ────────────────────────────────────────────────────────
    # Daily has explicit rule
    daily_write = config.write_rules["daily"]
    assert daily_write.mode == "append"
    assert daily_write.directory_template == "daily/"
    assert daily_write.filename_template == "{date}.md"
    assert daily_write.frontmatter is False
    assert daily_write.update_log is True
    assert daily_write.update_index is False
    assert daily_write.index_section is None
    assert daily_write.excluded_tags == []

    # ── Default write rule ─────────────────────────────────────────────────
    default = config.write_default
    assert default.mode == "create"
    assert default.directory_template == "wiki/{kind}s/"
    assert default.filename_template == "{slug}.md"
    assert default.frontmatter is True
    assert default.update_log is True
    assert default.update_index is True
    assert default.index_section == "{Kind}"
    assert default.excluded_tags == [
        "source", "concept", "entity", "synthesis", "clippings",
    ]
    # Frontmatter fields match what generate_frontmatter produces today
    assert default.frontmatter_fields == {
        "title": "{title}",
        "item-type": "{kind}",
        "tags": "{tags}",
        "created": "{date}",
        "updated": "{date}",
    }


def test_load_config_from_file(tmp_path: Path) -> None:
    """load_vault_config reads duckbrain.config.json and parses a custom pattern."""
    import json

    from duckbrain.config import DateSource, load_vault_config

    config_data = {
        "version": 1,
        "scan": {
            "patterns": [
                {
                    "glob": "wiki/projects/*.md",
                    "kind": "project",
                    "frontmatter": {"enabled": True, "kind_field": "item-type"},
                    "dates": {"created": "frontmatter:created", "updated": "frontmatter:updated"},
                },
            ],
        },
    }

    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    config_path = vault_dir / "duckbrain.config.json"
    config_path.write_text(json.dumps(config_data))

    config = load_vault_config(str(vault_dir))

    assert config.config_path == str(config_path)
    assert len(config.scan_patterns) == 1
    pattern = config.scan_patterns[0]
    assert pattern.glob == "wiki/projects/*.md"
    assert pattern.kind == "project"
    assert pattern.frontmatter_enabled is True
    assert pattern.kind_field == "item-type"
    assert pattern.date_created == DateSource.FRONTMATTER
    assert pattern.date_updated == DateSource.FRONTMATTER
    assert pattern.created_field == "created"
    assert pattern.updated_field == "updated"

    # Write rules should still have defaults (daily + write_default)
    assert "daily" in config.write_rules
    assert config.write_default.mode == "create"


def test_missing_config_returns_defaults(tmp_path: Path) -> None:
    """load_vault_config with a nonexistent path returns defaults."""
    from duckbrain.config import load_vault_config

    config = load_vault_config(str(tmp_path / "no-config-here"))
    assert config.config_path is None
    assert len(config.scan_patterns) == 5  # default patterns
    assert config.version == 1


def test_empty_vault_no_config(tmp_path: Path) -> None:
    """load_vault_config with an empty vault (no config file) returns defaults."""
    from duckbrain.config import load_vault_config

    vault = tmp_path / "empty-vault"
    vault.mkdir()

    config = load_vault_config(str(vault))
    assert config.config_path is None
    assert len(config.scan_patterns) == 5


def test_invalid_json_returns_defaults_with_warning(tmp_path: Path, caplog) -> None:
    """Malformed JSON returns default config and logs a warning."""
    from duckbrain.config import load_vault_config

    vault = tmp_path / "bad-config"
    vault.mkdir()
    (vault / "duckbrain.config.json").write_text("not valid json {{{")

    config = load_vault_config(str(vault))

    # Falls back to defaults
    assert len(config.scan_patterns) == 5
    assert config.config_path is None

    # Warning logged
    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert any("Failed to parse" in w for w in warnings), f"Expected parse warning, got: {warnings}"


def test_unknown_date_source_fallback(tmp_path: Path, caplog) -> None:
    """Invalid date source string falls back to FRONTMATTER with warning."""
    import json

    from duckbrain.config import DateSource, load_vault_config

    config_data = {
        "version": 1,
        "scan": {
            "patterns": [
                {
                    "glob": "wiki/projects/*.md",
                    "kind": "project",
                    "frontmatter": {"enabled": True, "kind_field": "item-type"},
                    "dates": {"created": "unknown:blah", "updated": "frontmatter:updated"},
                },
            ],
        },
    }

    vault = tmp_path / "bad-dates"
    vault.mkdir()
    (vault / "duckbrain.config.json").write_text(json.dumps(config_data))

    config = load_vault_config(str(vault))

    assert config.scan_patterns[0].date_created == DateSource.FRONTMATTER  # fallback
    assert config.scan_patterns[0].date_updated == DateSource.FRONTMATTER

    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert any("Unknown date" in w or "date" in w.lower() for w in warnings), (
        f"Expected date warning, got: {warnings}"
    )


def test_config_types_importable() -> None:
    """VaultConfig, ScanPattern, WriteRule, DateSource, load_vault_config are
    importable from duckbrain.config."""
    from duckbrain.config import (  # noqa: F401
        DateSource,
        ScanPattern,
        VaultConfig,
        WriteRule,
        load_vault_config,
    )


def test_config_types_importable_from_package() -> None:
    """Config types are re-exported from the duckbrain package."""
    from duckbrain import DateSource, ScanPattern, VaultConfig, WriteRule  # noqa: F401
