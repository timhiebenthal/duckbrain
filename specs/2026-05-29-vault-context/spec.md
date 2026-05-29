# vault_context + Session Plugin — Proactive Context Loading

## Overview

Two deliverables make DuckBrain load vault context automatically at session
start. Setup: configure MCP server + install the plugin.

| Component | What | When | Who triggers |
|---|---|---|---|
| `vault_context` MCP tool | Keyword search over vault | AI calls after seeing prompt | Model |
| Session plugin | Injects dailies + learnings ritual + vault tags | First model call per session | `experimental.chat.system.transform` |
| Compaction hook | Preserve vault context through compaction | Before session compacted | `experimental.session.compacting` |

## Requirements

### `vault_context` MCP tool
1. **Keyword search**: Accepts `keywords: list[str]`, joins with spaces, runs
   FTS search via `handle_vault_search`. `search_limit` controls count.
2. **Daily notes** (optional): `include_dailies: bool` reads today + yesterday
   from `daily/{date}.md`. Plugin pre-loads dailies; tool retains capability
   for mid-session reloads.
3. **Single response**: All results in one dict.

### Session plugin (`opencode/plugins/duckbrain-session-init.js`)
4. **System prompt injection** (`experimental.chat.system.transform`): On first
   model call per session, injects: today's + yesterday's daily notes, learnings
   ritual (triggers, session rituals, format), and vault tags overview. Injected
   into system prompt — model sees it, user doesn't.
5. **Vault tags overview**: Scans `wiki/**/*.md` YAML frontmatter for tags,
   deduplicates via Set, injects "Available tags: ai, mcp, memory, ..." so the
   model can decide intelligently whether to search.
6. **Compaction hook** (`experimental.session.compacting`): Pushes vault context
   preservation rules into compaction prompt so vault knowledge survives
   summarization.

## Scope

### In Scope
- `vault_context` MCP tool + registration + tests
- Session plugin (system.transform injection, vault tags scan, compaction hook)
- README plugin install docs
- Version bump to 0.3.0

### Out of Scope
- Guard hook (removed — vault tags overview makes it redundant; model decides)
- Keyword extraction from raw prompt (model responsibility)
- Semantic/vector search
- Auto-save on idle (deferred)

## Technical Approach

**`vault_context` tool**: Thin orchestrator over `handle_vault_search` +
date-based daily file reads.

**Plugin injection flow**:
```
session.created → read dailies from VAULT_PATH/daily/ → scan wiki/**/*.md for tags
  → cache context block in sessions[sid].contextBlock

experimental.chat.system.transform (first call per session)
  → push context block to output.system → model sees it invisibly

experimental.session.compacting
  → push preservation rules to output.context → survives summarization
```

**No `client.session.prompt`**: Switched to `system.transform` — avoids visible
chat bloat. Standard pattern used by context-mode, hindsight, ICM.

## Files Changed

| File | Change |
|---|---|
| `src/duckbrain/tools/vault_context.py` | New MCP tool |
| `src/duckbrain/server.py` | Registered `vault_context` |
| `tests/test_vault_context.py` | 6 TDD integration tests |
| `opencode/plugins/duckbrain-session-init.js` | Session plugin (2 hooks) |
| `README.md` | Tool docs + plugin install |
| `CHANGELOG.md` | 0.3.0 entries |
| `pyproject.toml` | Bump to 0.3.0 |

## Success Criteria

- `uv run pytest` — 78/78 pass
- `uv run ruff check src/duckbrain/` — 0 errors
- `uv run mypy src/duckbrain/` — 0 errors
- Plugin: new session → model has dailies + learnings + vault tags in system
  prompt (invisible), vault_context tool call visible
- Compaction: vault context preservation rules appear in compaction summary
