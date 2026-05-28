# Contributing to DuckBrain

## Development setup

```bash
git clone git@github.com:timhiebenthal/duckbrain.git
cd duckbrain
uv sync
```

## Running tests

```bash
uv run pytest                            # all 59 tests
uv run ruff check src/duckbrain/         # lint
uv run ruff format --check src/duckbrain/  # format check
uv run mypy src/duckbrain/              # type check
uv run pre-commit run --all-files       # all hooks
```

## TDD requirement

All production code must be preceded by a failing test. No exceptions.
See `tests/` for the test pattern (fixtures in conftest.py, temp vault per test).

## Codebase structure

- `src/duckbrain/scanner.py` — vault file discovery + frontmatter parsing
- `src/duckbrain/indexer.py` — DuckDB FTS index, search, stats
- `src/duckbrain/writer.py` — page creation, frontmatter gen, index/log updates
- `src/duckbrain/tools/` — MCP tool implementations (thin wrappers)
- `src/duckbrain/server.py` — FastMCP server entry point

## Adding a new tool

1. Create `src/duckbrain/tools/vault_X.py` with `handle_vault_X(vault_path, ...)`
2. Register in `server.py` with `@server.tool()`
3. Add tests in `tests/test_vault_X.py`
4. Run full suite: `uv run pytest`

## Commit conventions

Use conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `spec:`).
