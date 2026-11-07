"""Local, inspectable vault retrieval experiment."""

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

from duckbrain.scanner import scan_vault


def store_corpus(vault: Path, database: Path, excludes: list[str] | None = None) -> None:
    """Persist scanner-visible pages and bounded passages without modifying the vault."""
    excluded = [p.rstrip("/") for p in (excludes or [])]
    pages = [
        p
        for p in scan_vault(str(vault))
        if not any(p.filepath == x or p.filepath.startswith(x + "/") for x in excluded)
    ]
    hashes = [
        (p.filepath, hashlib.sha256((vault / p.filepath).read_bytes()).hexdigest()) for p in pages
    ]
    version = hashlib.sha256(json.dumps(hashes).encode()).hexdigest()
    print(f"Pages: {len(pages)}; text characters: {sum(len(p.body) for p in pages)}")
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS pages (filepath VARCHAR, title VARCHAR, kind VARCHAR, "
            "tags VARCHAR, body VARCHAR, source_hash VARCHAR)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS passages (id VARCHAR, filepath VARCHAR, "
            "position INTEGER, text VARCHAR)"
        )
        conn.execute("CREATE TABLE IF NOT EXISTS corpus (corpus_version VARCHAR)")
        conn.execute("BEGIN")
        try:
            conn.execute("DELETE FROM pages")
            conn.execute("DELETE FROM passages")
            conn.execute("DELETE FROM corpus")
            for page, (_, source_hash) in zip(pages, hashes):
                conn.execute(
                    "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        page.filepath,
                        page.title,
                        page.kind,
                        ",".join(page.tags),
                        page.body,
                        source_hash,
                    ],
                )
                for pos in range(0, len(page.body), 1000):
                    conn.execute(
                        "INSERT INTO passages VALUES (?, ?, ?, ?)",
                        [f"{page.filepath}:{pos}", page.filepath, pos, page.body[pos : pos + 1000]],
                    )
            conn.execute("INSERT INTO corpus VALUES (?)", [version])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Store an inspectable vault corpus")
    parser.add_argument("vault", type=Path)
    parser.add_argument("--database", type=Path, default=Path(".rag/corpus.duckdb"))
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    store_corpus(args.vault, args.database, args.exclude)


if __name__ == "__main__":
    main()
