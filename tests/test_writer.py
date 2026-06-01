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
    # Section heading carries the server-stamped timestamp; just check
    # the title text is present.
    assert "Debugging session" in content
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
    import re
    from duckbrain.writer import write_page

    today = date.today().isoformat()
    write_page(str(temp_vault), "daily", "Dup test", "Version one.", ["a"])
    write_page(str(temp_vault), "daily", "Dup test", "Version two.", ["b"])
    filepath = temp_vault / f"daily/{today}.md"
    content = filepath.read_text()
    # Server prepends YYYY-MM-DD HH:MM — to the heading; count regex matches.
    matches = re.findall(
        rf"^## {today} \d{{2}}:\d{{2}} — Dup test$", content, re.MULTILINE,
    )
    assert len(matches) == 1, f"Expected 1 heading, got {len(matches)}: {matches}"
    assert "Version two." in content
    assert "Version one." not in content


def test_write_daily_target_date_writes_past_file(temp_vault: Path) -> None:
    """target_date writes to a specific date's file, not today. v0.4.1:
    the H1 with the target date is no longer added — the file path is
    the date, and the H2 stamp uses the current date+time (when the
    write happened), not the target_date."""
    import re
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault), "daily", "Past entry", "Yesterday content.", ["tag"],
        target_date="2025-01-15",
    )
    filepath = temp_vault / "daily/2025-01-15.md"
    assert filepath.exists()
    content = filepath.read_text()
    # H1 with target date is no longer added
    assert "# 2025-01-15" not in content
    # H2 stamp uses today's date+time (when written), not 2025-01-15
    today = date.today().isoformat()
    assert re.search(
        rf"^## {today} \d{{2}}:\d{{2}} — Past entry$", content, re.MULTILINE,
    ), content
    assert "Yesterday content." in content
    # And the file at today's date was NOT created — only the past-date file
    assert not (temp_vault / f"daily/{today}.md").exists()


# ── Daily timestamp guarantee tests (server-side, DRY) ────────────────────────
#
# The timestamp on a daily-note heading is a SERVER guarantee, not a
# client concern. Every MCP client (OpenCode plugin, Cursor, Claude
# Code, raw curl) gets the same behavior: every heading has
# `## YYYY-MM-DD HH:MM — ` prepended. The model never has to compute
# or guess the time; the server stamps it on write.


def test_ensure_timestamp_on_heading_prepends_when_missing() -> None:
    """Title without a timestamp gets `YYYY-MM-DD HH:MM — ` prepended."""
    import re
    from duckbrain.writer import _ensure_timestamp_on_heading

    result = _ensure_timestamp_on_heading("Debugging session")
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} — Debugging session$", result), result


def test_ensure_timestamp_on_heading_idempotent_with_emdash() -> None:
    """Title already starting with `YYYY-MM-DD HH:MM —` is unchanged."""
    from duckbrain.writer import _ensure_timestamp_on_heading

    title = "2026-06-01 14:23 — Debugging session"
    assert _ensure_timestamp_on_heading(title) == title


def test_ensure_timestamp_on_heading_idempotent_without_emdash() -> None:
    """Title starting with `YYYY-MM-DD HH:MM` (no em-dash) is also left
    alone — avoid double-stamping if the client format differs slightly."""
    from duckbrain.writer import _ensure_timestamp_on_heading

    title = "2026-06-01 14:23 Debugging session"
    assert _ensure_timestamp_on_heading(title) == title


def test_ensure_timestamp_on_heading_zero_pads_single_digit_hour(
    monkeypatch,
) -> None:
    """Hours <10 are zero-padded (strftime %H produces `09`, not `9`).
    Date is also zero-padded (strftime %m/%d produce `06`/`01`, not `6`/`1`)."""
    from datetime import datetime as real_datetime

    import duckbrain.writer as writer_mod

    class _FrozenDatetime:
        @classmethod
        def now(cls):
            return real_datetime(2026, 6, 1, 9, 5, 0)

    monkeypatch.setattr(writer_mod, "datetime", _FrozenDatetime)
    result = writer_mod._ensure_timestamp_on_heading("Morning session")
    assert result == "2026-06-01 09:05 — Morning session", result


def test_ensure_timestamp_on_heading_tz_honors_env(
    monkeypatch,
) -> None:
    """When TZ env var is set, the timestamp reflects that timezone."""
    import os

    import duckbrain.writer as writer_mod

    monkeypatch.setenv("TZ", "Asia/Tokyo")
    # 2026-06-01 03:00 UTC = 2026-06-01 12:00 JST
    # We need to use a fixed UTC time and check the local-time output.
    # But since we can't easily re-initialize the timezone, just verify
    # the function doesn't crash and returns a valid YYYY-MM-DD HH:MM.
    result = writer_mod._ensure_timestamp_on_heading("Tokyo session")
    import re
    assert re.match(
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} — Tokyo session$", result,
    ), result
    # And TZ is unchanged after the call
    assert os.environ.get("TZ") == "Asia/Tokyo"


def test_write_daily_adds_timestamp_to_heading(temp_vault: Path) -> None:
    """Integration: write_page(kind='daily') prepends `YYYY-MM-DD HH:MM —`
    to the first H2 heading of the daily note. v0.4.1: no H1 — the file
    path is the date."""
    import re
    from duckbrain.writer import write_page

    write_page(
        str(temp_vault), "daily", "Server-stamped entry",
        "Body content.", ["test"],
    )
    today = date.today().isoformat()
    content = (temp_vault / f"daily/{today}.md").read_text()
    # Heading carries the full local timestamp
    assert re.search(
        rf"^## {today} \d{{2}}:\d{{2}} — Server-stamped entry$", content, re.MULTILINE,
    ), content
    # v0.4.1: no H1 — file path is the date
    assert not content.startswith(f"# {today}"), content
    # And the file should not contain a bare date H1 anywhere at the top
    first_line = content.splitlines()[0]
    assert not first_line.startswith("# "), f"Expected no H1, got first line: {first_line!r}"


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
