# Vault Interaction Robustness v2

## Context

The v1 vault-context plugin (`opencode/plugins/vault-context.ts`) injected all
vault context (tags + log tail + 3 daily notes) on EVERY model call — ~6K+ chars
of system prompt overhead. It relied on a prose instruction for journaling,
which the model could ignore.

This spec documents what was implemented, what was rejected, and why.

## Sources consulted

| Vault page | Filepath | Informed which decision |
|---|---|---|
| [[Claude Code Hooks - all 23 explained and implemented]] | `wiki/sources/Claude Code Hooks - all 23 explained and implemented.md` | D2 (Stop hook limitation), D3 (Prose vs tools) |
| [[Does OpenCode Support Hooks? A Complete Guide to Extensibility]] | `wiki/sources/Does OpenCode Support Hooks A Complete Guide to Extensibility.md` | D1 (Tiered injection), D2 (Hook surface) |
| [[Your OpenCode Agent Forgets Everything Between Sessions. Here's the Fix.]] | `wiki/sources/Your OpenCode Agent Forgets Everything Between Sessions. Here's the Fix.md` | D2 (Hindsight idle auto-save), D3 (Retain/recall/reflect) |
| [[OpenCode Memory Plugin Patterns]] | `wiki/concepts/opencode-memory-plugin-patterns.md` | D2 (Guard hook rejection, compaction survival) |
| [[OpenCode Plugin Sandbox Capabilities]] | `wiki/concepts/opencode-plugin-sandbox-capabilities.md` | D4 (Tags from file, not scan) |
| [[Debugging OpenCode Plugins with Probes]] | `wiki/concepts/debugging-opencode-plugins-with-probes.md` | D2 (Hook shapes — `console.log` works, `client.app.log` hangs) |
| [[DuckBrain Session Plugin — What It Does and Why]] | `wiki/concepts/duckbrain-session-plugin-what-it-does-and-why.md` | Baseline — what v1 did and why it was insufficient |

**Key insights from sources:**

- **Hooks fire regardless of context pressure** (Claude Code Hooks) — hooks catch
  things prose rules miss. But we have no Stop hook to enforce final write.
- **OpenCode has 6 extension mechanisms** (Extensibility Guide) — plugins, SDK,
  MCP, GitHub, custom commands, non-interactive. Plugin path is the only one
  that fits this work.
- **Hindsight auto-hooks** (Hindsight source) — recall on start, retain on idle,
  preserve through compaction. Idle hook is the key — but OpenCode doesn't
  expose it.
- **Agent tunnels after ~8 tool calls** (OpenCode Memory Plugin Patterns) —
  guard hooks catch this. But our guard implementation was too noisy (D2).
- **Bun.file() works, everything else blocked** (Sandbox Capabilities) —
  confirmed `wiki/tags.md` is the right path. No directory scanning possible.

## What shipped

### Tiered injection

| Tier | Content | When | Size |
|---|---|---|---|
| 1 | `wiki/tags.md` | Every model call | ~2K chars |
| 2 | Log tail + today + yesterday daily notes | First call + after compaction | ~4K chars |

**How it works:**
- `system.transform` fires on every model call
- Tags always pushed — small, provides topic routing ("is this in my vault?")
- Session context (log + dailies) pushed only when `sessionContextInjected === false`
- Compaction hook resets flag → full context re-injected after compaction

**Today/Yesterday labeling:**
Daily notes get dedicated `<vault-session-context>` sections:
```
## 📅 Today's daily note (2026-05-31)
## 📅 Yesterday's daily note (2026-05-30)
```
Instead of being buried in a batch with the log tail.

### Compaction improvements

- **Stronger journal nudge:** "⚠️ Journal checkpoint — save learnings now"
- **Context reset:** `sessionContextInjected = false` after compaction → full
  context re-injected on next model call
- **Compact snapshot:** 15 log lines (not 30), just today's daily (not 3)

### Guard hook (removed)

**Evaluated and rejected.** See Decision Record below.

### v2.1 — session.idle auto-save (added 2026-06-01)

After spec review caught the `session.idle` availability error, added
the v3 plan to the plugin. When the agent finishes a turn and the
session transitions to `session.idle`, the plugin re-prompts the
model with a journal nudge via `client.session.prompt()`. The model
decides whether anything is worth saving; if so, it calls
`vault_write`.

**Why re-prompt vs direct tool call:** the model knows what's worth
saving (root causes, architecture decisions, debugging journeys). The
plugin doesn't. Bypassing the model means constructing a save
blindly, which is worse.

**Why fire-and-forget:** the `event` hook handler is async but
OpenCode drops the return promise (per opencode issue #16879). The
plugin kicks off the call and accepts the window-close risk.
Compaction + manual `/journal` cover the "guaranteed save" cases —
this just adds a best-effort channel for the "agent finished
naturally" case.

**Recursion guard:** `idleNudgeSent` flag, set synchronously on
first fire, reset on compaction. One nudge per session-segment
between compactions. Even if the re-prompt response triggers
another idle, the flag blocks the second handler.

**Known limitations:**
- The re-prompt appears as a user message in conversation history
  (the `synthetic: true` flag on `TextPartInput` might suppress
  this — worth investigating for v0.4.1).
- Window close = no save. Same as everything else in this spec.
- Fire-and-forget, so the call might not complete before process
  teardown. Acceptable loss per the user's framing: "if you close
  the window, you shouldn't complain that memory is lost."

### Real timestamps, not hallucinated ones (added during PR development, refined after)

**Original fix (v0.4.0a):** the TS plugin's `currentTimeStr()` was
injected into the ritual block and idle nudge so the model saw
`## 14:30 — Title` with the actual local time, not a placeholder.

**Refined fix (v0.4.0b):** the timestamp guarantee moved from the
OpenCode plugin to the Python server (`writer.py`'s
`_ensure_timestamp_on_heading()`). On every daily-note write, the
server prepends `HH:MM —` to the section heading. The model no
longer has to know the time at all.

**Why the move:** DRY. The original fix worked for OpenCode but
meant every other MCP client (Cursor, Claude Code, raw `curl`) had
to re-implement the same logic to get real timestamps. The server
is the common denominator across clients — it owns the guarantee.
The plugin just doesn't tell the model about timestamps anymore
(`## Topic\n\nDetails` in the template); the server stamps it.

**Architectural principle** (see wiki concept page
`wiki/concepts/common-denominator-principle-for-shared-code.md`):
when a server is consumed by multiple clients, the *invariant*
lives in the server; the client owns *UX niceties*. We had the
invariant in the client (DRY violation); now it's in the server.

### v0.4.1 — Self-speaking timestamps + drop redundant H1 (2026-06-01)

**Discovered while reviewing the v0.4.0 PR:** the existing daily
note in the user's vault had a doubled header (`# 2026-06-01` H1 +
`## 22:38 — ...` H2 with only the time), and a query like "show me
everything from 2026-06-01 22:00 onward" required aligning
filename date with heading time — a pain for grep, chunking, and
cross-file queries.

**Two changes in v0.4.1 (still honoring the v0.4.0b server-side
guarantee):**

1. **Heading now carries the full local date + time, not just the
   time.** Server stamps `## YYYY-MM-DD HH:MM — Title` instead of
   `## HH:MM — Title`. Same `_ensure_timestamp_on_heading()`
   function, same idempotency check, just a fuller `strftime`
   format. The full timestamp is self-speaking — a heading can be
   read without consulting the filename.

2. **No more H1 on daily files.** The file path
   (`daily/YYYY-MM-DD.md`) already carries the date, so the
   writer no longer prepends `# YYYY-MM-DD` as the first line on
   new-file creation. Old daily files with the redundant H1 can
   be migrated manually (one-time, on the user's vault).

**Why these aren't a v0.5 feature:** both are tiny, well-tested
extensions of the v0.4.0b invariant. They share the same
architectural story (server owns the format, client doesn't
care). Holding them for v0.5 would be YAGNI ceremony.

### v0.4.1d — Server-side guard against bare-date titles (2026-06-02)

**Discovered in the same PR cycle:** the v0.4.0-era LEARNINGS
convention says to call daily writes with `title="YYYY-MM-DD"`. Under
v0.4.1, `_ensure_timestamp_on_heading()` stamps a full timestamp onto
the title automatically, so passing the date produces a double-stamped
heading like `## 2026-06-02 12:34 — 2026-06-02`. The bug was
documented (3 occurrences in one day) but never caught at the server.

**Fix:** `_write_daily()` now rejects titles matching
`^\d{4}-\d{2}-\d{2}$` with a clear error message and
`success=False`. The file is NOT created on rejection. Caller gets
the warning explaining the convention change and how to fix it
(pass a real section name like `"Topic (Category)"`).

**Why a server-side guard instead of just docs:** the convention is
deeply ingrained in the model's training prompt (LEARNINGS.md
prescribes `title="YYYY-MM-DD"`). Docs alone didn't prevent the bug —
even after documenting the failure mode, the model repeated the same
mistake. Same pattern as the v0.4.0 server-side timestamp guarantee:
when callers can't be trusted to do the right thing, the server
enforces it. Defensive, in line with the existing architecture.

**Tradeoff:** callers using the v0.4.0 convention now get a hard
error instead of a double-stamped file. This is a breaking change
in the strictest sense, but the only caller (the user's OpenCode
session) is already running v0.4.1 and explicitly opted into the new
behavior. The PR's CHANGELOG entry documents the breaking change.

**Architectural takeaway** (see wiki concept page
`wiki/concepts/common-denominator-principle-for-shared-code.md`):
when the server owns a guarantee, evolving the *format* of that
guarantee is also a server concern. The OpenCode plugin never
needed to know about the format change — it still tells the
model to write `## Topic\n\nDetails`, and the server stamps
whichever timestamp format is current.

## Files changed

| File | Change |
|---|---|
| `opencode/plugins/vault-context.ts` | v2 rewrite — tiered injection, compaction improvements, v2.1 session.idle hook |
| `opencode/plugins/vault-context-helpers.ts` | Extracted pure helpers for testability (TDD mandate) |
| `opencode/plugins/vault-context-helpers.test.ts` | 35 unit tests, bun test |
| `opencode/plugins/package.json`, `tsconfig.json` | Test infrastructure |
| `src/duckbrain/writer.py` | Added `_ensure_timestamp_on_heading()` — server-side timestamp guarantee |
| `src/duckbrain/writer.py` (v0.4.1) | Timestamp format `HH:MM` → `YYYY-MM-DD HH:MM`; removed H1 from new daily files |
| `tests/test_writer.py` | +6 tests for the timestamp guarantee (idempotent, single-digit padding, TZ, integration) |
| `tests/test_writer.py` (v0.4.1) | Updated 5 existing tests for new format + H1 absence |
| `src/duckbrain/writer.py` (v0.4.1d) | Reject `title="YYYY-MM-DD"` for daily writes (bare-date guard) |
| `tests/test_writer.py` (v0.4.1d) | +1 test for bare-date rejection |
| `wiki/concepts/duckbrain-session-plugin-what-it-does-and-why.md` | Added v2 architecture section |
| `wiki/concepts/common-denominator-principle-for-shared-code.md` | New concept page — why server owns the guarantee |
| `wiki/concepts/pick-one-dry-beats-belt-and-suspenders.md` | New concept page — why we dropped the client-side pre-fill |
| `CHANGELOG.md` | Unreleased entry |
| `specs/2026-05-31-vault-interaction-robustness/spec.md` | This spec |

## Decision Record

### D1: Tiered injection over all-or-nothing

**Decision:** Split injection into two tiers — tags always, session context
first-call-only.

**Reasoning:**
- Tags (~2K) are a routing signal — model needs them every call to decide
  "should I use vault tools?"
- Log + dailies (~4K) are session context — only needed once at start.
  Re-injecting on every call wastes tokens on unchanged content.
- After first call: ~67% reduction in vault-related system prompt overhead
  (4K/6K; spec previously said "~60%" — actual math favors the larger number).

**Alternatives considered:**
- *Inject everything always (v1)* — Simple but wasteful. 6K+ per call adds up.
- *Inject nothing, rely on vault_search* — Model doesn't know what's in the
  vault without tags. Leads to speculative vault_info() calls.

### D2: Compaction as the only auto-journal trigger

**Decision:** Rely solely on `experimental.session.compacting` for automatic
journal nudges. No `event` hook handler for `session.idle`, no guard hook.

**Reasoning:**
- **`session.idle` event DOES exist** (correction to earlier spec). It's
  fired via the `event` hook with `event.type === "session.idle"`. BUT the
  handler is fire-and-forget — the return promise is dropped at
  `plugin/index.ts` L138. So we cannot block the session transition. We
  can fire off an async write, but cannot guarantee it completes before
  the session ends or before the user closes the window.
- There is no `session.stop` hook. Window close gives <1s.
- Compaction fires when session has been running long → natural "should
  journal" moment. It's the closest we can get to guaranteed delivery,
  because it happens *before* context loss, not at session end.
- Compaction also triggers context re-injection, so the model gets a
  fresh view of the vault + the journal nudge in one shot.

**Why not use `session.idle` in v2:** Same compliance problem as the prose
ritual. The event is fire-and-forget — if we kick off a `vault_write`
call, we can't wait for it to complete. A v3 could use `session.idle`
as a *best-effort* auto-save (fire the write, hope it lands), but it
doesn't replace the compaction nudge as a guaranteed delivery channel.

**Alternatives considered:**
- *Guard hook (tool.execute.after + system.transform nudge)* — Rejected.
  Once triggered at 8 calls, nudge fires on EVERY subsequent model call
  regardless of context. Too noisy. `tool.execute.after` can't inject
  mid-conversation messages — only `system.transform` can, and it fires
  on every call.
- *`event` hook listening for `session.idle`* — Could add as best-effort
  auto-save in v3. Skipped for v2 to ship the compaction path first.
  Same fire-and-forget limitation as the prose ritual — fire the write,
  hope it lands before process teardown.
- *session.stopping hook* — Proposed in OpenCode PR #16598 (March 2026)
  but not yet merged. **Only helps the "agent finished naturally" case:**
  when the model decides to stop, the hook can re-prompt with a journal
  instruction before the loop break. **Does NOT help the "user closes
  window" case:** the OS kills the process tree before any hook
  completes. Same limitation as Claude Code's Stop-hook exit-2 pattern,
  which also re-prompts only when the agent itself wants to stop.
  Track for v3 as a complement to the in-session compaction channel,
  not a replacement.
- *Auto-save via plugin writing directly* — Plugin can't call MCP tools
  (separate process). Can't write files directly (sandbox blocks
  `import("fs")`).

### D3: No explicit retain/recall/reflect tools

**Decision:** Keep the existing `vault_context` MCP tool. Don't add
`vault_retain`, `vault_recall`, `vault_reflect` tools.

**Reasoning:**
- The Hindsight plugin pattern (explicit tools for memory control) is elegant
  but adds complexity. Our current architecture (prose instruction + tool
  availability) is simpler.
- The model already has `vault_write` (retain), `vault_search`/`vault_read`
  (recall), and can synthesize (reflect). Adding wrapper tools is YAGNI.
- If the model doesn't follow prose instructions, wrapper tools won't help
  either — same compliance problem, different surface.

### D4: Tags from file, not directory scanning

**Decision:** Read `wiki/tags.md` (maintained by DuckBrain writer) instead of
scanning `wiki/**/*.md` frontmatter.

**Reasoning:**
- Plugin sandbox blocks `readdirSync`, `Bun.Glob`, `import("fs")` — all
  directory listing APIs
- `Bun.file(path).text()` works for known file paths
- `wiki/tags.md` is already maintained by DuckBrain's `build_tags_index()`
  on every `write_page` call — always fresh
- Single file read vs directory scan → faster, sandbox-compatible

## What's still missing

### Idle auto-save — implemented in v2.1 ✅

See "What shipped → v2.1 — session.idle auto-save" above. The gap is
closed: best-effort fire-and-forget re-prompt on `session.idle`.
Window-close remains unsolvable by any in-process hook — that's
fundamentally a platform limitation, not a plugin one.

### No session.stop enforcement

**Gap:** When user closes the window, session ends abruptly. No time to write.

**Why not implemented:** Even if a stop hook existed, window close gives <1s.
The compaction journal nudge + the new session.idle re-prompt are the best
proactive alternatives — both fire before the session ends, giving the model
a chance to write. Neither is a guarantee for window-close.

### No selective injection for non-vault tasks

**Gap:** Tags are injected even when the user asks "write a unit test" —
irrelevant vault context in system prompt.

**Why not implemented:** `system.transform` has no access to the user message
(input is `{ sessionID?, model }`). Can't conditionally inject based on
query relevance.

**Possible future approach:** Project-scope detection — if VAULT_PATH points
to a vault unrelated to the current project, skip injection. Could check
if current working directory is inside VAULT_PATH.

## Open questions

1. **Should we add a `vault_search` call on first user message?** — The model
   sees tags but might not search proactively. Could we auto-search based on
   the first user message? No — plugin doesn't have access to it.

2. **Is the compaction journal nudge effective?** — Needs real-world testing.
   The model might still ignore it. If so, the only option is platform-level
   changes (OpenCode adding idle/stop hooks).

3. **Should we move the learnings ritual out of the plugin and into a
   dedicated MCP tool?** — e.g., `vault_journal` that auto-summarizes and
   writes. Keeps the plugin lean, moves compliance to tool-calling (which
   models are better at than prose following). **Probably not** — moving
   from prose-compliance to tool-compliance doesn't fix the underlying
   model-can-still-ignore problem. Same compliance surface, extra steps.

4. **(v2.1 follow-up) Suppress the re-prompt from conversation history** —
   The `synthetic: true` flag on `TextPartInput` might make the nudge
   invisible to the user. Investigate for v0.4.1.
