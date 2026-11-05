# Tasks: Codex Journaling

## 1. Verify CLI boundaries

- [x] Test a `UserPromptSubmit` hook in a temporary CLI session and confirm its output reaches the model. Codex CLI 0.166.0 reported the hook marker.
- [x] Test a DuckBrain MCP write against a temporary vault in a CLI session; a test-only server approval setting allowed the write under the environment's `never` approval policy.
- Acceptance: Event and write results are reproducible or explicitly identified as blocked. Dependencies: none. Files: temporary artifacts only. Verification: inspect CLI output and temporary vault.

## 2. Implement journal workflow

- [x] Create a Codex journal skill that checks today's note, writes only new progress, learnings and open work using the actual MCP signature, considers reusable wiki knowledge, and reports success or failure.
- [x] Add concise proactive capture guidance to Codex setup instructions without changing other integrations.
- Acceptance: Explicit journal and proactive workflows follow the spec and avoid false success reports. Dependencies: task 1. Files: `codex/skills/duckbrain-journal/SKILL.md`, `codex/README.md`. Verification: validate skill metadata and run a real Codex session where permitted.

## 3. Add verified reminder and complete checks

- [x] If task 1 proves reminder delivery, provide a manually installable reminder hook; otherwise document the limitation without claiming a hook works.
- [x] Document skill installation, invocation, reminder setup and approval limitations; run the repository quality gates and report smoke-test limitations.
- Acceptance: Setup is reproducible and event claims match observed behavior. Dependencies: tasks 1–2. Files: `codex/` and relevant focused tests. Verification: real CLI hook check and `uv run ruff check src/duckbrain/`, `uv run ruff format --check src/duckbrain/`, `uv run mypy src/duckbrain/`, `uv run pytest`.

## Checkpoint

- [x] Quality gates pass; a temporary-vault skill invocation wrote an entry and a second invocation skipped the duplicate. The reminder event was verified separately; abrupt session closure is not guaranteed.
