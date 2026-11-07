"""Local, inspectable vault retrieval experiment."""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

import duckdb

from duckbrain.rag_mistral import MistralClient
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
        conn.execute(
            "CREATE TABLE IF NOT EXISTS edges (source_path VARCHAR, raw_target VARCHAR, "
            "target_path VARCHAR)"
        )
        conn.execute("BEGIN")
        try:
            conn.execute("DELETE FROM pages")
            conn.execute("DELETE FROM passages")
            conn.execute("DELETE FROM corpus")
            conn.execute("DELETE FROM edges")
            targets: dict[str, set[str]] = {}
            for page in pages:
                for key in (
                    page.title,
                    Path(page.filepath).stem,
                    page.filepath.removesuffix(".md"),
                ):
                    targets.setdefault(key.casefold(), set()).add(page.filepath)
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
                for match in re.finditer(r"\[\[([^\]]+)\]\]", page.body):
                    raw = match.group(1).split("|", 1)[0].strip()
                    target = raw.split("#", 1)[0].strip().removesuffix(".md")
                    candidates = (
                        targets.get(target.casefold(), set()) if target else {page.filepath}
                    )
                    resolved = next(iter(candidates)) if len(candidates) == 1 else None
                    conn.execute(
                        "INSERT INTO edges VALUES (?, ?, ?)", [page.filepath, raw, resolved]
                    )
            conn.execute("INSERT INTO corpus VALUES (?)", [version])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("INSTALL fts")
        conn.execute("LOAD fts")
        conn.execute("DROP TABLE IF EXISTS passage_search")
        conn.execute(
            "CREATE TABLE passage_search AS SELECT s.id, s.filepath, p.title, p.tags, "
            "s.text FROM passages s JOIN pages p USING (filepath)"
        )
        conn.execute(
            "PRAGMA create_fts_index('passage_search', 'id', 'title', 'tags', 'text', overwrite=1)"
        )


def search_bm25(database: Path, query: str, limit: int) -> list[dict]:
    """Return passage-level BM25 results from the current corpus."""
    with duckdb.connect(str(database)) as conn:
        rows = conn.execute(
            "SELECT id, filepath, title, text, score FROM ("
            "SELECT *, fts_main_passage_search.match_bm25(id, ?) AS score "
            "FROM passage_search) WHERE score IS NOT NULL ORDER BY score DESC, id LIMIT ?",
            [query, limit],
        ).fetchall()
    return [dict(zip(("id", "filepath", "title", "text", "score"), row)) for row in rows]


def index_vault(
    vault: Path,
    database: Path,
    client: MistralClient,
    model: str,
    excludes: list[str] | None = None,
    batch_size: int = 32,
) -> None:
    """Build an index privately, then publish it only after all embeddings succeed."""
    if batch_size < 1:
        raise ValueError("Batch size must be positive")
    database.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".rag-index-", suffix=".duckdb", dir=database.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        if database.exists():
            shutil.copyfile(database, temporary)
        else:
            temporary.unlink()
        store_corpus(vault, temporary, excludes)
        with duckdb.connect(str(temporary)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS embedding_cache (hash VARCHAR, model VARCHAR, "
                "config VARCHAR, vector FLOAT[])"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS embeddings (id VARCHAR, filepath VARCHAR, "
                "hash VARCHAR, model VARCHAR, config VARCHAR, vector FLOAT[])"
            )
            passages = conn.execute(
                "SELECT id, filepath, text FROM passages ORDER BY id"
            ).fetchall()
            cached = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT hash, vector FROM embedding_cache WHERE model = ? AND config = ?",
                    [model, "chars:1000"],
                ).fetchall()
            }
            missing = {}
            for _, _, text in passages:
                digest = hashlib.sha256(text.encode()).hexdigest()
                if digest not in cached:
                    missing[digest] = text
            items = list(missing.items())
            for start in range(0, len(items), batch_size):
                batch = items[start : start + batch_size]
                vectors = client.embed([text for _, text in batch], model)
                for (digest, _), vector in zip(batch, vectors):
                    cached[digest] = vector
                    conn.execute(
                        "INSERT INTO embedding_cache VALUES (?, ?, ?, ?)",
                        [digest, model, "chars:1000", vector],
                    )
            conn.execute("DELETE FROM embeddings")
            for id_, filepath, text in passages:
                digest = hashlib.sha256(text.encode()).hexdigest()
                conn.execute(
                    "INSERT INTO embeddings VALUES (?, ?, ?, ?, ?, ?)",
                    [id_, filepath, digest, model, "chars:1000", cached[digest]],
                )
        os.replace(temporary, database)
    finally:
        temporary.unlink(missing_ok=True)


def compare(database: Path, client: MistralClient, question: str, limit: int) -> tuple[str, dict]:
    """Save BM25 and exact cosine rankings for one question and corpus."""
    if not database.exists():
        raise ValueError("Index does not exist; run indexing first")
    if not question.strip() or limit < 1:
        raise ValueError("A question and positive limit are required")
    with duckdb.connect(str(database)) as conn:
        try:
            settings = conn.execute("SELECT DISTINCT model, config FROM embeddings").fetchall()
            version_row = conn.execute("SELECT corpus_version FROM corpus").fetchone()
        except duckdb.Error as exc:
            raise ValueError("Index is incomplete; run indexing first") from exc
        if len(settings) != 1 or not version_row:
            raise ValueError("Index is incomplete or empty; run indexing first")
        model, config = settings[0]
        query_vector = client.embed([question], model)[0]
        rows = conn.execute(
            "SELECT e.id, e.filepath, p.title, s.text, e.vector FROM embeddings e "
            "JOIN passages s ON e.id = s.id JOIN pages p ON e.filepath = p.filepath"
        ).fetchall()
        scored = []
        for id_, filepath, title, text, vector in rows:
            if len(vector) != len(query_vector):
                raise ValueError("Embedding dimensions do not match")
            denominator = math.sqrt(sum(x * x for x in vector) * sum(x * x for x in query_vector))
            if not denominator:
                raise ValueError("Cannot compare a zero embedding")
            score = sum(x * y for x, y in zip(vector, query_vector)) / denominator
            scored.append(dict(id=id_, filepath=filepath, title=title, text=text, score=score))
        scored.sort(key=lambda item: (-item["score"], item["id"]))
        bm25 = search_bm25(database, question, limit)
        results = {"bm25": bm25, "embedding": scored[:limit]}
        run_id = uuid.uuid4().hex
        conn.execute(
            "CREATE TABLE IF NOT EXISTS runs (id VARCHAR, question VARCHAR, model VARCHAR, "
            "config VARCHAR, corpus_version VARCHAR, result_limit INTEGER)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS results (run_id VARCHAR, method VARCHAR, rank INTEGER, "
            "passage_id VARCHAR, filepath VARCHAR, title VARCHAR, text VARCHAR, score DOUBLE)"
        )
        conn.execute("BEGIN")
        try:
            conn.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                [run_id, question, model, config, version_row[0], limit],
            )
            for method, hits in results.items():
                for rank, hit in enumerate(hits, 1):
                    conn.execute(
                        "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            run_id,
                            method,
                            rank,
                            hit["id"],
                            hit["filepath"],
                            hit["title"],
                            hit["text"],
                            hit["score"],
                        ],
                    )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return run_id, results


ANSWER_INSTRUCTION = (
    "Answer using only the supplied passages. Cite factual claims using [number] citations. "
    "If evidence is insufficient, reply exactly: Insufficient evidence."
)


def answer_run(database: Path, client: MistralClient, run_id: str, model: str) -> dict:
    """Generate and save answers with explicitly checked passage citations."""
    if not model.strip():
        raise ValueError("An answer model is required")
    with duckdb.connect(str(database)) as conn:
        row = conn.execute("SELECT question FROM runs WHERE id = ?", [run_id]).fetchone()
        if row is None:
            raise ValueError("Unknown comparison run")
        answers = {}
        for method in ("bm25", "embedding"):
            rows = conn.execute(
                "SELECT rank, passage_id, filepath, text FROM results "
                "WHERE run_id = ? AND method = ? ORDER BY rank",
                [run_id, method],
            ).fetchall()
            evidence = "\n\n".join(
                f"[{rank}] {path} ({passage_id})\n{text}" for rank, passage_id, path, text in rows
            )
            prompt = f"{ANSWER_INSTRUCTION}\n\nQuestion: {row[0]}\n\nPassages:\n{evidence}"
            response = client.post(
                "chat/completions",
                {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
            )
            answer = response["choices"][0]["message"]["content"]
            if not isinstance(answer, str):
                raise ValueError("Provider returned an invalid answer")
            citations = sorted({int(match) for match in re.findall(r"\[(\d+)\]", answer)})
            available = {
                rank: {"passage_id": passage_id, "filepath": path, "text": text}
                for rank, passage_id, path, text in rows
            }
            invalid = [citation for citation in citations if citation not in available]
            insufficient = answer.strip().casefold().rstrip(".") == "insufficient evidence"
            valid = not invalid and (bool(citations) or insufficient)
            answers[method] = {
                "answer": answer,
                "prompt": prompt,
                "citations": citations,
                "invalid_citations": invalid,
                "valid": valid,
                "cited_passages": [available[c] for c in citations if c in available],
            }
        conn.execute(
            "CREATE TABLE IF NOT EXISTS answers (run_id VARCHAR, method VARCHAR, model VARCHAR, "
            "prompt VARCHAR, answer VARCHAR, citations JSON, cited_passages JSON, "
            "valid BOOLEAN, invalid_citations JSON)"
        )
        conn.execute("BEGIN")
        try:
            for method, answer in answers.items():
                conn.execute(
                    "INSERT INTO answers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        run_id,
                        method,
                        model,
                        answer["prompt"],
                        answer["answer"],
                        json.dumps(answer["citations"]),
                        json.dumps(answer["cited_passages"]),
                        answer["valid"],
                        json.dumps(answer["invalid_citations"]),
                    ],
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return answers


def main() -> None:
    parser = argparse.ArgumentParser(description="Store an inspectable vault corpus")
    parser.add_argument("vault", type=Path)
    parser.add_argument("--database", type=Path, default=Path(".rag/corpus.duckdb"))
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    store_corpus(args.vault, args.database, args.exclude)


if __name__ == "__main__":
    main()
