"""Tests for duckbrain.writer — page creation and vault management."""

from datetime import date
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


# ── Daily write tests ─────────────────────────────────────────────────────────


def test_write_daily_creates_file(temp_vault: Path) -> None:
    """Writing a daily entry creates daily/YYYY-MM-DD.md."""
    from duckbrain.writer import write_page

    result = write_page(
        str(temp_vault), "daily", "Debugging session",
        "Found a bug in the FTS index.",
        ["debugging", "fts"],
    )
    assert result["success"] is True
    today = date.today().isoformat()
    expected_path = f"daily/{today}.md"
    assert result["filepath"] == expected_path
    filepath = temp_vault / expected_path
    assert filepath.exists()
    content = filepath.read_text()
    assert "# Debugging session" in content
    assert "Found a bug in the FTS index." in content


def test_write_daily_has_no_frontmatter(temp_vault: Path) -> None:
    """Daily entries have NO yaml frontmatter."""
    from duckbrain.writer import write_page

    result = write_page(
        str(temp_vault), "daily", "Test entry",
        "Some content.",
        ["test"],
    )
    filepath = temp_vault / result["filepath"]
    content = filepath.read_text()
    assert "---" not in content
    assert "item-type" not in content


def test_write_daily_appends(temp_vault: Path) -> None:
    """Second write to same day appends, does not overwrite."""
    from duckbrain.writer import write_page

    today = date.today().isoformat()
    # First write
    write_page(str(temp_vault), "daily", "First entry", "Content one.", ["a"])
    # Second write
    write_page(str(temp_vault), "daily", "Second entry", "Content two.", ["b"])
    # Read file
    filepath = temp_vault / f"daily/{today}.md"
    content = filepath.read_text()
    assert "First entry" in content
    assert "Content one." in content
    assert "Second entry" in content
    assert "Content two." in content
    # First entry should appear before second
    assert content.index("First entry") < content.index("Second entry")


def test_write_daily_updates_log(temp_vault: Path) -> None:
    """Daily writes still update the log."""
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault), "daily", "Daily log test",
        "Testing log update.",
        ["test"],
    )
    log_path = temp_vault / "wiki" / "log.md"
    log_content = log_path.read_text()
    assert "Daily log test" in log_content


def test_write_daily_no_index_update(temp_vault: Path) -> None:
    """Daily writes do NOT update wiki/index.md."""
    from duckbrain.writer import write_page

    index_path = temp_vault / "wiki" / "index.md"
    before = index_path.read_text()
    write_page(
        str(temp_vault), "daily", "Index test",
        "Should not appear in index.",
        ["test"],
    )
    after = index_path.read_text()
    assert before == after  # No change


def test_write_daily_dedup_merges_same_title(temp_vault: Path) -> None:
    """Writing same title twice merges, not duplicates."""
    from duckbrain.writer import write_page

    today = date.today().isoformat()
    write_page(str(temp_vault), "daily", "Dup test", "Version one.", ["a"])
    write_page(str(temp_vault), "daily", "Dup test", "Version two.", ["b"])
    filepath = temp_vault / f"daily/{today}.md"
    content = filepath.read_text()
    assert content.count("## Dup test") == 1, (
        f"Expected 1 heading, got {content.count('## Dup test')}"
    )
    assert "Version two." in content
    assert "Version one." not in content


def test_write_daily_target_date_writes_past_file(temp_vault: Path) -> None:
    """target_date writes to a specific date's file, not today."""
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault), "daily", "Past entry", "Yesterday content.", ["tag"],
        target_date="2025-01-15",
    )
    filepath = temp_vault / "daily/2025-01-15.md"
    assert filepath.exists()
    content = filepath.read_text()
    assert "# 2025-01-15" in content
    assert "Past entry" in content
    assert "Yesterday content." in content
    today = date.today().isoformat()
    assert not (temp_vault / f"daily/{today}.md").exists()


def test_handle_vault_write_target_date(temp_vault: Path) -> None:
    """handle_vault_write passes target_date through to writer."""
    from duckbrain.tools.vault_write import handle_vault_write

    result = handle_vault_write(
        str(temp_vault), "daily", "Tool past entry", "Tool content.", ["t"],
        target_date="2025-06-01",
    )
    assert result["success"] is True
    filepath = temp_vault / "daily/2025-06-01.md"
    assert filepath.exists()
    assert "Tool past entry" in filepath.read_text()


# ── build_tags_index tests ────────────────────────────────────────────────────


def test_build_tags_index_basic(tmp_path: Path) -> None:
    """build_tags_index extracts unique tags with counts from all wiki pages."""
    from duckbrain.writer import build_tags_index

    vault = tmp_path / "test-vault"
    vault.mkdir()
    (vault / "wiki").mkdir()

    # Create two pages with different tags
    (vault / "wiki" / "entities").mkdir()
    (vault / "wiki" / "entities" / "page-a.md").write_text(
        "---\ntitle: Page A\nitem-type: entity\ntags: [ai, memory, mcp]\n---\n\n# Page A\n"
    )
    (vault / "wiki" / "concepts").mkdir()
    (vault / "wiki" / "concepts" / "page-b.md").write_text(
        "---\ntitle: Page B\nitem-type: concept\ntags: [ai, duckdb, plugin]\n---\n\n# Page B\n"
    )

    build_tags_index(str(vault))

    tags_path = vault / "wiki" / "tags.md"
    assert tags_path.exists()
    content = tags_path.read_text()
    assert "ai (2)" in content
    assert "memory (1)" in content
    assert "duckdb (1)" in content


def test_build_tags_index_sorted(temp_vault: Path) -> None:
    """Tags sorted by frequency descending, then alphabetically for ties."""
    from duckbrain.writer import build_tags_index

    (temp_vault / "wiki" / "entities").mkdir(parents=True, exist_ok=True)
    # apple appears in 3 pages, mango in 2, zebra in 1
    (temp_vault / "wiki" / "entities" / "x.md").write_text(
        "---\ntitle: X\nitem-type: entity\ntags: [zebra, apple, mango]\n---\n\n# X\n"
    )
    (temp_vault / "wiki" / "entities" / "y.md").write_text(
        "---\ntitle: Y\nitem-type: entity\ntags: [apple, mango]\n---\n\n# Y\n"
    )
    (temp_vault / "wiki" / "entities" / "z.md").write_text(
        "---\ntitle: Z\nitem-type: entity\ntags: [apple]\n---\n\n# Z\n"
    )

    build_tags_index(str(temp_vault))

    content = (temp_vault / "wiki" / "tags.md").read_text()
    # apple (3) before mango (2) before zebra (1)
    assert content.index("apple (3)") < content.index("mango (2)") < content.index("zebra (1)")


def test_build_tags_index_empty_vault(tmp_path: Path) -> None:
    """Empty vault produces tags.md with no tags."""
    from duckbrain.writer import build_tags_index

    vault = tmp_path / "empty-vault"
    vault.mkdir()
    (vault / "wiki").mkdir()

    build_tags_index(str(vault))

    tags_path = vault / "wiki" / "tags.md"
    assert tags_path.exists()
    content = tags_path.read_text()
    assert "No tags found" in content


def test_build_tags_index_deduplicates(tmp_path: Path) -> None:
    """Same tag across multiple pages appears once with correct count."""
    from duckbrain.writer import build_tags_index

    vault = tmp_path / "test-vault"
    vault.mkdir()
    (vault / "wiki").mkdir()

    (vault / "wiki" / "entities").mkdir()
    (vault / "wiki" / "entities" / "a.md").write_text(
        "---\ntitle: A\nitem-type: entity\ntags: [ai, memory]\n---\n\n# A\n"
    )
    (vault / "wiki" / "concepts").mkdir()
    (vault / "wiki" / "concepts" / "b.md").write_text(
        "---\ntitle: B\nitem-type: concept\ntags: [ai, duckdb]\n---\n\n# B\n"
    )

    build_tags_index(str(vault))

    content = (vault / "wiki" / "tags.md").read_text()
    assert "ai (2)" in content
    assert content.count("ai") == 1


def test_write_page_updates_tags(temp_vault: Path) -> None:
    """write_page triggers tags.md update with correct counts."""
    from duckbrain.writer import write_page

    # Create initial page
    write_page(str(temp_vault), "entity", "Page One", "Body", ["alpha", "beta"])

    tags_path = temp_vault / "wiki" / "tags.md"
    assert tags_path.exists()
    content = tags_path.read_text()
    assert "alpha (1)" in content
    assert "beta (1)" in content

    # Create second page with overlapping + new tags
    write_page(str(temp_vault), "concept", "Page Two", "Body", ["beta", "gamma"])

    content = tags_path.read_text()
    assert "alpha (1)" in content
    assert "beta (2)" in content  # beta now appears in 2 pages
    assert "gamma (1)" in content


# ── Config-driven write tests ──────────────────────────────────────────────────


def test_write_page_with_custom_config(tmp_path: Path) -> None:
    """write_page with config creates files in configured directories."""
    from duckbrain.config import WriteRule, VaultConfig
    from duckbrain.writer import write_page

    vault = tmp_path / "vault"
    wiki = vault / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "index.md").write_text("# Index\n\n## Projects\n\n")
    (wiki / "log.md").write_text("# Log\n\n")

    config = VaultConfig(
        write_rules={
            "project": WriteRule(
                mode="create",
                directory_template="wiki/projects/",
                filename_template="{slug}.md",
                frontmatter=True,
                index_section="Projects",
            ),
        },
    )

    result = write_page(
        str(vault), "project", "My Project", "Project body", ["tag1"], config=config,
    )

    assert result["success"] is True
    assert "wiki/projects/my-project.md" in result["filepath"]

    # Verify file exists with correct content
    written = (vault / "wiki" / "projects" / "my-project.md").read_text()
    assert "---" in written  # has frontmatter
    assert "title: My Project" in written
    assert "item-type: project" in written
    assert "Project body" in written

    # Verify index.md updated under correct section
    index = (wiki / "index.md").read_text()
    assert "[[My Project]]" in index


def test_write_page_no_config_unchanged(temp_vault: Path) -> None:
    """write_page without config creates same files as before."""
    from duckbrain.writer import write_page

    result = write_page(str(temp_vault), "entity", "Test Entity", "Body", [])

    assert result["success"] is True
    assert "wiki/entities/test-entity.md" in result["filepath"]
    assert (temp_vault / "wiki" / "entities" / "test-entity.md").exists()


def test_write_page_append_mode(tmp_path: Path) -> None:
    """write_page with mode='append' appends to existing file."""
    from duckbrain.config import WriteRule, VaultConfig
    from duckbrain.writer import write_page

    vault = tmp_path / "vault"
    log_dir = vault / "wiki" / "log"
    log_dir.mkdir(parents=True)
    (vault / "wiki" / "index.md").write_text("")
    (vault / "wiki" / "log.md").write_text("")

    today = date.today().isoformat()
    log_file = log_dir / f"{today}.md"
    log_file.write_text(f"# {today}\n")

    config = VaultConfig(
        write_rules={
            "log": WriteRule(
                mode="append",
                directory_template="wiki/log/",
                filename_template="{date}.md",
                frontmatter=False,
                update_index=False,
                index_section=None,
            ),
        },
    )

    result = write_page(
        str(vault), "log", "Entry Title", "Entry body", ["log-tag"], config=config,
    )

    assert result["success"] is True
    content = log_file.read_text()
    assert "Entry Title" in content
    assert "Entry body" in content
    assert "log-tag" in content


# ── TemplateResolver tests ────────────────────────────────────────────────────


def test_template_resolve_kind() -> None:
    """{kind}, {Kind}, {kinds} resolve correctly."""
    from duckbrain.writer import TemplateResolver

    r = TemplateResolver.resolve
    assert r("{kind}", "project", "T", []) == "project"
    assert r("{Kind}", "project", "T", []) == "Project"
    assert r("{kinds}", "project", "T", []) == "projects"


def test_template_resolve_slug() -> None:
    """{slug} and {title} resolve correctly."""
    from duckbrain.writer import TemplateResolver

    r = TemplateResolver.resolve
    assert r("{slug}", "entity", "My Project", []) == "my-project"
    assert r("{title}", "entity", "My Project", []) == "My Project"


def test_template_resolve_date() -> None:
    """{date} resolves to today's ISO date."""
    from datetime import date

    from duckbrain.writer import TemplateResolver

    r = TemplateResolver.resolve
    result = r("{date}", "x", "T", [])
    assert result == date.today().isoformat()


def test_template_no_substitution() -> None:
    """String with no templates returned unchanged."""
    from duckbrain.writer import TemplateResolver

    r = TemplateResolver.resolve
    assert r("hello world", "x", "T", []) == "hello world"


# ── Config-driven frontmatter tests ───────────────────────────────────────────


def test_generate_frontmatter_custom_fields(tmp_path: Path) -> None:
    """write_page uses config frontmatter_fields when provided."""
    from duckbrain.config import WriteRule, VaultConfig
    from duckbrain.writer import write_page

    vault = tmp_path / "vault"
    wiki = vault / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "index.md").write_text("")
    (wiki / "log.md").write_text("")

    config = VaultConfig(
        write_rules={
            "project": WriteRule(
                mode="create",
                directory_template="wiki/projects/",
                filename_template="{slug}.md",
                frontmatter=True,
                frontmatter_fields={
                    "title": "{title}",
                    "status": "active",
                },
                update_index=False,
                index_section=None,
            ),
        },
    )

    write_page(
        str(vault), "project", "My Project", "Body", ["tag1"], config=config,
    )

    written = (vault / "wiki" / "projects" / "my-project.md").read_text()
    assert "title: My Project" in written
    assert "status: active" in written
    assert "item-type" not in written  # not in custom fields


def test_generate_frontmatter_no_frontmatter(tmp_path: Path) -> None:
    """write_page with frontmatter=False generates no YAML block."""
    from duckbrain.config import WriteRule, VaultConfig
    from duckbrain.writer import write_page

    vault = tmp_path / "vault"
    wiki = vault / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "index.md").write_text("")
    (wiki / "log.md").write_text("")

    config = VaultConfig(
        write_rules={
            "note": WriteRule(
                mode="create",
                directory_template="wiki/notes/",
                filename_template="{slug}.md",
                frontmatter=False,
                update_index=False,
                index_section=None,
            ),
        },
    )

    write_page(
        str(vault), "note", "Plain Note", "No frontmatter here", [], config=config,
    )

    written = (vault / "wiki" / "notes" / "plain-note.md").read_text()
    assert "---" not in written
    assert written == "No frontmatter here"


# ── Config-aware build_tags_index tests ───────────────────────────────────────


def test_build_tags_index_with_config_scan_paths(tmp_path: Path) -> None:
    """build_tags_index uses config scan patterns instead of hardcoded subdirs."""
    from duckbrain.config import ScanPattern, VaultConfig
    from duckbrain.writer import build_tags_index

    vault = tmp_path / "vault"
    projects = vault / "wiki" / "projects"
    projects.mkdir(parents=True)
    notes = vault / "wiki" / "notes"
    notes.mkdir(parents=True)

    (projects / "p1.md").write_text(
        "---\ntitle: P1\ntags: [alpha, beta]\n---\n\nBody\n",
    )
    (notes / "n1.md").write_text(
        "---\ntitle: N1\ntags: [gamma]\n---\n\nBody\n",
    )

    config = VaultConfig(
        scan_patterns=[
            ScanPattern(glob="wiki/projects/*.md", kind="project"),
            ScanPattern(glob="wiki/notes/*.md", kind="note"),
        ],
    )

    build_tags_index(str(vault), config=config)

    tags_content = (vault / "wiki" / "tags.md").read_text()
    assert "alpha" in tags_content
    assert "beta" in tags_content
    assert "gamma" in tags_content


def test_build_tags_index_with_config_excluded_tags(tmp_path: Path) -> None:
    """build_tags_index excludes tags specified in config."""
    from duckbrain.config import ScanPattern, VaultConfig, WriteRule
    from duckbrain.writer import build_tags_index

    vault = tmp_path / "vault"
    projects = vault / "wiki" / "projects"
    projects.mkdir(parents=True)

    (projects / "p1.md").write_text(
        "---\ntitle: P1\ntags: [foo, bar, baz]\n---\n\nBody\n",
    )

    config = VaultConfig(
        scan_patterns=[
            ScanPattern(glob="wiki/projects/*.md", kind="project"),
        ],
        write_default=WriteRule(excluded_tags=["foo"]),
    )

    build_tags_index(str(vault), config=config)

    tags_content = (vault / "wiki" / "tags.md").read_text()
    assert "foo" not in tags_content
    assert "bar" in tags_content
    assert "baz" in tags_content


def test_build_tags_index_no_config_unchanged(temp_vault: Path) -> None:
    """build_tags_index without config scans same 4 dirs as today."""
    from duckbrain.writer import build_tags_index

    build_tags_index(str(temp_vault))

    tags_path = temp_vault / "wiki" / "tags.md"
    assert tags_path.exists()
    content = tags_path.read_text()
    # Fixture pages have tags like 'ai', 'agent-memory', 'mcp' etc.
    assert "ai" in content
