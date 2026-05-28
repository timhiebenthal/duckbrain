"""Tests for duckbrain.writer — page creation and vault management."""

from pathlib import Path


# ── slugify tests ──────────────────────────────────────────────────────────────


def test_slugify_basic() -> None:
    """'Claude Mem' → 'claude-mem'."""
    from duckbrain.writer import slugify

    assert slugify("Claude Mem") == "claude-mem"


def test_slugify_special_chars() -> None:
    """'BI's Second Unbundling' → 'bis-second-unbundling'."""
    from duckbrain.writer import slugify

    assert slugify("BI's Second Unbundling") == "bis-second-unbundling"


def test_slugify_parens() -> None:
    """'Open Brain (OB1)' → 'open-brain-ob1'."""
    from duckbrain.writer import slugify

    assert slugify("Open Brain (OB1)") == "open-brain-ob1"


def test_slugify_multiple_spaces() -> None:
    """'Agent   Memory' → 'agent-memory'."""
    from duckbrain.writer import slugify

    assert slugify("Agent   Memory") == "agent-memory"


# ── generate_frontmatter tests ────────────────────────────────────────────────


def _parse_yaml_block(text: str) -> dict:
    """Helper to extract and parse YAML from frontmatter block.

    Expects text with ``---`` delimiters at the start and end of
    the YAML block (the content after the closing ``---`` is ignored).
    """
    import yaml

    lines = text.splitlines()
    # Find the first "---" (line 0) and the second "---" that closes frontmatter
    end_marker = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_marker = i
            break
    if end_marker is None:
        return {}
    yaml_lines = lines[1:end_marker]
    return yaml.safe_load("\n".join(yaml_lines))


def test_generate_frontmatter_entity() -> None:
    """generate_frontmatter with kind='entity' produces correct YAML block."""
    from duckbrain.writer import generate_frontmatter

    result = generate_frontmatter("entity", "Claude Mem", ["ai", "memory"])

    # Should be a YAML block wrapped in ---
    assert result.startswith("---\n")
    assert result.endswith("\n---")

    # Parse the YAML and check keys
    data = _parse_yaml_block(result)

    assert data["title"] == "Claude Mem"
    assert data["item-type"] == "entity"
    assert data["tags"] == ["ai", "memory"]
    assert "created" in data
    assert "updated" in data
    # created and updated should be today's date
    from datetime import date

    today = date.today().isoformat()
    assert data["created"] == today
    assert data["updated"] == today


def test_generate_frontmatter_concept() -> None:
    """generate_frontmatter with kind='concept' sets item-type to 'concept'."""
    from duckbrain.writer import generate_frontmatter

    result = generate_frontmatter("concept", "Test Concept", ["test"])
    data = _parse_yaml_block(result)

    assert data["item-type"] == "concept"
    assert data["title"] == "Test Concept"


# ── write_page tests ──────────────────────────────────────────────────────────


def _today() -> str:
    """Return today's date as YYYY-MM-DD string."""
    from datetime import date

    return date.today().isoformat()


def test_write_page_creates_file(temp_vault: Path) -> None:
    """write_page creates a markdown file at the correct path with frontmatter."""
    from duckbrain.writer import write_page

    result = write_page(
        str(temp_vault),
        kind="entity",
        title="Test Entity",
        content="# Test Entity\n\nHello world.",
        tags=["test"],
    )

    assert result["success"] is True

    # File should exist at wiki/entities/test-entity.md
    filepath = temp_vault / "wiki" / "entities" / "test-entity.md"
    assert filepath.exists(), f"File {filepath} was not created"

    content = filepath.read_text()

    # Should start with frontmatter
    assert content.startswith("---\n")
    # Should contain the content body
    assert "# Test Entity" in content
    assert "Hello world." in content

    # Verify frontmatter is correct
    data = _parse_yaml_block(content)
    assert data["title"] == "Test Entity"
    assert data["item-type"] == "entity"
    assert data["tags"] == ["test"]
    assert data["created"] == _today()
    assert data["updated"] == _today()

    # Returned filepath should be relative
    assert "test-entity.md" in result["filepath"]
    assert result["warnings"] == []


def test_write_page_updates_index(temp_vault: Path) -> None:
    """write_page adds an entry to index.md under the correct section."""
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault),
        kind="entity",
        title="Test Entity",
        content="# Test Entity\n\nHello world.",
        tags=["test"],
    )

    index = (temp_vault / "wiki" / "index.md").read_text()

    # Should find the entity under ## Entities
    assert "## Entities" in index
    assert "- [[Test Entity]] - Test Entity" in index


def test_write_page_updates_log(temp_vault: Path) -> None:
    """write_page appends a log entry to log.md."""
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault),
        kind="entity",
        title="Test Entity",
        content="# Test Entity\n\nHello world.",
        tags=["test"],
    )

    log = (temp_vault / "wiki" / "log.md").read_text()

    # Should contain today's date in a log header
    today = _today()
    assert f"## [{today}] ingest | Test Entity" in log
    assert "- Created entity: Test Entity" in log


def test_write_page_concept_section(temp_vault: Path) -> None:
    """write_page of kind 'concept' updates ## Concepts section, not Entities."""
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault),
        kind="concept",
        title="Test Concept",
        content="# Test Concept\n\nA concept.",
        tags=["test-concept"],
    )

    index = (temp_vault / "wiki" / "index.md").read_text()

    # Should be under Concepts, not Entities
    assert "- [[Test Concept]] - Test Concept" in index
    # Find which section it's under
    entities_idx = index.index("## Entities")
    concepts_idx = index.index("## Concepts")
    concept_entry_idx = index.index("- [[Test Concept]] - Test Concept")
    # The entry should be after ## Concepts, not after ## Entities
    assert concept_entry_idx > concepts_idx, "Entry should be after ## Concepts"
    assert concept_entry_idx < index.index("## Sources", concepts_idx), (
        "Entry should be before ## Sources"
    )


def test_write_page_synthesis_section(temp_vault: Path) -> None:
    """write_page of kind 'synthesis' updates ## Synthesis section."""
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault),
        kind="synthesis",
        title="Test Synthesis",
        content="# Test Synthesis\n\nA synthesis.",
        tags=["test-synthesis"],
    )

    index = (temp_vault / "wiki" / "index.md").read_text()

    assert "- [[Test Synthesis]] - Test Synthesis" in index
    # Should be after ## Synthesis
    synthesis_idx = index.index("## Synthesis")
    entry_idx = index.index("- [[Test Synthesis]] - Test Synthesis")
    assert entry_idx > synthesis_idx


def test_write_page_index_append_not_overwrite(temp_vault: Path) -> None:
    """Existing index entries survive; new entry is appended, not replacing."""
    from duckbrain.writer import write_page

    # Verify existing entries exist
    index_before = (temp_vault / "wiki" / "index.md").read_text()
    assert "- [[Jason Ganz]]" in index_before
    assert "- [[Jagged Frontier]]" in index_before

    write_page(
        str(temp_vault),
        kind="entity",
        title="Test Entity",
        content="# Test Entity\n\nHello world.",
        tags=["test"],
    )

    index_after = (temp_vault / "wiki" / "index.md").read_text()

    # Old entries survive
    assert "- [[Jason Ganz]] - Author of Jagged Frontier dispatch" in index_after
    assert "- [[Jagged Frontier]] - Uneven LLM capability across tasks" in index_after
    # New entry present
    assert "- [[Test Entity]] - Test Entity" in index_after


# ── Edge case tests ──────────────────────────────────────────────────────────


def test_write_page_log_failure(temp_vault: Path, monkeypatch) -> None:
    """When log append fails, write_page still succeeds with a warning."""
    from duckbrain.writer import write_page

    original_open = Path.open

    def guarded_open(self, mode="r", *args, **kwargs):
        if "log.md" in str(self) and ("a" in mode or "w" in mode):
            raise PermissionError("Permission denied")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    result = write_page(
        str(temp_vault),
        kind="entity",
        title="Log Failure Test",
        content="# Log Failure Test\n\nShould still create file.",
        tags=["test"],
    )

    assert result["success"] is True
    filepath = temp_vault / "wiki" / "entities" / "log-failure-test.md"
    assert filepath.exists(), "Page file should still be created"
    assert any("log" in w.lower() for w in result["warnings"])


def test_write_page_index_failure(temp_vault: Path, monkeypatch) -> None:
    """When index update fails, write_page still succeeds with a warning."""
    from duckbrain.writer import write_page

    original_open = Path.open

    def guarded_open(self, mode="r", *args, **kwargs):
        if "index.md" in str(self) and ("a" in mode or "w" in mode):
            raise PermissionError("Permission denied")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    result = write_page(
        str(temp_vault),
        kind="entity",
        title="Index Failure Test",
        content="# Index Failure Test\n\nShould still create file.",
        tags=["test"],
    )

    assert result["success"] is True
    filepath = temp_vault / "wiki" / "entities" / "index-failure-test.md"
    assert filepath.exists(), "Page file should still be created"
    assert any("index" in w.lower() for w in result["warnings"])


def test_write_page_existing_index_preserved(temp_vault: Path) -> None:
    """After 3 writes to different kinds, all entries appear under correct sections."""
    from duckbrain.writer import write_page

    # Write entity "A"
    write_page(str(temp_vault), kind="entity", title="A", content="# A\n\nEntity A.", tags=[])
    # Write concept "B"
    write_page(str(temp_vault), kind="concept", title="B", content="# B\n\nConcept B.", tags=[])
    # Write synthesis "C"
    write_page(str(temp_vault), kind="synthesis", title="C", content="# C\n\nSynthesis C.", tags=[])

    index = (temp_vault / "wiki" / "index.md").read_text()

    # All 3 new entries present
    assert "- [[A]] - A" in index
    assert "- [[B]] - B" in index
    assert "- [[C]] - C" in index

    # Original pre-existing entries preserved
    assert "- [[Jason Ganz]]" in index
    assert "- [[Jagged Frontier]]" in index

    # Each entry is in the correct section (order: Entities < Concepts < Synthesis)
    entities_idx = index.index("## Entities")
    concepts_idx = index.index("## Concepts")
    sources_idx = index.index("## Sources")
    synthesis_idx = index.index("## Synthesis")

    a_idx = index.index("- [[A]] - A")
    b_idx = index.index("- [[B]] - B")
    c_idx = index.index("- [[C]] - C")

    assert entities_idx < a_idx < concepts_idx, "A should be under Entities"
    assert concepts_idx < b_idx < sources_idx, "B should be under Concepts"
    assert synthesis_idx < c_idx, "C should be under Synthesis"
