"""Test fixtures for DuckBrain."""

from pathlib import Path

import pytest

from duckbrain import PageMetadata


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create a temporary Obsidian-like vault with wiki structure.

    Returns the vault root path (parent of wiki/).
    """
    vault = tmp_path / "test-vault"
    wiki = vault / "wiki"

    # Create wiki subdirectories
    for subdir in ["entities", "concepts", "sources", "synthesis"]:
        (wiki / subdir).mkdir(parents=True)

    # Create daily/ subdirectory with a sample daily note
    daily_dir = vault / "daily"
    daily_dir.mkdir(parents=True)
    daily_content = "# 2026-05-28\n\nWorked on DuckBrain MCP server.\n"
    (daily_dir / "2026-05-28.md").write_text(daily_content)

    # Create index.md with all four section headers
    index_content = """# Wiki Index

## Entities
- [[Jason Ganz]] - Author of Jagged Frontier dispatch

## Concepts
- [[Jagged Frontier]] - Uneven LLM capability across tasks

## Sources
- [[A Dispatch from the Jagged Frontier]] - Jason Ganz on agent capabilities

## Synthesis
- [[agent-use-data-platforms]] - Theses on agent use in data platforms
"""
    (wiki / "index.md").write_text(index_content)

    # Create empty log.md
    (wiki / "log.md").write_text("# Wiki Log\n\n")

    # Create sample entity: Claude Mem
    entity_claude_mem = """---
title: Claude Mem
item-type: entity
tags: [open-source, ai, memory, mcp]
sources:
  - wiki/sources/source - claude-mem.md
created: 2026-05-28
updated: 2026-05-28
---

# Claude Mem

Claude Mem is an MCP-based memory plugin that provides persistent memory \
across sessions for OpenCode.
"""
    (wiki / "entities" / "claude-mem.md").write_text(entity_claude_mem)

    # Create sample concept: Agent Memory Systems
    concept_memory = """---
title: Agent Memory Systems
item-type: concept
tags: [agent-memory, taxonomy, ai]
created: 2026-05-28
updated: 2026-05-28
---

# Agent Memory Systems

A 6-level taxonomy of Claude Code memory approaches. Includes DuckDB Zero-ETL, \
Memweave/SQLite, and RushDB graph+vector implementations.
"""
    (wiki / "concepts" / "agent-memory-systems.md").write_text(concept_memory)

    # Create sample concept: Jagged Frontier
    concept_jagged = """---
title: Jagged Frontier
item-type: concept
tags: [ai, llm, capability]
created: 2026-05-04
updated: 2026-05-20
---

# Jagged Frontier

Uneven LLM capability across tasks — some things are easy for AI, others unexpectedly hard.
"""
    (wiki / "concepts" / "jagged-frontier.md").write_text(concept_jagged)

    # Create sample synthesis page
    synthesis_page = """---
title: duckdb-memory-mcp-build-decision
item-type: synthesis
tags: [agent-memory, duckdb, mcp, comparison]
created: 2026-05-28
updated: 2026-05-28
---

# DuckDB Memory MCP — Build vs Existing Tools

Verdict: Build a minimal DuckDB MCP server. Existing tools fail on vault schema-aware write-back.
"""
    (wiki / "synthesis" / "duckdb-memory-mcp-build-decision.md").write_text(synthesis_page)

    # Create sample source page
    source_page = """---
title: The missing piece of the modern data stack
item-type: source
tags: [metrics-layer, mds]
created: 2026-05-20
updated: 2026-05-20
---

# The missing piece of the modern data stack

Benn Stancil on the metrics layer as the missing MDS component.
"""
    (wiki / "sources" / "the-missing-piece-of-the-modern-data-stack.md").write_text(source_page)

    return vault


@pytest.fixture
def sample_pages() -> list[PageMetadata]:
    """Return a list of sample PageMetadata objects for testing indexer.

    These match the structure produced by scan_vault().
    """
    return [
        PageMetadata(
            filepath="wiki/entities/claude-mem.md",
            title="Claude Mem",
            kind="entity",
            tags=["open-source", "ai", "memory", "mcp"],
            body=(
                "Claude Mem is an MCP-based memory plugin that provides persistent memory "
                "across sessions for OpenCode."
            ),
            created="2026-05-28",
            updated="2026-05-28",
        ),
        PageMetadata(
            filepath="wiki/concepts/agent-memory-systems.md",
            title="Agent Memory Systems",
            kind="concept",
            tags=["agent-memory", "taxonomy", "ai"],
            body="A 6-level taxonomy of Claude Code memory approaches. Includes DuckDB Zero-ETL.",
            created="2026-05-28",
            updated="2026-05-28",
        ),
        PageMetadata(
            filepath="wiki/concepts/jagged-frontier.md",
            title="Jagged Frontier",
            kind="concept",
            tags=["ai", "llm", "capability"],
            body=(
                "Uneven LLM capability across tasks — some things are easy "
                "for AI, others unexpectedly hard."
            ),
            created="2026-05-04",
            updated="2026-05-20",
        ),
        PageMetadata(
            filepath="wiki/synthesis/duckdb-memory-mcp-build-decision.md",
            title="duckdb-memory-mcp-build-decision",
            kind="synthesis",
            tags=["agent-memory", "duckdb", "mcp", "comparison"],
            body=(
                "Verdict: Build a minimal DuckDB MCP server. Existing tools fail "
                "on vault schema-aware write-back."
            ),
            created="2026-05-28",
            updated="2026-05-28",
        ),
        PageMetadata(
            filepath="wiki/sources/the-missing-piece-of-the-modern-data-stack.md",
            title="The missing piece of the modern data stack",
            kind="source",
            tags=["metrics-layer", "mds"],
            body="Benn Stancil on the metrics layer as the missing MDS component.",
            created="2026-05-20",
            updated="2026-05-20",
        ),
        PageMetadata(
            filepath="daily/2026-05-28.md",
            title="2026-05-28",
            kind="daily",
            tags=[],
            body="Worked on DuckBrain MCP server.",
            created="2026-05-28",
            updated="2026-05-28",
        ),
    ]
