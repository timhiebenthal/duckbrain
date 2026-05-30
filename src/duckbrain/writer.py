"""Page creation with frontmatter generation, index/log auto-update."""

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from duckbrain.config import VaultConfig
from duckbrain.scanner import parse_frontmatter

# Map page kind to index section header name
KIND_TO_SECTION: dict[str, str] = {
    "entity": "Entities",
    "concept": "Concepts",
    "source": "Sources",
    "synthesis": "Synthesis",
}

# Map page kind to subdirectory under wiki/
KIND_TO_SUBDIR: dict[str, str] = {
    "entity": "entities",
    "concept": "concepts",
    "source": "sources",
    "synthesis": "synthesis",
}


def generate_frontmatter(kind: str, title: str, tags: list[str]) -> str:
    """Generate YAML frontmatter block for a new wiki page.

    Returns a string wrapped in ``---`` delimiters with keys:
    ``title``, ``item-type`` (mapped from *kind*), ``tags``,
    ``created``, and ``updated`` (both set to today's date).

    Args:
        kind: Page kind — ``entity``, ``concept``, ``source``, or ``synthesis``.
        title: Page title.
        tags: List of tag strings.

    Returns:
        A string containing the complete YAML frontmatter block
        including the ``---`` delimiters.
    """
    today = date.today().isoformat()
    data: dict[str, Any] = {
        "title": title,
        "item-type": kind,
        "tags": tags,
        "created": today,
        "updated": today,
    }
    yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
    return f"---\n{yaml_str}---"


def slugify(title: str) -> str:
    """Convert a title to a URL-friendly slug.

    - Lowercases the title
    - Replaces any non-alphanumeric character (except spaces) with ``-``
    - Collapses multiple dashes/spaces to a single dash
    - Strips leading/trailing dashes

    Examples:
        >>> slugify("Claude Mem")
        'claude-mem'
        >>> slugify("BI's Second Unbundling")
        'bis-second-unbundling'
    """
    # Lowercase
    slug = title.lower()
    # Remove apostrophes entirely (they should not become dashes)
    slug = slug.replace("'", "")
    # Replace any remaining non-alphanumeric (except spaces) with dash
    slug = re.sub(r"[^a-z0-9\s]", "-", slug)
    # Collapse multiple dashes/spaces to single dash
    slug = re.sub(r"[\s-]+", "-", slug)
    # Strip leading/trailing dashes
    slug = slug.strip("-")
    return slug


class TemplateResolver:
    """Resolve template strings like ``{kind}``, ``{slug}``, ``{date}``.

    Supports variables: kind, Kind, kinds, slug, title, date, tags.
    """

    @staticmethod
    def resolve(template: str, kind: str, title: str, tags: list[str]) -> str:
        """Substitute template variables in *template*."""
        today = date.today().isoformat()
        slug = slugify(title)
        result = template.replace("{kind}", kind)
        result = result.replace("{Kind}", kind.capitalize())
        result = result.replace("{kinds}", kind + "s")
        result = result.replace("{slug}", slug)
        result = result.replace("{title}", title)
        result = result.replace("{date}", today)
        result = result.replace("{tags}", ", ".join(tags))
        return result


def _write_daily(
    vault_path: str,
    title: str,
    content: str,
    tags: list[str],
    target_date: str | None = None,
) -> dict[str, Any]:
    """Append a section to today's daily note.

    Daily notes live under ``daily/YYYY-MM-DD.md`` in the vault root
    (not under ``wiki/``).  They have no YAML frontmatter and are
    **appended** to — the file grows throughout the day.

    If a section with the same ``## {title}`` heading already exists,
    its body is replaced in-place (dedup).  Otherwise the section is
    appended.

    Args:
        vault_path: Root path of the Obsidian vault.
        title: Section heading for this daily entry.
        content: Markdown body content.
        tags: List of tag strings.
        target_date: Override target date (``YYYY-MM-DD``).  When
            ``None`` (default), uses today's date.

    Returns:
        A dict with keys ``success`` (bool), ``filepath`` (str, relative),
        and ``warnings`` (list of str).
    """
    warnings: list[str] = []
    today = target_date or date.today().isoformat()
    relative_path = f"daily/{today}.md"
    filepath = Path(vault_path) / relative_path

    # Build the section body (content + tags)
    entry_body = f"\n\n{content}\n"
    if tags:
        entry_body += f"\n**Tags:** {', '.join(tags)}\n"
    heading = f"\n## {title}"

    # Create daily directory if needed
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not filepath.exists():
        # New file — prepend H1 date heading + first section
        full_entry = f"# {today}{heading}{entry_body}\n"
        with filepath.open("a") as f:
            f.write(full_entry)
    else:
        existing = filepath.read_text()
        if heading in existing:
            # Dedup: replace existing section body
            start = existing.index(heading)
            after_heading = existing[start + len(heading) :]
            next_h2 = after_heading.find("\n## ")
            if next_h2 == -1:
                updated = existing[:start] + heading + entry_body + "\n"
            else:
                updated = existing[:start] + heading + entry_body + "\n" + after_heading[next_h2:]
            filepath.write_text(updated)
        else:
            # New section: append
            with filepath.open("a") as f:
                f.write(f"{heading}{entry_body}\n")

    # Update log.md (but NOT index.md — daily pages aren't in the wiki index)
    log_path = Path(vault_path) / "wiki" / "log.md"
    try:
        log_entry = f"## [{today}] daily | {title}\n- Added to daily note: {title}\n"
        with log_path.open("a") as f:
            f.write(log_entry)
    except OSError as e:
        warnings.append(f"Failed to update log.md: {e}")

    return {
        "success": True,
        "filepath": relative_path,
        "warnings": warnings,
    }


def write_page(
    vault_path: str,
    kind: str,
    title: str,
    content: str,
    tags: list[str],
    config: VaultConfig | None = None,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Create a new wiki page in the vault and update index/log.

    When *config* is None (default): uses hardcoded kind-to-directory
    mappings matching DuckBrain's original layout.

    When *config* is a :class:`VaultConfig`: uses configured write rules
    for directory, frontmatter, index, and log behavior.

    Args:
        vault_path: Root path of the Obsidian vault.
        kind: Page kind — ``entity``, ``concept``, ``source``, or ``synthesis``
            (or custom kinds when using config).
        title: Page title.
        content: Markdown body content (without frontmatter).
        tags: List of tag strings.
        config: Optional vault configuration for custom page kinds.
        target_date: Override target date for daily notes (``YYYY-MM-DD``).

    Returns:
        A dict with keys ``success`` (bool), ``filepath`` (str, relative),
        and ``warnings`` (list of str).
    """
    if config is not None:
        return _write_with_config(
            vault_path,
            kind,
            title,
            content,
            tags,
            config,
            target_date=target_date,
        )

    if kind == "daily":
        return _write_daily(vault_path, title, content, tags, target_date=target_date)

    warnings: list[str] = []
    today = date.today().isoformat()

    # 1. Derive slug and subdirectory
    slug = slugify(title)
    subdir = KIND_TO_SUBDIR.get(kind, kind)
    relative_path = f"wiki/{subdir}/{slug}.md"
    filepath = Path(vault_path) / relative_path

    # 2. Generate full markdown
    frontmatter = generate_frontmatter(kind, title, tags)
    full_markdown = f"{frontmatter}\n\n{content}"

    # 3. Write file (create subdirectories if needed)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(full_markdown)

    # 4. Append to wiki/log.md
    log_path = Path(vault_path) / "wiki" / "log.md"
    try:
        log_entry = f"## [{today}] ingest | {title}\n- Created {kind}: {title}\n"
        with log_path.open("a") as f:
            f.write(log_entry)
    except OSError as e:
        warnings.append(f"Failed to update log.md: {e}")

    # 5. Update wiki/index.md
    index_path = Path(vault_path) / "wiki" / "index.md"
    try:
        section_name = KIND_TO_SECTION.get(kind, kind.capitalize())
        section_header = f"## {section_name}"
        index_entry = f"- [[{title}]] - {title}"

        content_bytes = index_path.read_text()
        lines = content_bytes.splitlines(keepends=True)

        new_lines: list[str] = []
        inserted = False
        in_section = False

        for i, line in enumerate(lines):
            if line.rstrip() == section_header:
                in_section = True
                new_lines.append(line)
                continue

            if in_section:
                # Check if this line starts a new section (next ## header)
                if line.startswith("## ") and line.rstrip() != section_header:
                    # Insert before the next section header
                    new_lines.append(index_entry + "\n")
                    inserted = True
                    in_section = False
                elif i == len(lines) - 1:
                    # Last line — append entry after it
                    new_lines.append(line)
                    if not line.endswith("\n"):
                        new_lines.append("\n")
                    new_lines.append(index_entry + "\n")
                    inserted = True
                    in_section = False
                    continue

            new_lines.append(line)

        # If we never found a boundary, append at the end
        if in_section and not inserted:
            new_lines.append(index_entry + "\n")

        if inserted or in_section:
            index_path.write_text("".join(new_lines))
        else:
            warnings.append(f"Section '{section_header}' not found in index.md")

    except OSError as e:
        warnings.append(f"Failed to update index.md: {e}")

    # 6. Update wiki/tags.md
    try:
        build_tags_index(vault_path)
    except Exception as e:
        warnings.append(f"Failed to update tags.md: {e}")

    return {
        "success": True,
        "filepath": relative_path,
        "warnings": warnings,
    }


def _write_with_config(
    vault_path: str,
    kind: str,
    title: str,
    content: str,
    tags: list[str],
    config: VaultConfig,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Write a page using configured write rules."""
    warnings: list[str] = []
    today = target_date if target_date else date.today().isoformat()
    resolver = TemplateResolver()

    # Look up the write rule for this kind
    rule = config.write_rules.get(kind)
    if rule is None:
        rule = config.write_default

    # Resolve directory and filename
    directory = resolver.resolve(rule.directory_template, kind, title, tags)
    filename = resolver.resolve(rule.filename_template, kind, title, tags)
    relative_path = f"{directory}{filename}"

    filepath = Path(vault_path) / relative_path
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if rule.mode == "append":
        # Append mode — add content to existing file
        entry = f"\n## {title}\n\n{content}\n"
        if tags and rule.frontmatter is False:
            entry += f"\n**Tags:** {', '.join(tags)}\n"

        if not filepath.exists():
            entry = f"# {today}\n{entry}"

        with filepath.open("a") as f:
            f.write(entry)
    else:
        # Create mode — write new file with optional frontmatter
        if rule.frontmatter and rule.frontmatter_fields:
            fm_dict: dict[str, Any] = {}
            for field_name, field_template in rule.frontmatter_fields.items():
                resolved = resolver.resolve(field_template, kind, title, tags)
                # Tags should be a list in frontmatter, not a comma string
                if field_name == "tags" and field_template == "{tags}":
                    fm_dict[field_name] = tags
                else:
                    fm_dict[field_name] = resolved
            fm_yaml = yaml.dump(fm_dict, default_flow_style=False, allow_unicode=True)
            full_markdown = f"---\n{fm_yaml}---\n\n{content}"
        else:
            full_markdown = content
        filepath.write_text(full_markdown)

    # Update log.md
    if rule.update_log:
        log_path = Path(vault_path) / "wiki" / "log.md"
        try:
            log_format = rule.log_entry_format or (
                "## [{date}] ingest | {title}\n- Created {kind}: {title}\n"
            )
            log_entry = resolver.resolve(log_format, kind, title, tags)
            with log_path.open("a") as f:
                f.write(log_entry)
        except OSError as e:
            warnings.append(f"Failed to update log.md: {e}")

    # Update index.md
    if rule.update_index and rule.index_section:
        index_path = Path(vault_path) / "wiki" / "index.md"
        try:
            section_name = resolver.resolve(rule.index_section, kind, title, tags)
            # Fall back to old KIND_TO_SECTION mapping for backward compat
            if section_name == kind.capitalize() and kind in KIND_TO_SECTION:
                section_name = KIND_TO_SECTION[kind]
            section_header = f"## {section_name}"
            index_entry = f"- [[{title}]] - {title}"

            index_content = index_path.read_text()
            lines = index_content.splitlines(keepends=True)

            new_lines: list[str] = []
            inserted = False
            in_section = False

            for i, line in enumerate(lines):
                if line.rstrip() == section_header:
                    in_section = True
                    new_lines.append(line)
                    continue
                if in_section:
                    if line.startswith("## ") and line.rstrip() != section_header:
                        new_lines.append(index_entry + "\n")
                        inserted = True
                        in_section = False
                    elif i == len(lines) - 1:
                        new_lines.append(line)
                        if not line.endswith("\n"):
                            new_lines.append("\n")
                        new_lines.append(index_entry + "\n")
                        inserted = True
                        in_section = False
                        continue
                new_lines.append(line)

            if in_section and not inserted:
                new_lines.append(index_entry + "\n")

            if inserted or in_section:
                index_path.write_text("".join(new_lines))
            else:
                warnings.append(f"Section '{section_header}' not found in index.md")
        except OSError as e:
            warnings.append(f"Failed to update index.md: {e}")

    # Update tags.md
    try:
        build_tags_index(vault_path, config=config)
    except Exception as e:
        warnings.append(f"Failed to update tags.md: {e}")

    return {
        "success": True,
        "filepath": relative_path,
        "warnings": warnings,
    }


def build_tags_index(vault_path: str, config: VaultConfig | None = None) -> None:
    """Regenerate wiki/tags.md with all unique tags across wiki pages.

    When *config* is None (default): scans hardcoded subdirectories
    (wiki/{entities,concepts,sources,synthesis}/) with hardcoded
    excluded tags.

    When *config* is a :class:`VaultConfig`: derives scan directories
    from config.scan_patterns and uses per-kind or default excluded_tags.
    """
    # Determine excluded tags
    if config is not None and config.write_default.excluded_tags is not None:
        excluded_tags: set[str] = set(config.write_default.excluded_tags)
    else:
        excluded_tags = {"source", "concept", "entity", "synthesis", "clippings"}

    tag_counts: dict[str, int] = {}
    wiki_path = Path(vault_path) / "wiki"

    # Determine which subdirs to scan
    if config is not None:
        # Derive directories from scan patterns
        subdirs: set[str] = set()
        for pat in config.scan_patterns:
            # Extract the directory from the glob pattern
            # pattern like "wiki/projects/*.md" → "wiki/projects"
            parts = pat.glob.rsplit("/", 1)[0]  # everything before /*
            # Remove "wiki/" prefix if present
            if parts.startswith("wiki/"):
                parts = parts[5:]
            if parts:
                subdirs.add(parts)
    else:
        subdirs = {"entities", "concepts", "sources", "synthesis"}

    for subdir in subdirs:
        dir_path = wiki_path / subdir
        if not dir_path.is_dir():
            continue
        for md_file in dir_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            meta, _ = parse_frontmatter(content)
            tags = meta.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    cleaned = str(tag).strip().strip("\"'")
                    if cleaned and cleaned.lower() not in excluded_tags:
                        tag_counts[cleaned] = tag_counts.get(cleaned, 0) + 1

    tags_path = wiki_path / "tags.md"
    if tag_counts:
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        tag_list = ", ".join(f"{tag} ({count})" for tag, count in sorted_tags)
        tags_content = f"# Vault Tags\n\n{tag_list}\n"
    else:
        tags_content = "# Vault Tags\n\nNo tags found.\n"

    tags_path.write_text(tags_content)
