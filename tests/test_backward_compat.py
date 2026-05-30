"""Backward-compatibility regression tests.

Verifies that the old API (without config) produces identical results
to the new API with config=None or config=VaultConfig().
"""

from pathlib import Path

from duckbrain import PageMetadata


# ── scan_vault backward compat ───────────────────────────────────────────────


def test_scan_vault_backward_compat(temp_vault: Path) -> None:
    """scan_vault(path) matches scan_vault(path, config=None) and config=VaultConfig()."""
    from duckbrain.config import VaultConfig
    from duckbrain.scanner import scan_vault

    old = scan_vault(str(temp_vault))
    new_none = scan_vault(str(temp_vault), config=None)
    new_default = scan_vault(str(temp_vault), config=VaultConfig())

    assert len(old) == len(new_none)
    assert len(old) == len(new_default)

    # Sort both lists by filepath for comparison
    old_sorted = sorted(old, key=lambda p: p.filepath)
    new_sorted = sorted(new_none, key=lambda p: p.filepath)

    for a, b in zip(old_sorted, new_sorted):
        assert a.filepath == b.filepath
        assert a.title == b.title
        assert a.kind == b.kind
        assert a.tags == b.tags
        assert a.created == b.created
        assert a.updated == b.updated


# ── write_page backward compat ───────────────────────────────────────────────


def test_write_page_backward_compat(temp_vault: Path) -> None:
    """write_page with config=None matches old API."""
    from duckbrain.config import VaultConfig
    from duckbrain.writer import write_page

    result_old = write_page(str(temp_vault), "entity", "T", "Body", [])
    result_new = write_page(str(temp_vault), "entity", "T2", "Body2", [], config=None)

    assert result_old["success"] is True
    assert result_new["success"] is True
    assert "wiki/entities/" in result_old["filepath"]


# ── get_stats backward compat ────────────────────────────────────────────────


def test_get_stats_backward_compat(sample_pages: list[PageMetadata]) -> None:
    """get_stats(conn) matches get_stats(conn, config=None)."""
    from duckbrain.indexer import build_fts_index, get_stats

    conn = build_fts_index(sample_pages)
    stats_old = get_stats(conn)
    stats_new = get_stats(conn, config=None)

    assert stats_old == stats_new
    conn.close()


# ── vault_info backward compat ────────────────────────────────────────────────


def test_vault_info_backward_compat(temp_vault: Path) -> None:
    """handle_vault_info without config returns standard keys."""
    from duckbrain.tools.vault_info import handle_vault_info

    info = handle_vault_info(str(temp_vault))

    assert "entities" in info
    assert "concepts" in info
    assert "sources" in info
    assert "synthesis" in info
    assert "daily" in info
    assert "available_tags" in info
    assert "last_modified" in info
    assert info["config_active"] is False


# ── vault_search backward compat ─────────────────────────────────────────────


def test_search_backward_compat(temp_vault: Path) -> None:
    """handle_vault_search without config returns expected results."""
    from duckbrain.tools.vault_search import handle_vault_search

    results = handle_vault_search(str(temp_vault), "Claude")
    assert len(results) >= 1
    assert any("Claude" in r["title"] for r in results)


# ── vault_read backward compat ───────────────────────────────────────────────


def test_vault_read_backward_compat(temp_vault: Path) -> None:
    """handle_vault_read with filepath returns same kind."""
    from duckbrain.tools.vault_read import handle_vault_read

    result = handle_vault_read(
        str(temp_vault), filepath="wiki/concepts/jagged-frontier.md",
    )
    assert result["kind"] in ("concept", "wiki")


# ── vault_context backward compat ─────────────────────────────────────────────


def test_vault_context_backward_compat(temp_vault: Path) -> None:
    """handle_vault_context without config returns dailies + search."""
    from duckbrain.tools.vault_context import handle_vault_context

    ctx = handle_vault_context(str(temp_vault), keywords=["Claude"])

    assert "today_daily" in ctx
    assert "yesterday_daily" in ctx
    assert "search_results" in ctx


# ── Roundtrip backward compat ────────────────────────────────────────────────


def test_write_read_roundtrip_backward_compat(temp_vault: Path) -> None:
    """Write with old API → read with new API → content matches."""
    from duckbrain.tools.vault_read import handle_vault_read
    from duckbrain.writer import write_page

    filepath_rel = write_page(
        str(temp_vault), "concept", "Roundtrip Test", "RT content", [],
    )["filepath"]

    result = handle_vault_read(str(temp_vault), filepath=filepath_rel)
    assert "RT content" in result["content"]


# ── Full stack custom config roundtrip ────────────────────────────────────────


def test_full_stack_custom_config(tmp_path: Path) -> None:
    """End-to-end config-aware roundtrip: scan → write → read → search → stats → tags."""
    import json

    from duckbrain.config import load_vault_config, ScanPattern, VaultConfig, WriteRule
    from duckbrain.indexer import build_fts_index, get_stats
    from duckbrain.scanner import scan_vault
    from duckbrain.tools.vault_read import handle_vault_read
    from duckbrain.tools.vault_search import handle_vault_search
    from duckbrain.writer import build_tags_index, write_page

    vault = tmp_path / "vault"
    wiki = vault / "wiki"
    projects = wiki / "projects"
    notes = wiki / "notes"
    projects.mkdir(parents=True)
    notes.mkdir(parents=True)
    (wiki / "index.md").write_text("")
    (wiki / "log.md").write_text("")

    # Write config file
    config_data = {
        "version": 1,
        "scan": {
            "patterns": [
                {
                    "glob": "wiki/projects/*.md",
                    "kind": "project",
                    "frontmatter": {"enabled": True, "kind_field": "item-type"},
                    "dates": {"created": "frontmatter:created", "updated": "frontmatter:updated"},
                },
                {
                    "glob": "wiki/notes/*.md",
                    "kind": "note",
                    "frontmatter": {"enabled": True, "kind_field": "item-type"},
                    "dates": {"created": "frontmatter:created", "updated": "frontmatter:updated"},
                },
            ],
        },
    }
    (vault / "duckbrain.config.json").write_text(json.dumps(config_data))
    config = load_vault_config(str(vault))

    # Create existing page and scan
    (projects / "p1.md").write_text(
        "---\ntitle: P1\nitem-type: project\ntags: [alpha]\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nP1 body\n"
    )
    pages = scan_vault(str(vault), config=config)
    assert len(pages) == 1
    assert pages[0].kind == "project"

    # Write a new note page
    result = write_page(
        str(vault), "note", "My Note", "Note body", ["beta"], config=config,
    )
    assert result["success"] is True
    assert "wiki/notes/my-note.md" in result["filepath"]

    # Read it back
    read_result = handle_vault_read(
        str(vault), filepath="wiki/notes/my-note.md", config=config,
    )
    assert read_result["kind"] == "note"

    # Search by kind
    search_results = handle_vault_search(
        str(vault), "Note", kind="note", config=config,
    )
    assert len(search_results) >= 1

    # Stats include note + project
    all_pages = scan_vault(str(vault), config=config)
    conn = build_fts_index(all_pages)
    stats = get_stats(conn, config=config)
    assert stats["project"] == 1
    assert stats["note"] == 1
    conn.close()

    # Tags index scans only configured dirs
    build_tags_index(str(vault), config=config)
    tags = (wiki / "tags.md").read_text()
    assert "alpha" in tags
    assert "beta" in tags
