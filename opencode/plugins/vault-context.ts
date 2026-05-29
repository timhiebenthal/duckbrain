/**
 * DuckBrain vault context plugin for OpenCode
 *
 * Placement:  ~/.config/opencode/plugins/vault-context.ts  (global)
 *         or  .opencode/plugins/vault-context.ts            (project-local)
 *
 * Requires:   VAULT_PATH env var pointing to your Obsidian vault root
 *
 * Proven constraints (from probe):
 *   ✅  Bun.file(path).text()     — works, use this for all file reads
 *   ❌  import("fs") / require     — blocked by sandbox
 *   ✅  process.env / Bun.env     — works
 *   ✅  output.system.push()      — mutations reach the LLM
 *   ✅  experimental.session.compacting — fires, output.context.push() works
 */

import type { Plugin } from "@opencode-ai/plugin"

// ─── tunables ────────────────────────────────────────────────────────────────

const MAX_DAILY_NOTES   = 3    // how many recent daily notes to include in full
const MAX_LOG_LINES     = 40   // tail of wiki/log.md to show

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
  return new Date().toISOString().slice(0, 10) // "YYYY-MM-DD"
}

function recentDates(n: number): string[] {
  const dates: string[] = []
  const d = new Date()
  for (let i = 0; i < n; i++) {
    dates.push(d.toISOString().slice(0, 10))
    d.setDate(d.getDate() - 1)
  }
  return dates
}

// ─── core context loader ──────────────────────────────────────────────────────

async function loadVaultContext(vaultPath: string): Promise<string> {
  const parts: string[] = []

  // 0. Vault tags — concise topic list (updated by DuckBrain on every write)
  const tags = await safeRead(`${vaultPath}/wiki/tags.md`)
  if (tags) {
    parts.push(`## Vault topic tags\n${tags.trim()}`)
  }

  // 1. Tail of wiki/log.md — most recent write activity
  const log = await safeRead(`${vaultPath}/wiki/log.md`)
  if (log) {
    parts.push(`## Recent vault activity (last ${MAX_LOG_LINES} log lines)\n${tail(log, MAX_LOG_LINES)}`)
  }

  // 3. Recent daily notes — today + yesterday + day before
  const dailyParts: string[] = []
  for (const date of recentDates(MAX_DAILY_NOTES)) {
    const note = await safeRead(`${vaultPath}/daily/${date}.md`)
    if (note) {
      dailyParts.push(`### ${date}\n${note.trim()}`)
    }
  }
  if (dailyParts.length > 0) {
    parts.push(`## Recent daily notes\n${dailyParts.join("\n\n")}`)
  }

  return parts.join("\n\n---\n\n")
}

// ─── compaction snapshot ──────────────────────────────────────────────────────
// Keeps vault context alive across session compactions.
// Without this, compaction discards the injected system prompt content
// and the model loses vault awareness mid-session.

async function loadCompactionSnapshot(vaultPath: string): Promise<string> {
  const log = await safeRead(`${vaultPath}/wiki/log.md`)
  const today = await safeRead(`${vaultPath}/daily/${todayStr()}.md`)

  const parts: string[] = [
    "The following vault context was active at compaction time and should be preserved:",
  ]
  if (log)   parts.push(`### Last vault writes\n${tail(log, 20)}`)
  if (today) parts.push(`### Today's daily note (${todayStr()})\n${today.trim()}`)

  return parts.join("\n\n")
}

// ─── plugin export ────────────────────────────────────────────────────────────

export const VaultContextPlugin: Plugin = async ({ client }) => {
  const vaultPath = process.env.VAULT_PATH

  if (!vaultPath) {
    // Fail loudly so it's obvious in stderr — not silently
    process.stderr.write("[vault-context] VAULT_PATH not set — plugin inactive\n")
    return {}
  }

  process.stderr.write(`[vault-context] loaded, vault: ${vaultPath}\n`)

  return {

    /**
     * Fires before every LLM call.
     * Injects the full vault topic index into the system prompt.
     *
     * Primary purpose: acts as a routing filter.
     * The model can see upfront which topics are documented, so it:
     *   - calls vault_read/vault_search only for topics that ARE in the index
     *   - falls through to web search or general knowledge for everything else
     *   - never calls vault_info() speculatively
     */
    "experimental.chat.system.transform": async (input, output) => {
      try {
        const context = await loadVaultContext(vaultPath)

        if (!context) {
          process.stderr.write("[vault-context] system.transform: nothing loaded\n")
          return
        }

        output.system.push(`
<vault-context>
IMPORTANT: After analyzing code, debugging, running tests, or making architecture decisions — call vault_write(kind="daily", title="${todayStr()}", content="## HH:MM — What was done\\n\\n...") to save learnings to today's daily note. Do this BEFORE continuing your response.

## Personal knowledge vault — topic tags

The tags below list every topic documented in your personal Obsidian vault.
Use them to decide how to answer before reaching for any tool:

- If the topic matches a tag → use vault_read or vault_search to retrieve the page
- If the topic does NOT match any tag → do not call vault tools; search the web or answer from general knowledge instead

Do not call vault_info() or vault_search() speculatively. The tags below are the complete topic map.

${context}

## Vault learnings ritual

Save learnings via vault_write(kind="daily", title="YYYY-MM-DD", content="## HH:MM — Summary\\n\\n..."):
- After completing a task or fixing a bug
- After finding root cause of a bug
- After a discovery during investigation
- After >5 min stuck on a problem
- After an architecture decision
- At end of session (/journal)

Format: caveman-concise. Cut filler words. vault_search first to avoid duplicates.
</vault-context>
        `.trim())

        process.stderr.write(
          `[vault-context] system.transform: injected ${context.length} chars\n`
        )
      } catch (err) {
        // Never crash the session over vault unavailability
        process.stderr.write(`[vault-context] system.transform error: ${err}\n`)
      }
    },

    /**
     * Fires when OpenCode compacts the session context.
     * Re-injects a snapshot of current vault state into the continuation prompt
     * so the model doesn't lose vault awareness after compaction.
     */
    "experimental.session.compacting": async (input, output) => {
      try {
        const snapshot = await loadCompactionSnapshot(vaultPath)
        output.context.push(snapshot)

        process.stderr.write(
          `[vault-context] compacting: preserved ${snapshot.length} chars\n`
        )
      } catch (err) {
        process.stderr.write(`[vault-context] compacting error: ${err}\n`)
      }
    },

  }
}

export default VaultContextPlugin
