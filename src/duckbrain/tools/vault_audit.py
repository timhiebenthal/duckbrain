"""MCP tool: vault_audit — diagnostic vault structure scanner.

Scans the vault and reports its current structure: directories,
frontmatter patterns, date conventions, and page kinds present.
"""

import re
from pathlib import Path
from typing import Any

from duckbrain.scanner import parse_frontmatter

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def handle_vault_audit(vault_path: str) -> dict[str, Any]:
    """Audit vault structure: detect directories, frontmatter patterns,
    date conventions, and page kinds for config design.

    Args:
        vault_path: Root path of the Obsidian vault.

    Returns:
        Dict with ``config_exists``, ``directories``, and ``summary``.
    """
    vault = Path(vault_path)
    config_exists = (vault / "duckbrain.config.json").is_file()

    # Find all .md files, group by directory
    dir_files: dict[str, list[Path]] = {}
    for md_file in vault.glob("**/*.md"):
        rel_dir = str(md_file.relative_to(vault).parent)
        if rel_dir == ".":
            rel_dir = ""
        else:
            rel_dir = rel_dir + "/"
        dir_files.setdefault(rel_dir, []).append(md_file)

    directories: list[dict[str, Any]] = []
    all_item_types: set[str] = set()
    known_dirs: list[str] = []
    unknown_dirs: list[str] = []
    has_dailies = False
    total_pages = 0

    for dir_path, files in sorted(dir_files.items()):
        total_pages += len(files)
        frontmatter_count = 0
        field_counter: dict[str, int] = {}
        item_type_values: set[str] = set()
        date_filenames = 0

        for f in files:
            try:
                content = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            meta, _ = parse_frontmatter(content)
            if meta:
                frontmatter_count += 1
                for key in meta:
                    field_counter[key] = field_counter.get(key, 0) + 1
                it = meta.get("item-type")
                if it:
                    item_type_values.add(str(it))
                    all_item_types.add(str(it))

            if _DATE_RE.match(f.stem):
                date_filenames += 1

        pct_fm = round(100.0 * frontmatter_count / len(files)) if files else 0
        # Top 5 common fields
        common_fields = sorted(
            field_counter.items(),
            key=lambda x: -x[1],
        )[:5]
        # Heuristic kinds
        heuristic_kinds: list[str] = []
        if date_filenames == len(files) and len(files) > 0:
            heuristic_kinds.append("daily")
            has_dailies = True

        dir_info = {
            "path": dir_path,
            "file_count": len(files),
            "filename_pattern": (
                "YYYY-MM-DD.md" if date_filenames == len(files) and files else "slug.md"
            ),
            "frontmatter": {
                "pct_with_frontmatter": pct_fm,
                "common_fields": [{"field": f, "count": c} for f, c in common_fields],
            },
            "item_type_values": sorted(item_type_values),
            "heuristic_kinds": heuristic_kinds,
        }
        directories.append(dir_info)

        if heuristic_kinds:
            known_dirs.append(dir_path)
        elif item_type_values:
            known_dirs.append(dir_path)
        elif dir_path and dir_path != "wiki/":
            # Directories with .md files but no recognized structure are unknown
            unknown_dirs.append(dir_path)

    return {
        "config_exists": config_exists,
        "directories": directories,
        "summary": {
            "total_pages": total_pages,
            "known_kinds": sorted(all_item_types),
            "unknown_dirs": unknown_dirs,
            "has_dailies": has_dailies,
            "has_config": config_exists,
        },
    }
