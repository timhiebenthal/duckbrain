/**
 * DuckBrain vault context plugin for OpenCode — v2
 *
 * Placement:  ~/.config/opencode/plugins/vault-context.ts  (global)
 *         or  .opencode/plugins/vault-context.ts            (project-local)
 *
 * Requires:   VAULT_PATH env var pointing to your Obsidian vault root
 *
 * Architecture: Tiered injection + compaction preservation
 *   - Tags: always injected (small ~2K, routing signal)
 *   - Log + dailies: first call only (expensive, session context)
 *   - Compaction: re-inject snapshot + journal nudge
 *
 * Proven constraints (from probe):
 *   ✅  Bun.file(path).text()     — works, use this for all file reads
 *   ❌  import("fs") / require     — blocked by sandbox
 *   ✅  process.env / Bun.env     — works
 *   ✅  output.system.push()      — mutations reach the LLM
 *   ✅  experimental.session.compacting — fires, output.context.push() works
 */

import type { Plugin } from "@opencode-ai/plugin"
import {
  loadTags,
  loadSessionContext,
  loadCompactionSnapshot,
  todayStr,
} from "./vault-context-helpers"

// ─── plugin export ────────────────────────────────────────────────────────────

export const VaultContextPlugin: Plugin = async ({ client }) => {
  const vaultPath = process.env.VAULT_PATH
  if (!vaultPath) return {}

  // Module-scoped flag. Safe only if OpenCode spawns one plugin
  // process per session — verified via probe 2026-05-31 (see
  // specs/2026-05-31-vault-interaction-robustness/spec.md). If
  // OpenCode ever reuses a process across sessions, this leaks
  // state — switch to Map<sessionID, bool> using the sessionID
  // from system.transform input.
  let sessionContextInjected = false

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

Save learnings via vault_write(kind="daily", title="${todayStr()}", content="## HH:MM — Summary\\n\\n..."):
- After completing a task or fixing a bug
- After finding root cause of a bug
- After a discovery during investigation
- After >5 min stuck on a problem
- After an architecture decision
- At end of session (/journal)

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
    "experimental.session.compacting": async (input, output) => {
      try {
        const snapshot = await loadCompactionSnapshot(vaultPath)
        output.context.push(snapshot)

        // Reset — will re-inject full session context after compaction
        sessionContextInjected = false
      } catch {
        // Never crash the session over vault unavailability
      }
    },
  }
}

export default VaultContextPlugin
