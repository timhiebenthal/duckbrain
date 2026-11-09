# Plan: vault RAG experiment

Implement [SPEC.md](../SPEC.md) as one experiment using a persistent local DuckDB database and an independent command-line entry point. Keep DuckBrain's MCP server unchanged. The ordered tasks and verification are in [todo.md](todo.md).

## Design

- Reuse `scan_vault` to discover wiki and daily pages. Apply optional path exclusions; report page count and text volume before hosted embedding. Store paths, source hashes and a corpus version in DuckDB, without changing vault files.
- Split pages deterministically into bounded passages, preserving page path, title and passage position. Use these same passages for both retrieval methods. DuckBrain's current BM25 indexes whole pages in memory, so build a separate persistent passage-level FTS index with its title/tags/body configuration and document the difference. Rebuild FTS after corpus changes.
- Use Mistral's embeddings endpoint, batching requests and recording model and passage settings. Cache vectors by content hash and configuration; update changed passages and remove stale current references only after successful indexing. Store vectors, metadata and pages in inspectable DuckDB tables. Use exact cosine similarity for this initial experiment.
- Run an ad hoc question against both indexes at the same limit; persist the question, configuration, ranked passage text, paths and scores in DuckDB. Compare rankings by inspection; do not introduce scoring benchmarks.
- Parse explicit wiki links into a DuckDB edges table; retain unresolved targets. Supply SQL examples for nodes, outgoing links, backlinks and two-hop traversal.
- Generate answers from each result set using the same configurable Mistral chat model and prompt, citing retrieved passage IDs and explicitly allowing an insufficient-evidence answer. Persist model, prompt, answers and cited passages. Mistral chat is a proposed default; model selection remains configurable and must be confirmed before a live answer run.
- Keep generated databases and output under an ignored local directory. Document provider calls, credentials and complete usage. Tests use real DuckDB and filesystem; isolate external calls with a local HTTP test service rather than contacting Mistral.

## Dependencies and risks

Corpus and passage storage → BM25 and embedding indexes → comparison → answers. Graph extraction depends on corpus storage but is sequenced after comparison to keep changes reviewable. The index and tests share files, so no parallel streams are planned.

Hosted runs send vault text and questions to Mistral and incur provider charges; document this and show text volume. A provider error or interruption must not publish partial results as a completed index. Whole-page BM25 and passage BM25 may rank differently; document the distinction rather than claiming exact equivalence. A generated citation is not proof of grounding, so keep passages visible for manual inspection.
