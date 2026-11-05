# Spec: Codex Context

## Objective

Give Codex CLI users automatic access to their DuckBrain vault context at session start, approaching the experience provided by the OpenCode integration without changing existing clients' behavior.

## Requirements and success criteria

- Supply the context categories used by OpenCode: vault topic tags, `imprint.md`, the recent vault log, and today's and yesterday's daily notes, using local dates.
- Prefer automatic context injection when verified with the actual Codex CLI. If it is unreliable or unavailable, instruct Codex to retrieve context through DuckBrain MCP tools at session start.
- Make Codex-specific injection opt-in so existing integrations do not receive duplicate context.
- Missing optional vault files do not prevent the server or session from starting.
- A real Codex CLI smoke test with a temporary vault demonstrates that a fresh session can access the expected context without an explicit user request.
- Document observed refresh, resume and compaction behavior, including any behavior not verified. Do not claim an MCP handshake is equivalent to OpenCode's system prompt transform without evidence.

## Technology and structure

Python 3.10+ with the existing FastMCP server and DuckDB; Codex CLI is the target client. Server code is under `src/duckbrain/`, tests under `tests/`, and integration documentation belongs alongside the existing client documentation. Use the existing scanner → indexer → writer → tools → server layering where applicable.

## Commands

```bash
uv run ruff check src/duckbrain/
uv run ruff format --check src/duckbrain/
uv run mypy src/duckbrain/
uv run pytest
```

## Code style

Follow the existing Python conventions, type annotations, and thin server wrappers. For example:

```python
@server.tool()
def vault_info() -> dict:
    """Get vault structure stats."""
    return handle_vault_info(vault_path)
```

## Testing strategy

Follow test-driven development: write a failing test, confirm the expected failure, implement minimally, then run focused tests and the full quality gates. Use `temp_vault` and the real filesystem and DuckDB rather than mocks. Cover context contents, local dates, missing files, and the opt-in boundary. Exercise a real Codex CLI session against a temporary vault; document unverified resume and compaction behavior rather than treating them as verified.

## Boundaries

- **Always:** Preserve existing clients' default behavior, keep instructions and vault content bounded to the integration's needs, and run the quality gates before committing.
- **Ask first:** Changes outside the approved context capability or changes to its agreed user-facing behavior.
- **Never:** Edit `.env`, `.venv/`, `dist/`, or `uv.lock` directly; remove failing tests to pass checks.

## Out of scope

- Journal skills and automatic journal reminders (`codex-journaling`).
- Complete cross-capability setup documentation (`codex-setup`).
- A dedicated installer.
- Changes to OpenCode or Claude Code integration behavior.

## Open question

Determine through a CLI experiment what MCP handshake instructions can carry, when Codex receives them, and whether their contents refresh on resume or after compaction. Select the implementation only after that observation.
