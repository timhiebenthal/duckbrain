# Spec: DuckBrain vault RAG experiment

## Objective

Build an inspectable experiment using the Obsidian vault to learn how keyword search, embeddings and a wiki-link graph work. Compare DuckBrain's existing DuckDB BM25 search with Mistral Embed on the same questions and passages, and inspect the pages, embeddings and links in persistent DuckDB files. Save retrieval results and grounded answers for the user to judge by eye.

## Scope and assumptions

- Index the entire scanner-visible vault by default, including daily notes; allow optional path exclusions. The original vault remains unchanged. Record indexed paths and content versions so runs identify their corpus and source changes are detected.
- Accept ad hoc questions and present results side by side for the user's qualitative judgment. A labeled question set and numerical evaluation are not required for the first experiment.
- Use Mistral's hosted embedding API first: indexed passages and query text are sent to Mistral. Store returned vectors locally in DuckDB. Report the indexed page count and text volume before the first embedding run; do not commit notes, vectors, answers, API keys or generated databases.
- Persist embeddings and update the index incrementally: reuse unchanged passage embeddings, embed new or changed passages, and remove deleted or excluded content from current retrieval results. Re-embed when the embedding model or passage configuration changes.
- Compare the same corpus, passage boundaries, questions and result limit for both methods. The BM25 baseline follows the existing DuckBrain indexer's search configuration; document any necessary differences. Record model identity, retrieval settings, corpus version, ranked passages, source paths and scores for each run.
- Represent pages as nodes and explicit Obsidian wiki links as directed edges in DuckDB. Retain link targets that are outside the index or unresolved so they are distinguishable from resolved links. Provide SQL examples for outgoing links, backlinks and a two-hop traversal. Edges represent authored links, not inferred factual relationships.
- Provide a way to generate answers from each method's retrieved passages using the same answer model and prompt, with citations to source passages and an explicit unsupported-answer response when the evidence is insufficient. Save the prompt/model settings, answer and cited passages alongside results. The answer provider and model are configurable; their selection and data handling must be documented before use.
- The experiment runs from this worktree without changing the existing MCP server's behavior. Persistent databases and run artifacts are local and inspectable with ordinary SQL. One database may hold multiple tables; separate databases are acceptable if documented.

## Commands and project structure

Use the existing Python and `uv` project with DuckDB and the scanner/indexer where applicable. Add an experiment entry point and usage documentation with complete executable commands for selection, indexing, comparison, graph inspection and answer generation. Tests belong in `tests/`; reusable production code follows `src/duckbrain/` conventions. Do not prescribe a CLI interface until the plan selects one.

```bash
uv run ruff check src/duckbrain/
uv run ruff format --check src/duckbrain/
uv run mypy src/duckbrain/
uv run pytest
```

## Code style and testing

Follow existing Python naming, types and formatting. Reuse the scanner's page representation and existing indexer where appropriate, for example:

```python
pages = scan_vault(vault_path)
conn = build_fts_index(pages)
```

Follow red–green–refactor: write a failing test, implement the smallest change and run the full suite. Use the existing temporary vault fixture and real DuckDB for tests. Test exclusions and incremental updates, passage/source provenance, reproducible comparison, graph links including unresolved targets, and saved results. Tests must run without credentials or sending vault data to an external API; exercise hosted integrations separately with deliberately chosen content.

## Success criteria

1. A documented command creates inspectable local DuckDB data for the scanner-visible vault, respecting optional exclusions. Re-running it reuses unchanged embeddings and updates changed, removed or excluded content. SQL examples show nodes, edges, vectors and retrieval results.
2. The same ad hoc question can be run against BM25 and Mistral embeddings, with ranked passages and source citations saved for side-by-side inspection. A run records the model and data versions needed to interpret the comparison.
3. A user can inspect outgoing, incoming and two-hop wiki links, including links whose target is not in the index.
4. Both retrieval methods can supply passages to the same answer model, and saved answers include source citations or state that the evidence is insufficient. Unanswerable cases remain visible for manual evaluation.
5. A user can run the documented workflow without modifying the original vault; all project quality gates pass.

## Boundaries

- Always: show which provider receives text; preserve source paths and run settings; keep generated private data out of Git.
- Never: modify source vault pages, commit secrets, or edit `.env`, `.venv/`, `dist/` or `uv.lock` directly.
- Any new dependencies must be installed through `uv`; do not change existing MCP behavior as part of this experiment.

## Out of scope

- Production deployment and new MCP tools.
- Numerical benchmarking and a labeled evaluation dataset.
- Graph-based reranking, inferred relationship extraction and a dedicated graph database.
- NBA text-to-SQL or ontology generation.

## Open questions

- Which answer model/provider should be used for the grounded-answer comparison? Mistral is a possible choice; embedding alone cannot generate answers.
