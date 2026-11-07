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
