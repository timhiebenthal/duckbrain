/**
 * DuckBrain vault context plugin for OpenCode — v2.1
 *
 * Placement:  ~/.config/opencode/plugins/vault-context.ts  (global)
 *         or  .opencode/plugins/vault-context.ts            (project-local)
 *
 * Requires:   VAULT_PATH env var pointing to your Obsidian vault root
 *
 * Architecture: Tiered injection + compaction preservation + idle auto-save
 *   - Tags: always injected (small ~2K, routing signal)
 *   - Log + dailies: first call only (expensive, session context)
 *   - Compaction: re-inject snapshot + journal nudge
 *   - session.idle: re-prompt model to journal before session ends
 *
 * Proven constraints (from probe):
 *   ✅  Bun.file(path).text()     — works, use this for all file reads
 *   ❌  import("fs") / require     — blocked by sandbox
 *   ✅  process.env / Bun.env     — works
 *   ✅  output.system.push()      — mutations reach the LLM
 *   ✅  experimental.session.compacting — fires, output.context.push() works
 *   ✅  event hook                — fires with EventSessionIdle; client.session.prompt() works
 *
 * v2.1 additions (this file):
 *   - Added `event` hook listening for `session.idle` to re-prompt the
 *     model with a journal nudge via client.session.prompt(). Best-effort
 *     auto-save for the "agent finished naturally" case. Fire-and-forget
 *     by design — window-close is acceptable loss (user can run /journal
 *     before close for guaranteed save).
 *   - Added `idleNudgeSent` flag, reset on compaction (same pattern as
 *     `sessionContextInjected`). Prevents recursion: one nudge per
 *     session-segment between compactions.
 */

import type { Plugin } from "@opencode-ai/plugin"
import {
  loadTags,
  loadSessionContext,
  loadCompactionSnapshot,
  buildIdleNudgePrompt,
  todayStr,
  currentTimeStr,
} from "./vault-context-helpers"

// ─── plugin export ────────────────────────────────────────────────────────────

export const VaultContextPlugin: Plugin = async ({ client }) => {
  const vaultPath = process.env.VAULT_PATH
  if (!vaultPath) return {}

  // Module-scoped flags. Safe only if OpenCode spawns one plugin
  // process per session — verified via probe 2026-05-31 (see
  // specs/2026-05-31-vault-interaction-robustness/spec.md). If
  // OpenCode ever reuses a process across sessions, these leak
  // state — switch to Map<sessionID, bool> using the sessionID
  // from system.transform input.
  let sessionContextInjected = false
  let idleNudgeSent = false

  return {
    // ─── Tiered system prompt injection ──────────────────────────────────
    "experimental.chat.system.transform": async (input, output) => {
      try {
        // Tier 1: Always inject tags
        const tags = await loadTags(vaultPath)
        if (tags) {
          output.system.push(`
<vault-context>
## Vault topic tags

The tags below list every topic documented in your personal Obsidian vault.
Use them to decide how to answer before reaching for any tool:

- If the topic matches a tag → use vault_read or vault_search to retrieve the page
- If the topic does NOT match any tag → do not call vault tools; search the web or answer from general knowledge instead

Do not call vault_info() or vault_search() speculatively. The tags below are the complete topic map.

${tags.trim()}

## Vault learnings ritual

Save learnings via vault_write(kind="daily", title="${todayStr()}", content="## ${currentTimeStr()} — Summary\\n\\n..."):
- After completing a task or fixing a bug
- After finding root cause of a bug
- After a discovery during investigation
- After >5 min stuck on a problem
- After an architecture decision
- At end of session (/journal)

The HH:MM in the content template is filled in with the current local time
so daily notes get real timestamps, not hallucinated ones. If you write
multiple entries in one session, increment the time manually.

Format: caveman-concise. Cut filler words. vault_search first to avoid duplicates.
</vault-context>
          `.trim())
        }

        // Tier 2: Session context — first call only (or after compaction)
        if (!sessionContextInjected) {
          const context = await loadSessionContext(vaultPath)
          if (context) {
            output.system.push(`
<vault-session-context>
${context}
</vault-session-context>
            `.trim())
          }
          sessionContextInjected = true
        }
      } catch {
        // Never crash the session over vault unavailability
      }
    },

    // ─── Compaction: re-inject snapshot + reset session context ───────────
    //
    // INTENTIONALLY DUPLICATIVE: the compactor pushes a snapshot into
    // output.context (for the compaction summary prompt), AND we reset
    // sessionContextInjected to false so the next system.transform call
    // re-injects the full session context. The model sees BOTH:
    //   - snapshot: kept in the compaction summary
    //   - full context: pushed to the fresh system prompt after compaction
    // The cost is ~4K chars of duplication per compaction event — small,
    // and worth it for the model to have a complete "where am I" view
    // after context loss. See spec D2 + "What's still missing" notes.
    //
    // v2.1 also resets idleNudgeSent so the next idle event after
    // compaction can re-prompt (one nudge per session-segment).
    "experimental.session.compacting": async (input, output) => {
      try {
        const snapshot = await loadCompactionSnapshot(vaultPath)
        output.context.push(snapshot)

        // Reset — will re-inject full session context after compaction
        sessionContextInjected = false
        // Reset — next idle after compaction can re-prompt
        idleNudgeSent = false
      } catch {
        // Never crash the session over vault unavailability
      }
    },

    // ─── Session lifecycle events ─────────────────────────────────────────
    //
    // v2.1: session.idle auto-save. When the agent finishes a turn and
    // the session transitions to idle, re-prompt the model with a
    // journal nudge. The model decides whether anything is worth
    // saving — if so, it calls vault_write.
    //
    // Why re-prompt vs direct tool call: the model knows what's worth
    // saving (root causes, architecture decisions, debugging journeys).
    // The plugin doesn't. Bypassing the model means constructing a
    // save blindly, which is worse.
    //
    // Why fire-and-forget: the event hook handler is async, but
    // OpenCode's plugin runtime drops the return promise (per
    // opencode issue #16879). We kick off the call and accept the
    // window-close risk. Compaction + manual /journal cover the
    // "guarantee" cases.
    //
    // Why a flag: prevents recursion. After the re-prompt, the model
    // responds, the session goes idle again, the handler fires again.
    // The flag is set synchronously, so the second fire is a no-op.
    // Reset on compaction so the next segment can nudge again.
    event: async ({ event }) => {
      if (event.type !== "session.idle" || idleNudgeSent) return
      idleNudgeSent = true
      try {
        // v1 SDK shape: { path: { id }, body: { parts } }
        await client.session.prompt({
          path: { id: event.properties.sessionID },
          body: {
            parts: [
              { type: "text", text: buildIdleNudgePrompt(todayStr(), currentTimeStr()) },
            ],
          },
        })
      } catch {
        // Best-effort. Session is going idle; the call may not land
        // before the process tears down. Manual /journal covers the
        // guaranteed-save case.
      }
    },
  }
}

export default VaultContextPlugin
