"""Page creation with frontmatter generation, index/log auto-update."""

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

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


def _write_daily(
    vault_path: str,
    title: str,
    content: str,
    tags: list[str],
) -> dict[str, Any]:
    """Append a section to today's daily note.

    Daily notes live under ``daily/YYYY-MM-DD.md`` in the vault root
    (not under ``wiki/``).  They have no YAML frontmatter and are
    **appended** to — the file grows throughout the day.

    Args:
        vault_path: Root path of the Obsidian vault.
        title: Section heading for this daily entry.
        content: Markdown body content.
        tags: List of tag strings.

    Returns:
        A dict with keys ``success`` (bool), ``filepath`` (str, relative),
        and ``warnings`` (list of str).
    """
    warnings: list[str] = []
    today = date.today().isoformat()
    relative_path = f"daily/{today}.md"
    filepath = Path(vault_path) / relative_path

    # Build the entry body
    entry = f"\n## {title}\n\n{content}\n"
    if tags:
        entry += f"\n**Tags:** {', '.join(tags)}\n"

    # Create daily directory if needed
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # If file doesn't exist yet, prepend a top-level date heading
    if not filepath.exists():
        entry = f"# {today}\n{entry}"

    # Append to file (always — daily notes accumulate)
    with filepath.open("a") as f:
        f.write(entry)

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
) -> dict[str, Any]:
    """Create a new wiki page in the vault and update index/log.

    Steps:
    1. Derive slug from title → filename
    2. Map *kind* to subdirectory under ``wiki/``
    3. Generate full markdown with frontmatter
    4. Write file to disk (creating subdirectories as needed)
    5. Append log entry to ``wiki/log.md``
    6. Insert index entry in ``wiki/index.md`` under the correct section

    Args:
        vault_path: Root path of the Obsidian vault.
        kind: Page kind — ``entity``, ``concept``, ``source``, or ``synthesis``.
        title: Page title.
        content: Markdown body content (without frontmatter).
        tags: List of tag strings.

    Returns:
        A dict with keys ``success`` (bool), ``filepath`` (str, relative),
        and ``warnings`` (list of str).
    """
    if kind == "daily":
        return _write_daily(vault_path, title, content, tags)

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

    return {
        "success": True,
        "filepath": relative_path,
        "warnings": warnings,
    }
