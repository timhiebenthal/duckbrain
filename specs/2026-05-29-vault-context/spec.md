# vault_context + Session Plugin — Proactive Context Loading

## Overview

Two changes make the AI agent automatically load vault context at session start,
shrink the OpenCode AGENTS.md, and reduce setup to two steps:
configure MCP server + install the plugin.

| Component | What | When | Who triggers |
|---|---|---|---|
| `vault_context` MCP tool | Keyword search over vault | AI calls after seeing prompt | Model (via AGENTS.md instruction) |
| OpenCode plugin | Injects dailies + learnings ritual | `session.created` (pre-prompt) | Plugin hook (automatic) |
| Guard hook | Nudge agent to search vault mid-session | After N tool calls with no vault_search | Plugin hook (automatic) |
| Compaction hook | Preserve vault context through compaction | Before session compacted | Plugin hook (automatic) |

Daily notes and the learnings ritual are deterministic — no model needed.
The plugin injects them before the AI sees any prompt. Keyword search requires
the model to see the prompt first, so that stays as a tool call.

## Requirements

### Functional Requirements

**`vault_context` MCP tool**:
1. **Keyword search**: Accepts `keywords: list[str]`, runs FTS search with
   joined keywords, returns ranked results. `search_limit` controls count.
2. **Daily notes** (optional): `include_dailies: bool` — reads today +
   yesterday daily notes. The plugin pre-loads dailies, but the tool retains
   the capability for mid-session use.
3. **Independent toggles**: `include_dailies` and `include_search` let the
   caller skip either component.
4. **Single response**: All results in one dict.

**OpenCode plugin** (`duckbrain-session-init.js`):
5. **Daily note injection**: On `session.created`, reads today's and
   yesterday's daily notes from `$VAULT_PATH/daily/`, injects as context
   via `client.session.prompt({ noReply: true })`.
6. **Learnings ritual injection**: Injects the learnings instructions
   (what to write, when, how) — replaces the ritual currently in
   `~/.config/opencode/AGENTS.md`.
7. **Guard hook** (`tool.execute.after`): Tracks tool call count per session.
   When >= N tool calls (default 8) have executed with no `vault_search` or
   `vault_context` call since last search, injects a nudge: "Consider searching
   the vault." Fires at most once per search gap to avoid spam.
8. **Compaction hook** (`experimental.session.compacting`): Appends active
   vault context (dailies + any search results from current session) to the
   compaction prompt so important context survives summarization. Without this,
   all vault-loaded context disappears on compaction.

**OpenCode AGENTS.md** (user's `~/.config/opencode/`):
7. **Shrinks**: Learnings ritual removed. Replaced with single instruction:
   `Call vault_context(keywords=[...]) at session start.`

### Non-Functional Requirements

- **No new Python dependencies** — zero changes to `pyproject.toml`
- **No DB schema change** — reuses existing scan → index → search pipeline
- **Plugin is zero-dependency** — uses only Bun built-ins + OpenCode SDK
- **Testable** — Python integration test for `vault_context` tool;
  plugin tested manually (reads files + injects context)
- **Backward compatible** — existing tools untouched

## Scope

### In Scope

- New `vault_context` tool in `src/duckbrain/tools/vault_context.py`
- Registration in `server.py`
- Integration test in `tests/test_vault_context.py`
- Plugin file: `plugin/duckbrain-session-init.js` (or `opencode/plugins/` in repo)
- Plugin install documentation in README.md

### Out of Scope

- Keyword extraction from raw prompt (AI/model responsibility)
- Any modification to existing tools
- Semantic/keyword extraction logic in DuckBrain
- Persistent DuckDB database file
- User's OpenCode AGENTS.md edits (user applies after install — documented)

## Approach

### Technical Approach

**`vault_context` tool** — thin orchestrator:

```
vault_context
  ├── include_dailies=True
  │     ├── Path(vault_path) / "daily" / f"{today}.md" → body or None
  │     └── Path(vault_path) / "daily" / f"{yesterday}.md" → body or None
  └── include_search=True
        └── handle_vault_search(vault_path, query=joined_keywords, limit=search_limit)
```

**Plugin** — three hooks:

```
session.created event
  → plugin gets session ID from event
  → reads VAULT_PATH env var
  → reads daily/{today}.md, daily/{yesterday}.md (Bun file API)
  → builds context block: dailies + learnings ritual
  → client.session.prompt({ path: { id }, body: { noReply: true, parts: [...] } })

tool.execute.after event
  → increment call counter for session
  → if counter >= N and no vault_search/vault_context since last check:
      inject nudge text into tool output
      reset gap flag

experimental.session.compacting event
  → append vault context section to output.context array
  → contains: daily note summaries + search result snippets from current session
```

**Guard hook logic**:
- Track `toolCallCount` and `lastVaultSearchAt` per session
- On `tool.execute.after`: if tool is `vault_search` or `vault_context`, update `lastVaultSearchAt`
- If `toolCallCount - lastVaultSearchAt >= threshold` (default 8), append nudge to tool output
- Nudge text: `"You haven't searched the vault in {N} tool calls. Consider vault_search() or vault_context() for relevant context."`

**Learnings ritual** (injected by plugin, removed from AGENTS.md):

```
## Vault learnings

### Triggers (save IMMEDIATELY):
- AFTER editing code → vault_write what changed + why
- AFTER debugging → vault_write root cause + fix
- AFTER investigating → vault_write discoveries
- AFTER >5 min on any problem → vault_write journey

### During session:
- vault_search for today's daily, read to load prior context
- After non-trivial task, vault_write to daily note
- Format: ## HH:MM — What was done

### End of session:
- vault_write session summary to daily note
- Include: Progress, Learnings, Open questions
```

### Files Changed

| File | Change |
|---|---|
| `src/duckbrain/tools/vault_context.py` | New file — `handle_vault_context()` |
| `src/duckbrain/server.py` | Import + register `vault_context` tool |
| `tests/test_vault_context.py` | New file — integration tests |
| `opencode/plugins/duckbrain-session-init.js` | New file — session plugin |
| `README.md` | Plugin install docs + updated setup steps |

### User Setup (end state)

```
1. Configure MCP: add duckbrain to opencode.json mcpServers
2. Install plugin: copy opencode/plugins/duckbrain-session-init.js to ~/.config/opencode/plugins/
3. (Optional) Shrink ~/.config/opencode/AGENTS.md — remove learnings ritual
```

## Dependencies

**Python**:
- `datetime`, `pathlib` (stdlib) — date construction, file paths
- `duckbrain.tools.vault_search.handle_vault_search` — keyword search

**Plugin**:
- OpenCode SDK (`client.session.prompt` for context injection)
- Bun file API (`Bun.file().text()` for reading daily notes)
- No npm dependencies

## Success Criteria

- `uv run pytest tests/test_vault_context.py -v` — all pass
- `uv run ruff check src/duckbrain/` — 0 errors
- `uv run ruff format --check src/duckbrain/` — all formatted
- `uv run mypy src/duckbrain/` — 0 errors
- `uv run pytest` — full suite passes
- Plugin: manual test — start new session, verify dailies + learnings ritual appear;
  verify guard hook fires after ~8 tool calls without vault search;
  verify compaction hook preserves vault context in compaction summary
- AGENTS.md learnings ritual section can be removed after plugin install

## Notes

- Plugin runs at `session.created` — dailies and learnings injected before
  the AI processes any user prompt. No "forgot to load context" failure mode.
- `vault_context` retains `include_dailies` for mid-session use even though
  the plugin pre-loads dailies at session start.
- The learnings ritual text is embedded in the plugin, not in AGENTS.md.
  Updates to the ritual = update the plugin, not a config file.
