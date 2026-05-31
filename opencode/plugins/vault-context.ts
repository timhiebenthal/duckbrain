/**
 * DuckBrain vault context plugin for OpenCode — v2
 *
 * Placement:  ~/.config/opencode/plugins/vault-context.ts  (global)
 *         or  .opencode/plugins/vault-context.ts            (project-local)
 *
 * Requires:   VAULT_PATH env var pointing to your Obsidian vault root
 *
 * Architecture: Tiered injection + guard + compaction preservation
 *   - Tags: always injected (small ~2K, routing signal)
 *   - Log + dailies: first call only (expensive, session context)
 *   - Guard: track vault-free calls, nudge via system prompt
 *   - Compaction: re-inject snapshot + journal nudge
 *
 * Proven constraints (from probe):
 *   ✅  Bun.file(path).text()     — works, use this for all file reads
 *   ❌  import("fs") / require     — blocked by sandbox
 *   ✅  process.env / Bun.env     — works
 *   ✅  output.system.push()      — mutations reach the LLM
 *   ✅  experimental.session.compacting — fires, output.context.push() works
 *   ✅  tool.execute.after         — fires after every tool call (for counting)
 */

import type { Plugin } from "@opencode-ai/plugin"

// ─── tunables ────────────────────────────────────────────────────────────────

const MAX_LOG_LINES      = 30   // tail of wiki/log.md
const GUARD_THRESHOLD    = 8    // tool calls before guard nudge fires
const VAULT_TOOL_NAMES   = [    // tools that count as "vault interaction"
  "vault_search", "vault_read", "vault_write", "vault_info", "vault_context",
]

// ─── helpers ─────────────────────────────────────────────────────────────────

async function safeRead(path: string): Promise<string | null> {
  try {
    return await Bun.file(path).text()
  } catch {
    return null
  }
}

function tail(text: string, lines: number): string {
  return text.split("\n").slice(-lines).join("\n")
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

function yesterdayStr(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

// ─── tiered context loaders ──────────────────────────────────────────────────

/**
 * Tier 1: Tags — always injected. Small (~2K), provides topic routing.
 */
async function loadTags(vaultPath: string): Promise<string | null> {
  return safeRead(`${vaultPath}/wiki/tags.md`)
}

/**
 * Tier 2: Session context — injected on first call + after compaction.
 * Log tail + today + yesterday daily notes.
 */
async function loadSessionContext(vaultPath: string): Promise<string> {
  const parts: string[] = []

  const log = await safeRead(`${vaultPath}/wiki/log.md`)
  if (log) {
    parts.push(`## Recent vault writes\n${tail(log, MAX_LOG_LINES)}`)
  }

  const today = await safeRead(`${vaultPath}/daily/${todayStr()}.md`)
  if (today) {
    parts.push(`## 📅 Today's daily note (${todayStr()})\n${today.trim()}`)
  }

  const yesterday = await safeRead(`${vaultPath}/daily/${yesterdayStr()}.md`)
  if (yesterday) {
    parts.push(`## 📅 Yesterday's daily note (${yesterdayStr()})\n${yesterday.trim()}`)
  }

  return parts.join("\n\n---\n\n")
}

/**
 * Compaction snapshot — compact version + journal nudge.
 */
async function loadCompactionSnapshot(vaultPath: string): Promise<string> {
  const log = await safeRead(`${vaultPath}/wiki/log.md`)
  const today = await safeRead(`${vaultPath}/daily/${todayStr()}.md`)

  const parts: string[] = [
    "The following vault context was active at compaction time and should be preserved:",
  ]
  if (log)   parts.push(`### Recent vault writes\n${tail(log, 15)}`)
  if (today) parts.push(`### Today's daily note (${todayStr()})\n${today.trim()}`)

  parts.push(`### ⚠️ Journal checkpoint
This session has been compacted. Before continuing, save any learnings:
vault_write(kind="daily", title="${todayStr()}", content="## HH:MM — What was done\\n\\n...")
Format: caveman-concise. Cut filler words.`)

  return parts.join("\n\n")
}

// ─── guard state ─────────────────────────────────────────────────────────────

let toolCallCount = 0
let lastVaultToolCall = 0

function isVaultTool(toolName: string): boolean {
  return VAULT_TOOL_NAMES.some(vt => toolName.toLowerCase().includes(vt))
}

// ─── plugin export ────────────────────────────────────────────────────────────

export const VaultContextPlugin: Plugin = async ({ client }) => {
  const vaultPath = process.env.VAULT_PATH
  if (!vaultPath) return {}

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

        // Guard: inject nudge if threshold exceeded
        const callsSinceVault = toolCallCount - lastVaultToolCall
        if (callsSinceVault >= GUARD_THRESHOLD) {
          output.system.push(`
<vault-guard>
⚠️ You've made ${callsSinceVault} tool calls without checking the vault.
If the current task relates to documented topics, consider vault_search or vault_read before proceeding.
</vault-guard>
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

    // ─── Guard: count tool calls, track vault interactions ────────────────
    "tool.execute.after": async (input, output) => {
      try {
        toolCallCount++
        const toolName = input.tool?.name || ""

        if (isVaultTool(toolName)) {
          lastVaultToolCall = toolCallCount
        }
      } catch {
        // Never crash the session over guard logic
      }
    },

    // ─── Compaction: re-inject snapshot + reset session context ───────────
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
