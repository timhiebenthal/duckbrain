# AGENTS.md — DuckBrain coding conventions

## User Identity

Read `<vault_root>/imprint.md` at session start — contains communication
preferences, environment details, and work patterns. Maintain it: when
the user states a durable fact or corrects your approach, update imprint.md.

### imprint.md maintenance

When the user:
- States a fact about their setup, preferences, or constraints → update imprint.md
- Corrects your tone or approach → update imprint.md
- Demonstrates a repeated work pattern → consider adding to imprint.md
- Contradicts an existing line → update or remove that line

Do NOT add session-specific details (one-off tasks, current bugs). Only durable facts.

---

## Core mandate

Test-Driven Development. No production code without a failing test first.
Write the test → run to confirm it fails → write minimal implementation →
run to confirm it passes → run full suite.

## Codebase pipeline

The architecture follows a pipeline pattern:

scanner → indexer → writer → tools → server

- **scanner.py**: Reads vault filesystem, parses YAML frontmatter, returns `PageMetadata` objects.
- **indexer.py**: Takes `PageMetadata` list, builds DuckDB in-memory FTS index, provides `search()` and `get_stats()`.
- **writer.py**: Creates markdown pages, generates frontmatter, updates index.md and log.md.
- **tools/*.py**: Thin wrappers that wire scanner/indexer/writer into tool functions (`handle_vault_*`).
- **server.py**: FastMCP server that registers tools with `@server.tool()` and runs on stdio.

Each layer depends on the one before it. Never skip layers.

## Shared types

`src/duckbrain/__init__.py` defines the data model:
- `PageMetadata` — parsed page data (filepath, title, kind, tags, body, created, updated)
- `SearchResult` — FTS hit (title, kind, filepath, snippet, created, updated)
- `WriteResult` — write outcome (success, filepath, warnings)

Do not create new types without adding them here.

## Adding a new MCP tool

1. Create `src/duckbrain/tools/vault_X.py` with `handle_vault_X(vault_path, ...)` 
2. Add tests in `tests/test_vault_X.py` using `temp_vault` fixture from `conftest.py`
3. Register in `server.py`: add import + `@server.tool()` decorated function
4. Run: `uv run ruff check src/duckbrain/`, `uv run mypy src/duckbrain/`, `uv run pytest`
5. Update README.md Tools section with the new tool

## Testing conventions

- Use `temp_vault` fixture from `tests/conftest.py` — creates a real temp directory with wiki structure
- Use `sample_pages` fixture for indexer tests — list of `PageMetadata` objects
- Tests use real DuckDB (in-memory) and real filesystem — never mock
- All test files are prefixed `test_` and live in `tests/`
- Run: `uv run pytest` (all), `uv run pytest tests/test_X.py -v` (specific)

## Quality gates (must pass before commit)

```bash
uv run ruff check src/duckbrain/          # 0 errors
uv run ruff format --check src/duckbrain/  # all formatted
uv run mypy src/duckbrain/               # 0 errors
uv run pytest                             # 59 passed
```

## Commit conventions

```
feat: new feature or tool
fix: bug fix
docs: documentation
chore: config, deps, cleanup
spec: specification files under specs/
```

## Never edit

- `.env` files (user's local secrets)
- `.venv/` (managed by uv)
- `dist/` (build artifacts)
- `uv.lock` directly (use `uv add`/`uv remove`)
