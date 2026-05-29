# vault_context + Session Plugin — Implementation Tasks

## Overview

Two deliverables: `vault_context` MCP tool (Python) and OpenCode session plugin
(JavaScript). Plugin injects daily notes + learnings ritual at `session.created`,
nudges agent to search vault mid-session via guard hook, and preserves vault context
through compaction. Tool handles keyword search when model extracts keywords from prompt.

## Tasks

### SPRINT 1: vault_context MCP Tool

#### Stream A: `tests/test_vault_context.py` → `src/duckbrain/tools/vault_context.py`

⚠️ Sequential within stream: tests must be written and confirmed failing before implementation.

- [ ] **Write failing test: keyword search** — `test_vault_context_keyword_search` in `tests/test_vault_context.py`
  Creates today + yesterday daily files dynamically, calls
  `handle_vault_context(str(temp_vault), keywords=["memory"])`, asserts
  `search_results` contains "Claude Mem" and "Agent Memory Systems",
  asserts `today_daily` has content, asserts `yesterday_daily` has content.

- [ ] **Write failing test: skip dailies** — `test_vault_context_skip_dailies` in `tests/test_vault_context.py`
  Calls `handle_vault_context(str(temp_vault), include_dailies=False, keywords=["memory"])`,
  asserts `today_daily` is None, `yesterday_daily` is None,
  `search_results` still populated.

- [ ] **Write failing test: skip search** — `test_vault_context_skip_search` in `tests/test_vault_context.py`
  Calls `handle_vault_context(str(temp_vault), include_search=False)`,
  asserts `search_results` is `[]`, daily notes still populated.

- [ ] **Write failing test: missing daily** — `test_vault_context_missing_daily` in `tests/test_vault_context.py`
  Does NOT create daily files past what the fixture provides.
  The current date will not have daily files in the temp vault.
  Asserts today_daily is None (unless fixture happens to match date).

- [ ] **Write failing test: empty keywords** — `test_vault_context_empty_keywords` in `tests/test_vault_context.py`
  Calls with `keywords=[]`, asserts `search_results` is `[]`.

- [ ] **Write failing test: search limit** — `test_vault_context_search_limit` in `tests/test_vault_context.py`
  Calls with `keywords=["memory"]`, `search_limit=1`, asserts `len(search_results) == 1`.

- [ ] **Run to verify failure**: `uv run pytest tests/test_vault_context.py -v` → all 6 tests FAIL (module not found)

- [ ] **Implement `handle_vault_context`** in `src/duckbrain/tools/vault_context.py`
  Function signature: `handle_vault_context(vault_path: str, keywords: list[str] | None = None, include_dailies: bool = True, include_search: bool = True, search_limit: int = 10) -> dict[str, Any]`
  - `include_dailies=True`: reads `Path(vault_path) / "daily" / f"{today}.md"` and
    `f"{yesterday}.md"` using `datetime.date.today()` and `timedelta(days=1)`.
    File not found → `None` for that daily.
  - `include_search=True` and `keywords` non-empty: joins keywords with `" "`,
    calls `handle_vault_search(vault_path, query=joined, limit=search_limit)`.
  - `keywords` is `None` or empty: returns `[]` for search_results.
  - Returns dict with keys `today_daily`, `yesterday_daily`, `search_results`.

- [ ] **Run to verify pass**: `uv run pytest tests/test_vault_context.py -v` → 6 PASS

- [ ] **Commit**: `feat: add vault_context MCP tool`

#### Stream B: `src/duckbrain/server.py`

- [ ] **Register vault_context tool** in `src/duckbrain/server.py`
  - Import `handle_vault_context` from `duckbrain.tools.vault_context`
  - Add `@server.tool()` decorated function `vault_context()` that delegates

- [ ] **Run quality gates**:
  - `uv run ruff check src/duckbrain/` → 0 errors
  - `uv run ruff format --check src/duckbrain/` → all formatted
  - `uv run mypy src/duckbrain/` → 0 errors
  - `uv run pytest` → all pass (no regressions)

- [ ] **Commit**: `feat: register vault_context in server`

### SPRINT 2: Session Plugin + Docs

#### Stream A: `opencode/plugins/duckbrain-session-init.js`

- [ ] **Create plugin file** at `opencode/plugins/duckbrain-session-init.js`
  Plugin hooks `session.created` event:
  - Reads `VAULT_PATH` from `process.env` — skips if not set
  - Computes today + yesterday date strings via `new Date().toISOString().slice(0, 10)`
  - Uses Bun file API to read `daily/{date}.md` from vault
  - Builds context injection block:
    ```
    ## Session context (auto-loaded)
    ### Today's daily: YYYY-MM-DD
    {content or "(no daily note yet)"}
    ### Yesterday's daily: YYYY-MM-DD
    {content or "(no daily note yet)"}
    ### Learnings ritual
    {learnings instructions — triggers, session rituals, format}
    ```
  - Injects via `client.session.prompt({ path: { id: sessionID }, body: { noReply: true, parts: [{ type: "text", text: contextBlock }] } })`
  - Gets `sessionID` from `event.properties.session?.id` or similar

- [ ] **Manual verify**: Copy plugin to `~/.config/opencode/plugins/`, start new
  session, confirm daily notes + learnings ritual appear in context.

#### Stream B: `README.md`

- [ ] **Update README.md** — add plugin install step to setup
  - After MCP config step, add: "Copy the session plugin:
    `cp opencode/plugins/duckbrain-session-init.js ~/.config/opencode/plugins/`"
  - Note: after installing plugin, learnings ritual in AGENTS.md is redundant
    and can be removed

- [ ] **Commit**: `feat: add duckbrain session plugin + update README`

### SPRINT 3: Fixes + Refinements (shipped)

- [x] **Fix: flatten hooks** — hooks were nested under `hooks: { }` key, OpenCode expects top-level. Moved `system.transform`, compaction hook, and `event` to top level of return object.
- [x] **Fix: invisible injection** — switched from `client.session.prompt()` (creates visible chat messages) to `experimental.chat.system.transform` (system prompt injection). Model sees it, user doesn't. Standard pattern used by context-mode, hindsight, ICM.
- [x] **Add vault tags overview** — scans `wiki/**/*.md` for YAML `tags:` entries, deduplicates via Set, injects "Available tags (N): ai, mcp, memory, ..." into system prompt. Model can now decide intelligently whether to search vault.
- [x] **Remove guard hook** — vault tags overview makes it redundant. Model sees what's in the vault and decides for itself. Guard hook was a workaround for lack of vault visibility.
- [x] **Tune triggers** — learnings ritual triggers changed from "AFTER editing code" to "AFTER completing a task or fixing a bug". Saves less noise.
- [x] **Commit**: series of atomic commits on `feat/vault-context`

## Summary

### Sprint Overview
| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| 1 | vault_context tool | 10 | A (tests + impl), B (server) |
| 2 | Plugin + Docs | 3 | A (plugin), B (docs) |
| 3 | Guard + Compaction Hooks | 5 | A (plugin hooks) |

### Total Effort
- SPRINTS: 3
- STREAMS: 5
- Tasks: 18

## Notes

- The `vault_context` tool retains `include_dailies` even though the plugin
  pre-loads dailies — useful for mid-session context reloads.
- Plugin uses `noReply: true` on `session.prompt` to inject context without
  triggering an AI response.
- Learnings ritual text embedded in plugin, not in any config file. To update
  the ritual, update the plugin file.
- Test dates use `datetime.date.today()` dynamically — no hardcoded dates.
  Daily files created in test setup to match current date.
- Plugin event shape (`event.properties.session?.id`) is based on typical
  OpenCode event payloads. May need adjustment after testing.

### Quality Standards
- No placeholders — all implementations functional
- TDD: every code change preceded by failing test
- Plugin: zero npm dependencies, Bun built-ins only
