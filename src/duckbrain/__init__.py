"""DuckBrain — DuckDB-backed MCP memory server for Obsidian vaults."""

from dataclasses import dataclass, field


@dataclass
class PageMetadata:
    """Parsed metadata and body from a single wiki markdown page."""

    filepath: str
    title: str
    kind: str  # entity, concept, source, synthesis
    tags: list[str] = field(default_factory=list)
    body: str = ""
    created: str = ""
    updated: str = ""


@dataclass
class SearchResult:
    """A single FTS search hit."""

    title: str
    kind: str
    filepath: str
    snippet: str
    score: float | None = None
    created: str = ""
    updated: str = ""
    matched_tags: list[str] = field(default_factory=list)


@dataclass
class WriteResult:
    """Result of a vault_write operation."""

    success: bool
    filepath: str
    warnings: list[str] = field(default_factory=list)
