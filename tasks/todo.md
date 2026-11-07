# Tasks: vault RAG experiment

All tasks are sequential and use test-first development. Owner: the implementation agent for each listed file.

## 1. Store the scanned corpus and passages

- [x] Add a local experiment CLI to scan the vault, apply optional path exclusions, report page count and text volume, and store page metadata, source hashes, corpus version and deterministic bounded passages with source positions in a persistent DuckDB file. Keep data under an ignored local directory.
- Acceptance: wiki and daily pages are included by default, exclusions work, source files remain unchanged, and SQL can inspect pages and passage provenance; a changed source changes the corpus version.
- Dependencies: none. Files: `src/duckbrain/rag.py`, `src/duckbrain/__init__.py` if shared types are needed, `tests/test_rag.py`, `.gitignore`. Verification: `uv run pytest tests/test_rag.py -v` with a real temporary vault and database.

## 2. Build passage BM25 retrieval

- [x] Create a persistent DuckDB FTS index over passage title, tags and text using the existing indexer's configuration; return ranked passages with source paths and scores. Rebuild the index when the corpus changes.
- Acceptance: a query returns a relevant source passage from the stored corpus, honors the limit, and does not return removed passages after rebuilding.
- Dependencies: task 1. Files: `src/duckbrain/rag.py`, `tests/test_rag.py`. Verification: focused tests with real DuckDB FTS, then `uv run pytest`.

## 3. Add Mistral embeddings and incremental indexing

- [x] Add a configurable Mistral embeddings client and persist vectors with passage hashes, model and chunk settings. Batch inputs; reuse unchanged embeddings; update new or changed passages and remove deleted or excluded passages. Preserve the last complete index on provider failures; changes in model or passage configuration trigger re-embedding.
- Acceptance: repeated indexing sends only required text; deleted passages cannot be retrieved; interrupted or failed runs leave no partial completed index. No credentials are needed by automated tests.
- Dependencies: tasks 1–2. Files: `src/duckbrain/rag.py`, `src/duckbrain/rag_mistral.py`, `tests/test_rag.py`, `tests/test_rag_mistral.py`. Verification: focused tests using a local HTTP test service, real DuckDB and temporary vault.

## Checkpoint: indexing

- [x] Run `uv run pytest` and manually inspect the database schema and passage metadata from a temporary vault. Confirm no external requests occur in automated tests.

## 4. Compare ad hoc searches

- [x] Embed a user question with the configured Mistral model; rank stored vectors using cosine similarity and run BM25 against the same corpus and result limit. Display and persist both lists, passage text, source paths, scores, question, corpus version and retrieval settings.
- Acceptance: one question produces side-by-side results and a saved run that can be inspected in SQL; missing credentials or an unavailable/incomplete index produces a clear error.
- Dependencies: tasks 2–3. Files: `src/duckbrain/rag.py`, `src/duckbrain/rag_mistral.py`, `tests/test_rag.py`. Verification: focused end-to-end tests with a local HTTP test service and real DuckDB.

## 5. Store and explore wiki links

- [x] Extract explicit wiki links, including alias and heading forms, into directed edges for indexed pages; retain the raw target and distinguish unresolved targets. Refresh edges as the corpus changes.
- Acceptance: SQL can retrieve outgoing links, backlinks and two-hop connections; excluded or missing targets remain identifiable and do not create false resolved edges.
- Dependencies: task 1; execute after task 4. Files: `src/duckbrain/rag.py`, `tests/test_rag.py`. Verification: focused tests with real temporary vault pages and DuckDB.

## 6. Generate and save grounded answers

- [ ] Add configurable Mistral chat answer generation for each saved retrieval list, using the same model and prompt and passage IDs as citations. Save prompt, model, answers and cited passages; surface unsupported evidence and provider errors clearly.
- Acceptance: both methods produce independently inspectable answers with citations to retrieved passages or an insufficient-evidence response; invalid citations are reported, not silently presented as verified.
- Dependencies: task 4. Files: `src/duckbrain/rag.py`, `src/duckbrain/rag_mistral.py`, `tests/test_rag.py`, `tests/test_rag_mistral.py`. Verification: local HTTP test service and real DuckDB tests cover both retrieval lists, invalid citations and provider errors.

## 7. Document and verify the workflow

- [ ] Document environment setup and complete commands for indexing, incremental updates, exclusions, comparison, answers and SQL exploration. Explain Mistral data transfer and the difference between page-level DuckBrain BM25 and passage-level experiment BM25.
- Acceptance: a reader can follow the workflow using their own vault and key; SQL examples cover pages, vectors, results, outgoing links, backlinks and two hops; generated data stays ignored.
- Dependencies: tasks 1–6. Files: `README.md`, `docs/rag-experiment.md`, tests only if documentation exposes behavior needing a check. Verification: exercise documented workflow against a temporary vault and local HTTP test service; run `git diff --check` and inspect `git status`.

## Final checkpoint

- [ ] Run `uv run ruff check src/duckbrain/`, `uv run ruff format --check src/duckbrain/`, `uv run mypy src/duckbrain/`, and `uv run pytest`. Report whether a real Mistral smoke test was performed and its limitations.
