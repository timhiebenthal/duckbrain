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
