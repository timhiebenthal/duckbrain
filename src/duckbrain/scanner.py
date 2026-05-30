"""Vault file discovery and YAML frontmatter parsing."""

import re
from pathlib import Path
from typing import Any

import yaml

from duckbrain import PageMetadata
from duckbrain.config import DateSource, VaultConfig


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.

    Returns:
        A tuple of (frontmatter_dict, body_text). If no frontmatter is found or
        YAML parsing fails, returns ({}, content) unchanged.
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing `---`
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    yaml_block = content[3:end_idx].strip()
    body = content[end_idx + 3 :].strip()

    if not yaml_block:
        return {}, body

    try:
        meta = yaml.safe_load(yaml_block)
        if not isinstance(meta, dict):
            return {}, content
        return meta, body
    except yaml.YAMLError:
        return {}, content


def scan_vault(vault_path: str, config: VaultConfig | None = None) -> list[PageMetadata]:
    """Scan an Obsidian vault for wiki pages.

    When *config* is None (default): uses hardcoded kind-to-directory
    mappings matching DuckBrain's original layout.

    When *config* is a :class:`VaultConfig`: iterates the configured
    scan patterns.

    Args:
        vault_path: Root path of the Obsidian vault.
        config: Optional vault configuration.

    Returns:
        A list of :class:`PageMetadata` objects (one per discovered page).
    """
    if config is not None:
        return _scan_with_config(vault_path, config)

    vault = Path(vault_path)
    pages: list[PageMetadata] = []

    kind_to_dir = {
        "entity": "entities",
        "concept": "concepts",
        "source": "sources",
        "synthesis": "synthesis",
    }

    # Build a reverse map: parent dir name → kind
    dir_to_kind = {v: k for k, v in kind_to_dir.items()}

    for subdir in kind_to_dir.values():
        glob_pattern = f"wiki/{subdir}/*.md"
        for filepath in sorted(vault.glob(glob_pattern)):
            try:
                content = filepath.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue  # skip unreadable files

            meta, body = parse_frontmatter(content)

            item_type = meta.get("item-type")
            if not item_type:
                continue

            # Infer kind from parent directory name
            parent_dir = filepath.parent.name
            kind = dir_to_kind.get(parent_dir, item_type)

            title = meta.get("title", filepath.stem)
            tags = meta.get("tags", [])
            created = meta.get("created", "")
            updated = meta.get("updated", "")

            pages.append(
                PageMetadata(
                    filepath=str(filepath.relative_to(vault)),
                    title=title,
                    kind=kind,
                    tags=tags if isinstance(tags, list) else [],
                    body=body,
                    created=created,
                    updated=updated,
                )
            )

    pages.extend(scan_daily(vault_path))
    return pages


def _scan_with_config(vault_path: str, config: VaultConfig) -> list[PageMetadata]:
    """Scan vault using configured scan patterns."""
    vault = Path(vault_path)
    pages: list[PageMetadata] = []

    for pattern in config.scan_patterns:
        for filepath in sorted(vault.glob(pattern.glob)):
            try:
                content = filepath.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            if pattern.frontmatter_enabled:
                meta, body = parse_frontmatter(content)
                # Check kind field matches expected kind
                kind_field = pattern.kind_field or "item-type"
                item_type = meta.get(kind_field)
                if not item_type:
                    continue
                kind = str(item_type)
                title = meta.get("title", filepath.stem)
                tags = meta.get("tags", [])
                tags = tags if isinstance(tags, list) else []
                created = _extract_date(
                    meta,
                    filepath,
                    pattern.date_created,
                    pattern.created_field,
                )
                updated = _extract_date(
                    meta,
                    filepath,
                    pattern.date_updated,
                    pattern.updated_field,
                )
            else:
                # No frontmatter — derive from filename
                body = content
                kind = pattern.kind
                title = filepath.stem
                tags = []
                created = _extract_date(
                    {},
                    filepath,
                    pattern.date_created,
                    pattern.created_field,
                )
                updated = _extract_date(
                    {},
                    filepath,
                    pattern.date_updated,
                    pattern.updated_field,
                )

            pages.append(
                PageMetadata(
                    filepath=str(filepath.relative_to(vault)),
                    title=title,
                    kind=kind,
                    tags=tags,
                    body=body,
                    created=created,
                    updated=updated,
                ),
            )

    return pages


_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _extract_date(
    meta: dict[str, Any],
    filepath: Path,
    source: DateSource,
    field: str,
) -> str:
    """Extract date from metadata or filesystem per DateSource."""
    if source == DateSource.FRONTMATTER:
        val = meta.get(field, "")
        return str(val) if val else ""
    if source == DateSource.FILENAME:
        m = _DATE_RE.match(filepath.stem)
        return m.group(1) if m else ""
    if source == DateSource.MTIME:
        try:
            return str(filepath.stat().st_mtime)
        except OSError:
            return ""
    return ""


def scan_daily(vault_path: str) -> list[PageMetadata]:
    """Scan daily notes (``daily/*.md``).

    Daily files have no YAML frontmatter — all metadata is derived from the
    filename (title = filename stem, created/updated = filename date).

    Args:
        vault_path: Root path of the Obsidian vault.

    Returns:
        A list of :class:`PageMetadata` objects (one per daily file).
    """
    daily_dir = Path(vault_path) / "daily"
    if not daily_dir.is_dir():
        return []

    pages: list[PageMetadata] = []
    for md_file in sorted(daily_dir.glob("*.md")):
        date_str = md_file.stem
        try:
            body = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        pages.append(
            PageMetadata(
                filepath=str(md_file.relative_to(Path(vault_path))),
                title=date_str,
                kind="daily",
                tags=[],
                body=body,
                created=date_str,
                updated=date_str,
            )
        )
    return pages
