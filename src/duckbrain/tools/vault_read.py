"""MCP tool: vault_read — read a page by title or filepath."""

from pathlib import Path
from typing import Any

from duckbrain.config import VaultConfig
from duckbrain.scanner import scan_vault


def handle_vault_read(
    vault_path: str,
    title: str | None = None,
    filepath: str | None = None,
    config: VaultConfig | None = None,
) -> dict[str, Any]:
    """Read a wiki or daily page by title or filepath."""
    # filepath takes priority — direct read, no scan needed
    if filepath:
        full_path = Path(vault_path) / filepath
        if not full_path.is_file():
            return {"error": f"File not found: {filepath}"}

        content = full_path.read_text(encoding="utf-8")
        title_from_file = filepath.rsplit("/", 1)[-1].removesuffix(".md")

        # Derive kind from config if available
        kind: str = "wiki"
        if config is not None:
            for pattern in config.scan_patterns:
                if full_path.match(pattern.glob.replace("*.md", "") + full_path.name):
                    kind = pattern.kind
                    break
        else:
            kind = "daily" if filepath.startswith("daily/") else "wiki"

        return {
            "title": title_from_file,
            "kind": kind,
            "filepath": filepath,
            "content": content,
            "tags": [],
            "created": "",
            "updated": "",
        }

    # title lookup — scan and find match
    if title:
        pages = scan_vault(vault_path, config=config)
        title_lower = title.strip().lower()

        for page in pages:
            if page.title.lower() == title_lower:
                full_path = Path(vault_path) / page.filepath
                if full_path.is_file():
                    return {
                        "title": page.title,
                        "kind": page.kind,
                        "filepath": page.filepath,
                        "content": full_path.read_text(encoding="utf-8"),
                        "tags": page.tags,
                        "created": page.created,
                        "updated": page.updated,
                    }

        return {"error": f"Page not found: {title}"}

    return {"error": "Provide either title or filepath"}
