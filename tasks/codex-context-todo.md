# Tasks: Codex Context

## 1. Verify Codex context delivery

- Observation (Codex CLI 0.166.0): a fresh session instructed not to use tools reported the handshake marker as unknown. A second session discovered the server and reported the marker. With a temporary `AGENTS.md` directing discovery and a `ping` call, Codex reported the marker but the MCP call failed because the environment's approval policy is `never`. These results do not establish reliable automatic startup retrieval. Resume, refresh and compaction remain unverified.
- Follow-up: two fresh sessions with a temporary `AGENTS.md` directing server discovery without a tool call both reported the handshake marker. One was asked only to summarize its session context. This establishes a promising discovery-driven path for this CLI version, but not yet a DuckBrain vault smoke test or lifecycle behavior.
- [x] Use a temporary vault and isolated per-invocation Codex configuration to run `codex exec` against a temporary MCP server that advertises a unique handshake instruction. Ask the session to report the marker without mentioning it in the prompt; verify the marker appears. Resume is unverified.
- [x] Test a temporary `AGENTS.md` instruction when the first marker probe fails. The attempted MCP call was rejected by the environment's approval policy; discovery without a call succeeded. Record startup and unverified lifecycle observations in the integration documentation.
- **Acceptance:** Evidence identifies which startup path works; no global configuration or real vault is changed. If neither works, stop and report the blocker.
- **Verification:** Inspect CLI output and temporary MCP request logs; repeat the successful fresh-session test.
- **Dependencies:** None. **Likely files:** integration documentation. **Size:** Small.

## 2. Build the snapshot

- [x] Add failing filesystem tests for tags, imprint, the last 30 log lines, today's and yesterday's local-date notes, and absent optional files; confirm the expected failures.
- [x] Implement a small snapshot builder using the existing vault conventions, with clear labels for each available section; pass the focused tests.
- **Acceptance:** Present files are represented correctly, missing optional files do not fail startup, and date boundaries use local dates.
- **Verification:** `uv run pytest tests/test_vault_context.py -v`.
- **Dependencies:** Task 1. **Likely files:** `src/duckbrain/tools/vault_context.py`, `tests/test_vault_context.py`. **Size:** Small.

## Checkpoint: Snapshot

- [x] Focused tests pass and the snapshot matches the approved context categories.

## 3. Expose context through the verified path

- [x] Add failing real-stdio MCP tests proving the snapshot is available through the selected path and that the default server initialize behavior remains unchanged; confirm failures.
- [x] Implement the opt-in path: set FastMCP instructions from the snapshot only when explicitly enabled and provide a Codex instruction to discover the server at startup.
- **Acceptance:** Enabled Codex sessions receive the snapshot; existing clients' default server behavior remains compatible; optional missing files do not cause a failure.
- **Verification:** `uv run pytest tests/test_e2e.py tests/test_vault_context.py tests/test_server.py -v`.
- **Dependencies:** Tasks 1–2. **Likely files:** `src/duckbrain/server.py`, `src/duckbrain/tools/vault_context.py`, `tests/test_e2e.py`, `tests/test_vault_context.py`, Codex instruction file if needed. **Size:** Medium.

## 4. Document and verify the user flow

- [x] Write context-only manual setup instructions with the exact opt-in configuration, verification steps, snapshot contents, and measured refresh/resume/compaction limitations.
- [x] Run a fresh real Codex CLI session using a temporary vault and the documented setup; verify available context categories without naming their contents in the prompt. Yesterday's note was not present in the smoke-test vault; it is covered by the automated test.
- **Acceptance:** Another user can reproduce the verified context flow without modifying OpenCode or Claude configuration; unsupported behavior is clearly identified.
- **Verification:** CLI smoke test; `uv run ruff check src/duckbrain/`, `uv run ruff format --check src/duckbrain/`, `uv run mypy src/duckbrain/`, `uv run pytest`.
- **Dependencies:** Task 3. **Likely files:** Codex context documentation, `README.md`. **Size:** Small.

## Checkpoint: Complete

- [x] CLI smoke test and all quality gates pass; record any unverified lifecycle behavior.
