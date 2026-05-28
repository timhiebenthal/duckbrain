"""Vault file discovery and YAML frontmatter parsing."""

from pathlib import Path
from typing import Any
import yaml

from duckbrain import PageMetadata


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
    body = content[end_idx + 3:].strip()

    if not yaml_block:
        return {}, body

    try:
        meta = yaml.safe_load(yaml_block)
        if not isinstance(meta, dict):
            return {}, content
        return meta, body
    except yaml.YAMLError:
        return {}, content


def scan_vault(vault_path: str) -> list[PageMetadata]:
    """Scan an Obsidian vault for wiki pages with valid item-type frontmatter.

    Globs ``wiki/{entities,concepts,sources,synthesis}/*.md`` under *vault_path*
    and returns a :class:`PageMetadata` for each file that has an ``item-type``
    key matching the parent directory name.

    Args:
        vault_path: Root path of the Obsidian vault.

    Returns:
        A list of :class:`PageMetadata` objects (one per discovered page).
    """
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

    return pages


def scan_daily(vault_path: str) -> list[PageMetadata]:
    """Scan daily notes (placeholder for future use).

    Glob ``daily/*.md`` under *vault_path* and returns metadata for each file.
    Currently returns an empty list.
    """
    # TODO: implement daily note scanning when needed
    # vault = Path(vault_path)
    # for filepath in sorted(vault.glob("daily/*.md")):
    #     ...
    return []
