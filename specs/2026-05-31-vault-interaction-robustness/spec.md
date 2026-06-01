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

## Files changed

| File | Change |
|---|---|
| `opencode/plugins/vault-context.ts` | v2 rewrite — tiered injection, compaction improvements |
| `wiki/concepts/duckbrain-session-plugin-what-it-does-and-why.md` | Added v2 architecture section |
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

### No idle auto-save

**Gap:** If the model doesn't follow the prose instruction to `vault_write`,
learnings are lost. No automatic mechanism exists.

**Status (post-review):** `session.idle` event DOES exist (`event` hook with
`event.type === "session.idle"`), but the handler is fire-and-forget. A v3
could attach a `session.idle` listener that kicks off a `vault_write` call
as best-effort. Not guaranteed delivery, but better than nothing.

**Possible future approaches:**
- v3: add `event: async ({ event }) => { if (event.type === "session.idle")
  { /* fire-and-forget auto-save */ } }` handler — best-effort, not a
  guarantee. Same window-close limitation as everything else in this section.
- If OpenCode merges session.stopping hook (PR #16598) → use it for the
  "agent finished naturally" case. Window close remains unsolvable by
  any in-process hook — only manual `/journal` or in-session auto-save
  (compaction) works there.
- Workaround: user runs `/journal` command manually before closing the
  session. This is the only **reliable** way to guarantee a save in the
  window-close case.

### No session.stop enforcement

**Gap:** When user closes the window, session ends abruptly. No time to write.

**Why not implemented:** Even if a stop hook existed, window close gives <1s.
The compaction journal nudge is the best proactive alternative — it fires
before the session ends, giving the model a chance to write.

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
   models are better at than prose following).
