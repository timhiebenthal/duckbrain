# Vault RAG experiment

This separate command compares passage-level DuckDB BM25 with Mistral embeddings and stores a directed graph of authored wiki links. It does not change MCP behavior or edit vault files. Results are for qualitative inspection, not numerical evaluation.

## Data handling and setup

Run from the repository root. `uv sync` installs project dependencies. Set `MISTRAL_API_KEY` in your shell; do not put it in the repository. Choose the answer model explicitly. Indexing sends selected passage text to Mistral's embeddings API; comparison sends the question to the same API; answering sends the question and retrieved passages to Mistral's chat API. These calls may incur charges and are subject to your provider's data policies. A custom Mistral-compatible endpoint can be selected with `MISTRAL_BASE_URL`; it receives the same data and the API key.

The default database `.rag/corpus.duckdb` is ignored by Git. It contains private source text, vectors, questions, answers, and historical runs; do not commit or share it. If choosing another path, keep it outside the vault and ensure Git ignores it, including DuckDB WAL files and temporary index files. Remove the database and its surrounding private directory when finished.

## Select and index

The scanner includes daily notes and correctly frontmatter-tagged wiki pages by default. Exclusions are vault-relative paths and exclude a file or directory and its descendants. Inspect page count and character volume without a provider call:

```bash
uv run python -m duckbrain.rag preview /path/to/vault --exclude daily
```

Index the same selection (omit `--exclude daily` to include daily notes):

```bash
export MISTRAL_API_KEY='your-key'
uv run python -m duckbrain.rag index /path/to/vault --exclude daily --model mistral-embed
```

The count and text volume are printed before embedding. Embedding requests are spaced at least 10 seconds apart by default; use `--request-interval` to change the interval. Rate-limit responses are retried up to three times with backoff. Repeat the index command after changes; unchanged passage vectors are reused, new or changed passages are embedded, and deleted or excluded pages leave the current index. The embedding cache and old runs remain in the private database. A new model causes re-embedding. Indexing builds a temporary database next to the destination and replaces it only after success; close other database connections before indexing. Fixed 1,000-character passages use character offsets into the parsed page body. Full file hashes and the corpus version record source changes.

## Compare and answer

Compare the classic page search against embedding retrieval directly:

```bash
uv run python -m duckbrain.rag ab
```

Enter a question at the prompt, or pass `--question 'your question'`. Use `--limit 5` to set the number of results per method. Each comparison saves `bm25_result.md` (full matched pages) and `rag_result.md` (matched passages) in a new timestamped folder under `.rag/results/`. Both files include the question, rank, path, and score. The files contain private vault text; use `--output-dir` to choose another location. The command reads `.rag/classic.duckdb` and `.rag/corpus.duckdb`; override them with `--classic-database` and `--database` if needed. It sends the question to Mistral for one embedding without saving a run in the database. The classic index is a snapshot; rebuild it to a new path if the vault has changed. BM25 and cosine scores have different scales.

The command also prints and saves `comparison.json` with DuckDB's stemmed BM25 search terms, result paths and scores, RAG passage IDs, unique page counts, character counts, and estimated tokens. Token estimates are rounded up at one token per four characters; they are a rough sizing aid, not model-specific tokenization or API usage. BM25 counts full page bodies, while RAG counts returned passages, including repeated pages. These are retrieved results, not text sent to an answer model; this command does not generate an answer.

For passage-level BM25 versus embedding retrieval, with results saved in the database:

```bash
uv run python -m duckbrain.rag compare --question 'How is agent memory organized?' --limit 5
uv run python -m duckbrain.rag answer --run RUN_ID_FROM_COMPARE --model YOUR_MISTRAL_CHAT_MODEL
```

Comparison prints JSON with `run_id` and the two ranked lists. Both lists use the same corpus, passage boundaries, question and maximum result count. BM25 uses DuckBrain's title/tags/body FTS configuration, but indexes passages rather than whole pages, so rankings can differ from MCP search. Embedding ranking uses exact cosine similarity. Answers use the same instruction and chosen model for both lists, with rank numbers as citations. `valid: false` flags missing or invalid citations; citation validation checks references, not whether a claim is actually supported. Read the passages and answers to judge grounding. An answer can explicitly say `Insufficient evidence.`

## Inspect with SQL

Save a separate snapshot of the classic page-level index (no API key or provider call required):

```bash
uv run python -m duckbrain.rag classic "$VAULT_PATH"
```

This writes `.rag/classic.duckdb` and refuses to overwrite an existing file. It is a snapshot, so use a new path to capture later vault changes. Normal MCP searches still build their own in-memory index. Both database files contain private vault text and are ignored by Git.

To inspect both databases in the DuckDB UI, run `duckdb -ui` from the repository root and run these commands in a UI notebook:

```sql
ATTACH '.rag/classic.duckdb' AS classic (READ_ONLY);
ATTACH '.rag/corpus.duckdb' AS rag (READ_ONLY);
SELECT count(*) FROM classic.pages;
SELECT count(*) FROM rag.embeddings;
```

Open the database with a DuckDB client, or use Python:

```bash
uv run python -c 'import duckdb; c=duckdb.connect(".rag/corpus.duckdb", read_only=True); print(c.execute("SHOW TABLES").fetchall())'
```

Examples (replace the path or run ID):

```sql
SELECT filepath, title, kind, source_hash FROM pages;
SELECT id, filepath, position, text FROM passages;
SELECT id, filepath, model, config, vector FROM embeddings;
SELECT * FROM runs ORDER BY id;
SELECT method, rank, filepath, text, score FROM results WHERE run_id = 'RUN_ID' ORDER BY method, rank;
SELECT method, model, answer, cited_passages, valid, invalid_citations FROM answers WHERE run_id = 'RUN_ID';
-- Outgoing links, including unresolved targets (target_path IS NULL):
SELECT * FROM edges WHERE source_path = 'daily/2026-05-28.md';
-- Backlinks:
SELECT * FROM edges WHERE target_path = 'wiki/concepts/example.md';
-- Two hops through resolved pages:
SELECT a.source_path, a.target_path AS via, b.target_path, b.raw_target
FROM edges a JOIN edges b ON a.target_path = b.source_path
WHERE a.source_path = 'daily/2026-05-28.md';
```

Edges are explicit authored links, not inferred facts. Resolution matches a unique indexed title, filename stem, or vault-relative path case-insensitively. Aliases and headings do not affect page resolution; unresolved, ambiguous, excluded and missing targets have a null `target_path`. Raw targets retain headings.
