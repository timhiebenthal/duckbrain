"""Tests for duckbrain.scanner — vault file discovery and frontmatter parsing."""

from pathlib import Path
import pytest
from duckbrain import PageMetadata


# ── scan_vault tests ──────────────────────────────────────────────────────────


def test_scan_vault_finds_all_pages(temp_vault: Path) -> None:
    """scan_vault returns a PageMetadata for each wiki/* page with valid item-type."""
    from duckbrain.scanner import scan_vault

    pages = scan_vault(str(temp_vault))

    # temp_vault fixture creates 5 pages with item-type
    assert len(pages) == 5

    kinds = [p.kind for p in pages]
    assert kinds.count("entity") == 1
    assert kinds.count("concept") == 2
    assert kinds.count("source") == 1
    assert kinds.count("synthesis") == 1

    # Check a specific page's kind is inferred from parent dir
    for p in pages:
        if p.title == "Claude Mem":
            assert p.kind == "entity"
            assert "claude-mem.md" in p.filepath
        elif p.title == "Agent Memory Systems":
            assert p.kind == "concept"
        elif p.title == "Jagged Frontier":
            assert p.kind == "concept"


def test_scan_vault_excludes_non_wiki(temp_vault: Path) -> None:
    """Files in wiki/ but not under entities/concepts/sources/synthesis are skipped."""
    from duckbrain.scanner import scan_vault

    # Add a junk file directly in wiki/ with no frontmatter
    junk = temp_vault / "wiki" / "junk.md"
    junk.write_text("# Just a note\n\nNo frontmatter here.\n")

    pages = scan_vault(str(temp_vault))
    titles = [p.title for p in pages]
    assert "junk.md" not in [p.filepath for p in pages]
    assert len(pages) == 5  # unchanged


def test_scan_vault_frontmatter_no_item_type(temp_vault: Path) -> None:
    """File with YAML frontmatter but no item-type key is skipped."""
    from duckbrain.scanner import scan_vault

    no_type = temp_vault / "wiki" / "entities" / "no-type.md"
    no_type.write_text("---\ntitle: No Type\n---\n\nBody.\n")

    pages = scan_vault(str(temp_vault))
    titles = [p.title for p in pages]
    assert "No Type" not in titles
    assert len(pages) == 5


def test_scan_vault_empty_dir(tmp_path: Path) -> None:
    """An empty vault returns an empty list."""
    from duckbrain.scanner import scan_vault

    pages = scan_vault(str(tmp_path))
    assert pages == []


# ── parse_frontmatter tests ───────────────────────────────────────────────────


def test_parse_frontmatter_with_yaml() -> None:
    """Valid YAML frontmatter is parsed into a dict and the body is returned."""
    from duckbrain.scanner import parse_frontmatter

    content = "---\ntitle: Foo\nitem-type: entity\ntags: [a, b]\n---\n# Foo\n\nBody text."
    meta, body = parse_frontmatter(content)

    assert meta["title"] == "Foo"
    assert meta["item-type"] == "entity"
    assert meta["tags"] == ["a", "b"]
    assert body == "# Foo\n\nBody text."


def test_parse_frontmatter_no_yaml() -> None:
    """Content without frontmatter returns ({}, full_content)."""
    from duckbrain.scanner import parse_frontmatter

    content = "# Just a heading\n\nSome text without frontmatter."
    meta, body = parse_frontmatter(content)

    assert meta == {}
    assert body == content


def test_parse_frontmatter_malformed_yaml() -> None:
    """Malformed YAML is handled gracefully — returns ({}, content)."""
    from duckbrain.scanner import parse_frontmatter

    content = "---\ntitle: Foo\nitem-type: [unclosed\n---\n# Broken"
    meta, body = parse_frontmatter(content)

    assert meta == {}
    assert body == content
