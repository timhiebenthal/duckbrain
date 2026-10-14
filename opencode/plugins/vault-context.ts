/**
 * DuckBrain vault context plugin for OpenCode — supports OpenCode 1 and 2.
 *
 * OpenCode 2 replaced the plugin API. V2 plugins default-export
 * `Plugin.define({ id, setup })` and register hooks on the context.
 * V1 plugins export a function that returns a hook map; since OpenCode
 * 1.18.29 V1 also accepts an object with a `server` entrypoint.
 *
 * Both implementations live in one default export:
 *   - V2 reads `id` + `setup`
 *   - V1 (>= 1.18.29) reads `server`
 *
 * They share the pure helpers (vault-context-helpers.ts), so the injected
 * text cannot drift between runtimes. See specs/2026-10-14-opencode-v2-plugin/.
 *
 * Placement:  ~/.config/opencode/plugins/vault-context.ts  (global)
 *         or  .opencode/plugins/vault-context.ts            (project-local)
 *
 * Requires:   VAULT_PATH env var pointing to your Obsidian vault root
 *             @opencode/plugin  (V2 runtime types; V2 provides it at runtime)
 *             @opencode-ai/plugin (V1 types)
 *
 * Architecture (identical in both runtimes):
 *   - Tags + identity: always injected (small, routing signal)
 *   - Log + dailies: first call per session (expensive, session context)
 *   - Compaction: re-inject snapshot + journal nudge
 *   - session.idle: re-prompt the model to journal before the session ends
 *
 * Runtime differences that matter:
 *   - V2 injects content parts: event.system.push({ type: "text", text })
 *     V1 injects raw strings:    output.system.push(text)
 *   - A V2 plugin instance serves every session in its location, so the
 *     per-session flags are Sets keyed by sessionID. V1 spawns one plugin
 *     process per session (verified 2026-05-31), so plain booleans are safe.
 *   - V2's `event` hook is ctx.event.subscribe(...), aborted from cleanup.
 *     V1's `event` hook is a returned callback.
 *   - The idle nudge is ctx.session.synthetic(...) in V2 (not a user turn)
 *     and client.session.prompt(...) in V1.
 */

import { Plugin } from "@opencode/plugin"
import type { Hooks, PluginInput } from "@opencode-ai/plugin"

import {
  buildIdentityBlock,
  buildIdleNudgePrompt,
  buildVaultContextBlock,
  loadCompactionSnapshot,
  loadIdentity,
  loadSessionContext,
  loadTags,
  todayStr,
} from "./vault-context-helpers"

// ─── OpenCode 2 ───────────────────────────────────────────────────────────────

/**
 * V2 entrypoint. Exported (and referenced by `Plugin.define`) so tests can
 * drive it with a fake context — the hook wiring is otherwise unobservable.
 */
export async function setup(
  ctx: Plugin.Context,
): Promise<(() => void) | void> {
  const vaultPath = process.env.VAULT_PATH
  if (!vaultPath) return

  // Per-session state. A V2 plugin instance serves every session in its
  // location, so module-scoped booleans would leak across concurrent
  // sessions. Keyed by sessionID instead.
  const sessionContextInjected = new Set<string>()
  const idleNudgeSent = new Set<string>()

  // ─── Tiered system prompt injection ────────────────────────────────────
  await ctx.session.hook("context", async (event) => {
    const { sessionID } = event
    try {
      // Tier 1: Always inject tags + learnings ritual
      const tags = await loadTags(vaultPath)
      if (tags) {
        event.system.push({
          type: "text",
          text: buildVaultContextBlock(tags, todayStr()),
        })
      }

      // Identity — always injected (small, like tags). imprint.md at
      // vault root captures durable user identity.
      const identity = await loadIdentity(vaultPath)
      if (identity) {
        event.system.push({
          type: "text",
          text: buildIdentityBlock(identity),
        })
      }

      // Tier 2: Session context — first call per session only (or after
      // compaction).
      if (!sessionContextInjected.has(sessionID)) {
        const context = await loadSessionContext(vaultPath)
        if (context) {
          event.system.push({
            type: "text",
            text: `
<vault-session-context>
${context}
</vault-session-context>
            `.trim(),
          })
        }
        sessionContextInjected.add(sessionID)
      }
    } catch {
      // Never crash the session over vault unavailability
    }
  })

  // ─── Compaction: re-inject snapshot + reset session context ─────────────
  //
  // INTENTIONALLY DUPLICATIVE: the snapshot is kept in the compaction
  // summary, AND this session is cleared from sessionContextInjected so the
  // next context hook re-injects the full session context. The model sees
  // both — cheap, and gives a complete "where am I" view after context loss.
  //
  // Also clears idleNudgeSent so the next idle event after compaction can
  // re-prompt (one nudge per session-segment).
  await ctx.session.hook("compaction", async (event) => {
    const { sessionID } = event
    try {
      const snapshot = await loadCompactionSnapshot(vaultPath)
      event.system.push({ type: "text", text: snapshot })

      sessionContextInjected.delete(sessionID)
      idleNudgeSent.delete(sessionID)
    } catch {
      // Never crash the session over vault unavailability
    }
  })

  // ─── Session lifecycle events ───────────────────────────────────────────
  //
  // session.idle auto-save. When the agent finishes a turn and the session
  // transitions to idle, nudge the model to journal. The model decides
  // whether anything is worth saving.
  //
  // synthetic() (not prompt()): a synthetic message is not attributed to the
  // user, so the nudge does not appear in history as if the user typed it.
  //
  // The `idleNudgeSent` set prevents recursion: after the nudge the model may
  // respond, the session goes idle again, and the handler fires again. The set
  // is mutated synchronously, so the second fire is a no-op.
  const controller = new AbortController()

  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({
        signal: controller.signal,
      })) {
        if (event.type !== "session.idle") continue
        const { sessionID } = event.data
        if (idleNudgeSent.has(sessionID)) continue
        idleNudgeSent.add(sessionID)
        try {
          await ctx.session.synthetic({
            sessionID,
            text: buildIdleNudgePrompt(todayStr()),
          })
        } catch {
          // Best-effort. Session is going idle; the call may not land
          // before teardown. Manual /journal covers the guaranteed case.
        }
      }
    } catch {
      // Subscription aborted during unload
    }
  })()

  return () => controller.abort()
}

const plugin = Plugin.define({
  id: "duckbrain.vault-context",
  setup,
})

// ─── OpenCode 1 (needs >= 1.18.29 for object entrypoints) ──────────────────────

async function server(input: PluginInput): Promise<Hooks> {
  const vaultPath = process.env.VAULT_PATH
  if (!vaultPath) return {}

  // Module-scoped flags. Safe because V1 spawns one plugin process per
  // session (verified via probe 2026-05-31). If V1 ever reuses a process
  // across sessions, switch to Map<sessionID, bool>.
  let sessionContextInjected = false
  let idleNudgeSent = false

  return {
    // ─── Tiered system prompt injection ──────────────────────────────────
    "experimental.chat.system.transform": async (_input, output) => {
      try {
        // Tier 1: Always inject tags + learnings ritual
        const tags = await loadTags(vaultPath)
        if (tags) {
          output.system.push(buildVaultContextBlock(tags, todayStr()))
        }

        // Identity — always injected (small, like tags).
        const identity = await loadIdentity(vaultPath)
        if (identity) {
          output.system.push(buildIdentityBlock(identity))
        }

        // Tier 2: Session context — first call only (or after compaction)
        if (!sessionContextInjected) {
          const context = await loadSessionContext(vaultPath)
          if (context) {
            output.system.push(
              `
<vault-session-context>
${context}
</vault-session-context>
              `.trim(),
            )
          }
          sessionContextInjected = true
        }
      } catch {
        // Never crash the session over vault unavailability
      }
    },

    // ─── Compaction: re-inject snapshot + reset session context ───────────
    "experimental.session.compacting": async (_input, output) => {
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
    event: async ({ event }) => {
      if (event.type !== "session.idle" || idleNudgeSent) return
      idleNudgeSent = true
      try {
        // v1 SDK shape: { path: { id }, body: { parts } }
        await input.client.session.prompt({
          path: { id: event.properties.sessionID },
          body: {
            parts: [{ type: "text", text: buildIdleNudgePrompt(todayStr()) }],
          },
        })
      } catch {
        // Best-effort. Manual /journal covers the guaranteed-save case.
      }
    },
  }
}

// One default export serves both runtimes: V2 reads `id` + `setup`,
// V1 reads `server`. Extra keys are ignored by the other runtime.
export default {
  ...plugin,
  server,
}
