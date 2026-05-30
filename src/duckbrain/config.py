"""Vault config types, loading, and defaults."""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DateSource(Enum):
    """Where to extract created/updated dates from."""

    FRONTMATTER = "frontmatter"
    FILENAME = "filename"
    MTIME = "mtime"


@dataclass
class ScanPattern:
    """A glob pattern that maps vault files to a page kind."""

    glob: str
    kind: str
    frontmatter_enabled: bool = True
    kind_field: str | None = "item-type"  # frontmatter key indicating kind
    date_created: DateSource = DateSource.FRONTMATTER
    date_updated: DateSource = DateSource.FRONTMATTER
    created_field: str = "created"
    updated_field: str = "updated"


@dataclass
class WriteRule:
    """Per-kind writing rules: where and how pages are created."""

    mode: str = "create"  # "create" or "append"
    directory_template: str = "wiki/{kind}s/"
    filename_template: str = "{slug}.md"
    frontmatter: bool = True
    frontmatter_fields: dict[str, str] | None = None
    update_log: bool = True
    update_index: bool = True
    index_section: str | None = "{Kind}"
    log_entry_format: str | None = None
    excluded_tags: list[str] | None = None

    def __post_init__(self) -> None:
        """Fill in defaults matching current writer.py behavior."""
        if self.frontmatter_fields is None:
            self.frontmatter_fields = {
                "title": "{title}",
                "item-type": "{kind}",
                "tags": "{tags}",
                "created": "{date}",
                "updated": "{date}",
            }
        if self.log_entry_format is None:
            self.log_entry_format = "## [{date}] ingest | {title}\n- Created {kind}: {title}\n"
        if self.excluded_tags is None:
            self.excluded_tags = [
                "source",
                "concept",
                "entity",
                "synthesis",
                "clippings",
            ]


@dataclass
class VaultConfig:
    """Parsed vault config with defaults matching current hardcoded behavior."""

    version: int = 1
    scan_patterns: list[ScanPattern] = field(default_factory=list)
    write_rules: dict[str, WriteRule] = field(default_factory=dict)
    write_default: WriteRule = field(default_factory=WriteRule)
    config_path: str | None = None  # None when using defaults

    def __post_init__(self) -> None:
        if not self.scan_patterns:
            self.scan_patterns = _default_scan_patterns()
        if not self.write_rules:
            self.write_rules = _default_write_rules()


def _default_scan_patterns() -> list[ScanPattern]:
    """Scan patterns matching current hardcoded scanner.py behavior."""
    return [
        ScanPattern(
            glob="wiki/entities/*.md",
            kind="entity",
        ),
        ScanPattern(
            glob="wiki/concepts/*.md",
            kind="concept",
        ),
        ScanPattern(
            glob="wiki/sources/*.md",
            kind="source",
        ),
        ScanPattern(
            glob="wiki/synthesis/*.md",
            kind="synthesis",
        ),
        ScanPattern(
            glob="daily/*.md",
            kind="daily",
            frontmatter_enabled=False,
            kind_field=None,
            date_created=DateSource.FILENAME,
            date_updated=DateSource.FILENAME,
        ),
    ]


def _default_write_rules() -> dict[str, WriteRule]:
    """Write rules matching current hardcoded writer.py behavior.

    Returns a dict with key "daily" for the daily notes rule.
    """
    return {
        "daily": WriteRule(
            mode="append",
            directory_template="daily/",
            filename_template="{date}.md",
            frontmatter=False,
            frontmatter_fields={},
            update_index=False,
            index_section=None,
            log_entry_format=("## [{date}] daily | {title}\n- Added to daily note: {title}\n"),
            excluded_tags=[],
        ),
    }


def load_vault_config(vault_path: str) -> VaultConfig:
    """Load config from vault_path/duckbrain.config.json, or return defaults.

    Args:
        vault_path: Root path of the Obsidian vault.

    Returns:
        VaultConfig parsed from file, or defaults if no file found.
    """
    config_file = Path(vault_path) / "duckbrain.config.json"
    if not config_file.is_file():
        return VaultConfig()  # defaults already match hardcoded behavior
    try:
        return _parse_config(config_file.read_text(encoding="utf-8"), str(config_file))
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse %s: %s — using defaults", config_file, e)
        return VaultConfig()


def _parse_date_source(raw: str) -> tuple[DateSource, str]:
    """Parse a date source string like 'frontmatter:created' or 'filename'.

    Returns (DateSource, field_name) tuple.
    """
    if raw == "filename":
        return DateSource.FILENAME, ""
    if raw == "mtime":
        return DateSource.MTIME, ""
    if raw.startswith("frontmatter:"):
        field = raw.split(":", 1)[1]
        return DateSource.FRONTMATTER, field
    logger.warning("Unknown date source '%s', falling back to frontmatter:created", raw)
    return DateSource.FRONTMATTER, "created"  # fallback


def _parse_config(raw_text: str, config_path: str) -> VaultConfig:
    """Parse JSON config text into VaultConfig."""
    data = json.loads(raw_text)
    version = data.get("version", 1)

    # Parse scan patterns
    scan_patterns: list[ScanPattern] = []
    scan_data = data.get("scan", {})
    for pat in scan_data.get("patterns", []):
        fm = pat.get("frontmatter", {})
        dates_raw = pat.get("dates", {})
        created_src, created_field = _parse_date_source(
            dates_raw.get("created", "frontmatter:created"),
        )
        updated_src, updated_field = _parse_date_source(
            dates_raw.get("updated", "frontmatter:updated"),
        )
        scan_patterns.append(
            ScanPattern(
                glob=pat["glob"],
                kind=pat["kind"],
                frontmatter_enabled=fm.get("enabled", True),
                kind_field=fm.get("kind_field") if fm.get("enabled") else None,
                date_created=created_src,
                date_updated=updated_src,
                created_field=created_field,
                updated_field=updated_field,
            ),
        )

    # Parse write rules
    write_data = data.get("write", {})
    write_rules: dict[str, WriteRule] = {}
    rules = write_data.get("rules", {})
    for kind, raw_rule in rules.items():
        write_rules[kind] = _parse_write_rule(raw_rule)

    # Parse write default
    write_default_raw = write_data.get("default", {})
    write_default = _parse_write_rule(write_default_raw) if write_default_raw else WriteRule()

    return VaultConfig(
        version=version,
        scan_patterns=scan_patterns,
        write_rules=write_rules,
        write_default=write_default,
        config_path=config_path,
    )


def _parse_write_rule(raw: dict[str, Any]) -> WriteRule:
    """Parse a single write rule from raw JSON dict."""
    fm_fields = raw.get("frontmatter_fields")
    return WriteRule(
        mode=raw.get("mode", "create"),
        directory_template=raw.get("directory", "wiki/{kind}s/"),
        filename_template=raw.get("filename", "{slug}.md"),
        frontmatter=raw.get("frontmatter", True),
        frontmatter_fields=dict(fm_fields) if fm_fields else None,
        update_log=raw.get("update_log", True),
        update_index=raw.get("update_index", True),
        index_section=raw.get("index_section"),
        log_entry_format=raw.get("log_entry_format"),
        excluded_tags=raw.get("excluded_tags"),
    )
