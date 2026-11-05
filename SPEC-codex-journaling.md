# Spec: Codex Journaling

## Objective

Give DuckBrain users a consistent way to preserve useful Codex CLI session progress and learnings in their vault. This capability is `codex-journaling` in [the capability map](CAPABILITY-MAP.md).

## Requirements

- Provide a discoverable Codex skill users can invoke to journal the current session. It reviews completed work, decisions, discoveries and unfinished work; includes user-provided context; and reports what was saved and where.
- Use existing DuckBrain MCP tools to inspect the current daily note and avoid repeating material already recorded. Append a concise summary of progress, meaningful learnings and open items to today's daily note with `vault_write`.
- Consider significant reusable knowledge for a permanent wiki page, using existing vault tools and avoiding duplicates. Do not claim a write succeeded when a tool call fails or needs approval.
- Provide instructions encouraging Codex to capture useful learnings proactively during work, consistent with the existing OpenCode learning ritual. Skip writes when there is nothing new to record.
- Investigate Codex CLI events for automatic journal reminders. Add a reminder only if an actual CLI test verifies its event and delivery; otherwise document the limitation and retain explicit journaling and instruction-driven capture.
- Support manual installation and document how to invoke the skill and verify a journal entry in a temporary vault. Do not require a dedicated installer.

## Success criteria

- An invoked skill can review a session and append a useful, non-duplicate daily entry using the existing MCP tool interface, and reports the outcome accurately.
- A real Codex CLI smoke test with a temporary vault verifies the explicit workflow, or documents an environment-specific blocker without claiming success.
- The skill contains actionable proactive-capture instructions; any automatic reminder has a verified trigger or is explicitly documented as unavailable or unverified.
- Existing OpenCode and Claude integrations continue to behave as before. Ruff, formatting, mypy and the complete pytest suite pass.

## Technology and structure

The integration targets Codex CLI skills and the existing Python 3.10+ DuckBrain MCP server. Codex integration files and documentation live under `codex/`; Python source and tests, if needed, live under `src/duckbrain/` and `tests/`. Preserve the scanner → indexer → writer → tools → server architecture and existing shared types.

## Commands

```bash
uv run ruff check src/duckbrain/
uv run ruff format --check src/duckbrain/
uv run mypy src/duckbrain/
uv run pytest
```

## Code style

Follow existing conventions and use DuckBrain's tool interface. For example, the server exposes:

```python
def vault_write(kind: str, title: str, content: str, tags: list[str]) -> dict:
    """Create a new wiki page or append to today's daily note."""
```

Keep skill instructions specific, concise and aligned with `opencode/commands/journal.md`. The writer supplies daily entry timestamps.

## Testing strategy

Use test-driven development for production behavior: demonstrate the expected failing test before implementation, then run focused tests and the complete quality gates. Use the real filesystem and `temp_vault` for any Python behavior. Verify skill installation and invocation with a real Codex session and a temporary vault; report any approval-policy limitations accurately. Verify any automatic reminder in an actual CLI session before documenting it as supported.

## Boundaries

- **Always:** Use existing vault tools for writes, avoid duplicates, and distinguish requested writes from completed writes.
- **Ask first:** Changes outside this capability or changes to agreed user-facing behavior.
- **Never:** Edit `.env`, `.venv/`, `dist/`, or `uv.lock` directly; remove failing tests to pass checks; claim unverified hooks work.

## Out of scope

- Replacing the context snapshot mechanism (`codex-context`).
- A dedicated installer or complete combined onboarding (`codex-setup`).
- Changes to OpenCode or Claude Code integration behavior.
- Guaranteed capture after a terminal or process is abruptly closed.

## Open questions

- Which Codex CLI events can deliver an automatic reminder in the supported installation mode? Test before deciding whether to include one.
- Can an actual Codex CLI session invoke DuckBrain write tools under the available approval policy? If not, record the limitation and test in an environment that permits the call before claiming end-to-end success.
