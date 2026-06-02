# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2026-06-01

### Fixed

- **Daily note headings now carry the full local date + time, not just
  the time**: previously the server stamped `## HH:MM — Title`; now it
  stamps `## YYYY-MM-DD HH:MM — Title`. The full timestamp is
  self-speaking (no need to look at the filename to know when an entry
  was made) and works for cross-file queries, grep, and chunking — e.g.
  "show me everything from 2026-06-01 22:00 onward" returns hits
  without having to align filename and heading.

- **Daily note no longer has a redundant H1**: the file path
  (`daily/YYYY-MM-DD.md`) already carries the date, so the writer no
  longer prepends `# YYYY-MM-DD` as the first line. Old daily files
  with the redundant H1 can be migrated manually (one-time, on the
  user's vault).

## [0.4.0] - 2026-06-01

### Fixed

- **TZ bug in vault context plugin**: `todayStr()` / `yesterdayStr()` now
  use `toLocaleDateString("sv-SE")` for local timezone, not
  `toISOString().slice(0, 10)` (which returns UTC). Users in non-UTC
  timezones (e.g. America/Los_Angeles) now get the correct "today" daily
  note throughout the day, not just after late-afternoon local time.
  Without this fix, a user in UTC-8 would see yesterday's daily note
  injected as "today" until 4pm local time, and a just-rolled-over daily
  note would not be picked up until late afternoon.

- **Hallucinated timestamps in daily note ritual**: the ritual block
  (and the v2.1 session.idle nudge) previously told the model to write
  `## HH:MM — Title` with `HH:MM` as a literal placeholder. The model
  would then guess a time, producing entries like "## 14:30" that
  don't match the actual local clock. Fixed by moving the timestamp
  guarantee to the server (`writer.py`'s new
  `_ensure_timestamp_on_heading()`), which prepends `HH:MM —` to the
  section heading on every daily-note write. The model no longer has
  to know about or guess the time — it just writes the content; the
  server stamps it. DRY: same guarantee for every MCP client
  (OpenCode, Cursor, Claude Code, etc.).

- **`tail()` edge case in vault context helpers**: `tail(text, 0)` previously
  returned the full string due to JavaScript's `slice(-0) === slice(0)`
  quirk. Now correctly returns empty string for `lines <= 0`. Caught by
  unit test, no production caller passes 0 — but the contract should hold
  for any input.

### Added

- **Tests for vault context plugin helpers**
  (`opencode/plugins/vault-context-helpers.test.ts`): 35 unit tests
  (was 30; +5 for `buildIdleNudgePrompt`) covering `tail`,
  `todayStr`, `yesterdayStr`, `loadTags`, `loadSessionContext`,
  `loadCompactionSnapshot`, `buildIdleNudgePrompt`. Uses real
  temp directories and `setSystemTime` — no mocks, same
  convention as duckbrain's Python tests. Verifies TZ behavior
  in America/Los_Angeles, Asia/Tokyo, and UTC, plus month/year
  boundaries and missing-file fallbacks.

  **`currentTimeStr()` removed** — the timestamp guarantee moved
  to the Python server (`writer.py:_ensure_timestamp_on_heading()`),
  so the plugin no longer needs to compute the time locally.

- **Test infrastructure for OpenCode plugins**
  (`opencode/plugins/package.json`, `tsconfig.json`): bun test config
  with `@types/bun` and `@types/node` for type checking. Run
  `cd opencode/plugins && bun test` to execute.

- **`node_modules/` in `.gitignore`**: prevents accidental commits of
  the opencode/plugins dependency tree.

- **v2.1 — session.idle auto-save** (`opencode/plugins/vault-context.ts`):
  **Added during PR development (2026-06-01)** after a spec review
  caught that the v2 spec incorrectly claimed `session.idle` didn't
  exist in OpenCode. It does — fired via the `event` hook with
  `event.type === "session.idle"`. The plugin now listens for it
  and re-prompts the model with a journal nudge via
  `client.session.prompt()`. The model decides whether anything is
  worth saving; if so, it calls `vault_write`. Best-effort
  fire-and-forget for the "agent finished naturally" case. Window
  close is acceptable loss per the design decision documented in
  spec D2 (manual `/journal` covers the "guaranteed save" case).

  **Not part of the original v2 plan.** This was discovered mid-PR
  when reviewing the spec, validated against the OpenCode SDK
  (`@opencode-ai/sdk` `EventSessionIdle` type), and added in the
  same release because the change is small (~25 lines) and the spec
  already had the v3 stub documented in "What's still missing →
  No idle auto-save → Possible future approaches." If you'd prefer
  this in a separate v0.4.1 release, the v2.1 commit
  (`5b39520`) can be cherry-picked off cleanly.

### Changed

- **Vault context plugin v2** (`opencode/plugins/vault-context.ts`):
  Significant rewrite of the v1 plugin. The v1 design injected ~6K chars
  of vault context (tags + log + 3 daily notes) on every model call —
  wasteful, and relied on a prose instruction for journaling that the
  model could ignore. v2 splits injection into two tiers based on
  freshness contract.

  - **Tiered injection**: tags always injected (~2K chars, routing
    signal — "is this topic in my vault?"). Session context (log tail +
    today + yesterday daily notes, ~4K chars) injected only on first
    model call and after compaction. **~67% reduction in vault-related
    system prompt overhead after the first call** (was ~60% in earlier
    spec draft — actual math is 4K/6K).

  - **Compaction improvements**: stronger journal nudge ("⚠️ Journal
    checkpoint — save learnings now"), resets session context flag so
    full context re-injects after compaction, compact snapshot (15 log
    lines not 30, today's daily only not 3).

  - **Today/yesterday labeling**: daily notes get dedicated
    `<vault-session-context>` sections with `## 📅 Today's daily note`
    and `## 📅 Yesterday's daily note` headers, instead of being buried
    in a batch with the log tail.

  - **Refactored for testability**: pure functions moved to
    `opencode/plugins/vault-context-helpers.ts` per AGENTS.md TDD
    mandate. Main plugin file imports from helpers. Same external
    behavior, internal structure split for unit testing.

- **Spec corrections** (`specs/2026-05-31-vault-interaction-robustness/spec.md`):
  Two factual errors caught in review and corrected.

  - **`session.idle` does exist in OpenCode** — fired via the `event`
    hook with `event.type === "session.idle"`. Verified in
    `@opencode-ai/sdk/dist/gen/types.gen.d.ts` (the `EventSessionIdle`
    type) and official docs at https://opencode.ai/docs/plugins/. The
    spec previously claimed "OpenCode has no `session.idle` hook" — this
    was wrong. The handler is still **fire-and-forget** (return promise
    is dropped at `plugin/index.ts` L138, per OpenCode issue #16879), so
    we cannot block the session transition. v3 candidate: add an
    `event` hook listener for `session.idle` as best-effort auto-save.
    For v2, compaction remains the only guaranteed delivery channel
    for journal nudges.

  - **Reduction is ~67%, not ~60%** — actual math is 4K saved / 6K
    baseline. Spec previously understated the win.

### Changed

- **Timestamp guarantee moved from OpenCode plugin to Python server**
  (`src/duckbrain/writer.py`): The TS plugin previously computed
  `HH:MM` locally via `currentTimeStr()` and pre-filled the ritual
  template. That worked for OpenCode but meant every other MCP client
  (Cursor, Claude Code, raw `curl`) had to re-implement the same
  logic to get real timestamps — a DRY violation.

  The fix: `_ensure_timestamp_on_heading()` in `writer.py` now
  prepends `HH:MM —` to the section heading on every daily-note
  write. The model never has to know the time. The TS plugin's
  `currentTimeStr()` and the `time` parameter on
  `buildIdleNudgePrompt` were removed; the ritual template now uses
  `## Topic\n\nDetails` and the server stamps it.

  **Architectural rationale** (per concept page
  `wiki/concepts/common-denominator-principle-for-shared-code.md`):
  when a server is the common denominator across clients, the
  *guarantee* lives in the server. The client owns UX niceties; the
  server owns invariants.

### Notes

- **Versioning note**: `0.4.0b1` was previously published to PyPI for
  the `configurable-vault` feature (still on `feat/configurable-vault`
  branch, not yet on main). This release is the v2 vault-context plugin
  on a separate branch. If both land together as a coordinated release,
  bump this entry to `0.4.0` and merge `feat/configurable-vault` first
  or alongside. If you want beta-tagged coordination, rename this to
  `0.4.0b2` before tagging.

- **No change to public MCP API**: the four existing tools (`vault_search`,
  `vault_read`, `vault_write`, `vault_info`) plus `vault_context` work
  exactly as before. This release is internal plugin + tooling
  improvements.

- **Quality gates**: `bun test` 35/35, `bunx tsc --noEmit` clean,
  `uv run ruff check` clean, `uv run mypy` clean, `uv run pytest` 93/93.

## [0.3.1] - 2026-05-30

## [0.3.1] - 2026-05-30

### Fixed

- **Daily note deduplication**: `_write_daily` now detects duplicate `## {title}`
  headings and merges in-place instead of appending a second copy.
- **`target_date` parameter**: `_write_daily`, `write_page`, and `handle_vault_write`
  accept optional `target_date: str | None = None` to write to a specific date's
  daily file instead of always targeting today.

## [0.3.0] - 2026-05-29

### Added

- **`vault_context` tool**: New MCP tool that bundles today's + yesterday's daily
  notes and keyword-based vault search into a single call. Reduces session-start
  round-trips from 3 to 1.
- **Session plugin** (`opencode/plugins/duckbrain-session-init.js`): OpenCode plugin
  that injects daily notes and the learnings ritual at `session.created` — no AI
  action needed. The learnings ritual moves out of AGENTS.md into the plugin payload.

## [0.2.0] - 2026-05-29

### Added

- **BM25 score exposure**: `vault_search` results now include a numeric `score` field
  from DuckDB's BM25 ranking, letting agents judge result relevance.
- **Context-aware snippets**: Snippets extracted from ~200 characters around the
  first query term match rather than the first 100 characters of body text.
  Snippet containment improved from 45% to 81%.
- **Result limit parameter**: `vault_search("memory", limit=10)` caps results,
  defaulting to 20. Pass `limit=None` for unlimited.
- **`matched_tags` populated**: The existing `matched_tags` field on search
  results is now filled with the tag filter used in the query.
- **Search quality benchmark**: `tests/benchmarks/search_quality.py` with
  `--label` flag for versioned snapshot archiving.
- **Marimo benchmark dashboard**: `uv run marimo edit notebooks/benchmark_dashboard.py`
  visualizes benchmark snapshots across versions.

### Changed

- **Page count bump**: test fixtures updated from 6 to 7 pages (added knowledge
  graph concept page with long body for snippet testing).
## [0.1.2] - 2026-05-29

### Added

- **OpenCode config templates** in `opencode/`: pre-response learning guard, trigger table, session rituals, `/journal` slash command, and example MCP config. Copy into `~/.config/opencode/` to enable automatic learning capture and session journaling.

### Fixed

- **MCP server name** renamed from `"duckbrain-vault"` to `"duckbrain"` to match the MCP config key users configure.

## [0.1.0] - 2026-05-28

### Added

- **vault_info**: MCP tool returning vault structure stats (page counts by kind, tags, last modified).
- **vault_search**: Full-text search over vault wiki pages via DuckDB BM25, with kind and tag filters, plus per-page created/updated dates.
- **vault_read**: Read a page by title or filepath, returning full markdown content.
- **vault_write**: Create wiki pages (entity, concept, source, synthesis) with YAML frontmatter and auto index/log updates. Append to daily notes (kind=daily).
- **DuckDB FTS index**: Lazy, in-memory full-text search built on first query — no persistent database.
- **Daily note scanning**: vault_search indexes daily/*.md files as kind=daily.
- **MCP stdio transport**: FastMCP server registered as `duckbrain` CLI command.
- **E2E tests**: Subprocess-based MCP client tests covering all 4 tools.
- **Error handling**: Graceful handling of log/index write failures, non-UTF8 files, missing sections.
