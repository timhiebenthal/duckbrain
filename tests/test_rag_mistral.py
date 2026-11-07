import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import duckdb
import pytest

from duckbrain.rag import index_vault
from duckbrain.rag_mistral import MistralClient


@pytest.fixture
def provider():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            if body.get("model") == "fail":
                self.send_error(500)
                return
            if self.path.endswith("/chat/completions"):
                content = "Answer [99]" if body.get("model") == "invalid" else "Answer [1]"
                payload = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if body.get("model") == "bad-vector":
                payload = json.dumps({"data": [{"index": 0, "embedding": ["bad"]}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            data = [
                {"index": i, "embedding": [float(len(text)), 1.0]}
                for i, text in enumerate(body["input"])
            ]
            payload = json.dumps({"data": data}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()
    thread.join()
    server.server_close()


def test_incremental_embeddings_and_atomic_failure(temp_vault: Path, tmp_path: Path, provider):
    url, requests = provider
    db = tmp_path / "rag.duckdb"
    client = MistralClient("test", url)
    index_vault(temp_vault, db, client, "model")
    first_count = sum(len(r["input"]) for r in requests)
    assert first_count > 0
    index_vault(temp_vault, db, client, "model")
    assert sum(len(r["input"]) for r in requests) == first_count
    with duckdb.connect(str(db)) as conn:
        before = conn.execute("SELECT corpus_version FROM corpus").fetchone()[0]
    (temp_vault / "daily/2026-05-28.md").write_text("new content")
    with pytest.raises(Exception):
        index_vault(temp_vault, db, client, "fail")
    with duckdb.connect(str(db)) as conn:
        assert conn.execute("SELECT corpus_version FROM corpus").fetchone()[0] == before
    index_vault(temp_vault, db, client, "model")
    assert sum(len(r["input"]) for r in requests if r["model"] == "model") == first_count + 1
    (temp_vault / "daily/2026-05-28.md").unlink()
    index_vault(temp_vault, db, client, "model")
    with duckdb.connect(str(db)) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM embeddings WHERE filepath = 'daily/2026-05-28.md'"
            ).fetchone()[0]
            == 0
        )


def test_model_changes_and_exclusions(temp_vault: Path, tmp_path: Path, provider):
    url, requests = provider
    db = tmp_path / "rag.duckdb"
    client = MistralClient("test", url)
    index_vault(temp_vault, db, client, "first", batch_size=2)
    first_count = sum(len(r["input"]) for r in requests)
    assert len(requests) > 1
    index_vault(temp_vault, db, client, "second", excludes=["daily"], batch_size=2)
    second_count = sum(len(r["input"]) for r in requests if r["model"] == "second")
    assert 0 < second_count < first_count
    with duckdb.connect(str(db)) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM embeddings WHERE filepath LIKE 'daily/%'"
            ).fetchone()[0]
            == 0
        )
        assert {r[0] for r in conn.execute("SELECT DISTINCT model FROM embeddings").fetchall()} == {
            "second"
        }


def test_invalid_provider_vectors_do_not_replace_index(temp_vault: Path, tmp_path: Path, provider):
    url, _ = provider
    db = tmp_path / "rag.duckdb"
    client = MistralClient("test", url)
    index_vault(temp_vault, db, client, "valid")
    with pytest.raises(ValueError, match="embedding"):
        index_vault(temp_vault, db, client, "bad-vector", batch_size=1)
    with duckdb.connect(str(db)) as conn:
        rows = conn.execute("SELECT DISTINCT model FROM embeddings").fetchall()
        assert {row[0] for row in rows} == {"valid"}


def test_compare_persists_both_rankings(temp_vault: Path, tmp_path: Path, provider):
    from duckbrain.rag import compare

    url, _ = provider
    db = tmp_path / "rag.duckdb"
    client = MistralClient("test", url)
    index_vault(temp_vault, db, client, "model")
    run_id, results = compare(db, client, "taxonomy", 2)
    assert set(results) == {"bm25", "embedding"}
    assert results["bm25"][0]["filepath"] == "wiki/concepts/agent-memory-systems.md"
    assert len(results["embedding"]) == 2
    with duckdb.connect(str(db)) as conn:
        assert conn.execute(
            "SELECT question, model FROM runs WHERE id = ?", [run_id]
        ).fetchone() == ("taxonomy", "model")
        rows = conn.execute(
            "SELECT method, text, filepath, score FROM results WHERE run_id = ?", [run_id]
        ).fetchall()
        assert {row[0] for row in rows} == {"bm25", "embedding"}
        assert all(row[1] and row[2] and row[3] is not None for row in rows)


def test_compare_rejects_missing_or_incomplete_index(temp_vault: Path, tmp_path: Path, provider):
    from duckbrain.rag import compare, store_corpus

    url, requests = provider
    client = MistralClient("test", url)
    db = tmp_path / "missing.duckdb"
    with pytest.raises(ValueError, match="Index"):
        compare(db, client, "question", 2)
    store_corpus(temp_vault, db)
    with pytest.raises(ValueError, match="incomplete"):
        compare(db, client, "question", 2)
    assert requests == []


def test_answers_record_citations_and_reject_invalid_ids(
    temp_vault: Path, tmp_path: Path, provider
):
    from duckbrain.rag import answer_run, compare

    url, _ = provider
    db = tmp_path / "rag.duckdb"
    client = MistralClient("test", url)
    index_vault(temp_vault, db, client, "embed")
    run_id, _ = compare(db, client, "taxonomy", 2)
    answers = answer_run(db, client, run_id, "chat")
    assert set(answers) == {"bm25", "embedding"}
    assert all(answer["valid"] and answer["citations"] == [1] for answer in answers.values())
    with duckdb.connect(str(db)) as conn:
        assert (
            conn.execute("SELECT count(*) FROM answers WHERE run_id = ?", [run_id]).fetchone()[0]
            == 2
        )
    invalid = answer_run(db, client, run_id, "invalid")
    assert not any(answer["valid"] for answer in invalid.values())
    assert all(answer["invalid_citations"] == [99] for answer in invalid.values())
    with pytest.raises(Exception):
        answer_run(db, client, run_id, "fail")
    with duckdb.connect(str(db)) as conn:
        assert (
            conn.execute("SELECT count(*) FROM answers WHERE run_id = ?", [run_id]).fetchone()[0]
            == 4
        )


def test_cli_workflow(temp_vault: Path, tmp_path: Path, provider):
    import os
    import subprocess
    import sys

    url, _ = provider
    db = tmp_path / "cli.duckdb"
    env = {**os.environ, "MISTRAL_API_KEY": "test", "MISTRAL_BASE_URL": url}

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "duckbrain.rag", *args],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

    preview = run("preview", str(temp_vault), "--exclude", "daily")
    assert "Pages: 5" in preview.stdout
    assert not db.exists()
    assert not provider[1]

    indexed = run(
        "index", str(temp_vault), "--database", str(db), "--model", "embed", "--exclude", "daily"
    )
    assert "Pages:" in indexed.stdout
    compared = run("compare", "--database", str(db), "--question", "taxonomy", "--limit", "2")
    result = json.loads(compared.stdout)
    assert result["results"]["bm25"][0]["filepath"].endswith("agent-memory-systems.md")
    answered = run("answer", "--database", str(db), "--run", result["run_id"], "--model", "chat")
    assert json.loads(answered.stdout)["bm25"]["valid"]
