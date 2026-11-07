from pathlib import Path

import duckdb

from duckbrain.rag import store_corpus


def test_store_corpus_tracks_sources_exclusions_and_versions(temp_vault: Path, tmp_path: Path):
    db = tmp_path / "rag.duckdb"
    original = (temp_vault / "daily/2026-05-28.md").read_text()
    store_corpus(temp_vault, db, excludes=["wiki/sources"])
    with duckdb.connect(str(db)) as conn:
        paths = {row[0] for row in conn.execute("SELECT filepath FROM pages").fetchall()}
        assert "daily/2026-05-28.md" in paths
        assert not any(path.startswith("wiki/sources/") for path in paths)
        assert (
            conn.execute(
                "SELECT count(*) FROM passages WHERE filepath = ?", ["daily/2026-05-28.md"]
            ).fetchone()[0]
            > 0
        )
        version = conn.execute("SELECT corpus_version FROM corpus").fetchone()[0]
    assert (temp_vault / "daily/2026-05-28.md").read_text() == original
    (temp_vault / "daily/2026-05-28.md").write_text(original + " changed")
    store_corpus(temp_vault, db, excludes=["wiki/sources"])
    with duckdb.connect(str(db)) as conn:
        assert conn.execute("SELECT corpus_version FROM corpus").fetchone()[0] != version


def test_bm25_search_uses_current_passages(temp_vault: Path, tmp_path: Path):
    from duckbrain.rag import search_bm25

    db = tmp_path / "rag.duckdb"
    store_corpus(temp_vault, db)
    hits = search_bm25(db, "taxonomy", 1)
    assert len(hits) == 1
    assert hits[0]["filepath"] == "wiki/concepts/agent-memory-systems.md"
    assert hits[0]["score"] > 0
    (temp_vault / hits[0]["filepath"]).unlink()
    store_corpus(temp_vault, db)
    assert search_bm25(db, "taxonomy", 10) == []


def test_graph_resolves_links_and_preserves_missing_targets(temp_vault: Path, tmp_path: Path):
    db = tmp_path / "rag.duckdb"
    daily = temp_vault / "daily/2026-05-28.md"
    daily.write_text("[[Claude Mem#Notes|memory]] [[missing|alias]]")
    entity = temp_vault / "wiki/entities/claude-mem.md"
    entity.write_text(entity.read_text() + "\n[[Jagged Frontier]]")
    store_corpus(temp_vault, db)
    with duckdb.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT source_path, raw_target, target_path FROM edges ORDER BY source_path, raw_target"
        ).fetchall()
        assert ("daily/2026-05-28.md", "Claude Mem#Notes", "wiki/entities/claude-mem.md") in rows
        assert ("daily/2026-05-28.md", "missing", None) in rows
        assert (
            "wiki/entities/claude-mem.md",
            "Jagged Frontier",
            "wiki/concepts/jagged-frontier.md",
        ) in rows
    store_corpus(temp_vault, db, excludes=["wiki/entities"])
    with duckdb.connect(str(db)) as conn:
        assert (
            conn.execute(
                "SELECT target_path FROM edges WHERE raw_target = 'Claude Mem#Notes'"
            ).fetchone()[0]
            is None
        )
