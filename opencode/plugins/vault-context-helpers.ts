/**
 * Pure helper functions for the DuckBrain vault context plugin.
 *
 * Kept separate from the plugin entry point for testability — every
 * function here is deterministic and can be unit-tested without
 * loading the OpenCode plugin runtime.
 *
 * Why split: AGENTS.md mandates TDD. The plugin entry point depends
 * on the @opencode-ai/plugin runtime, which is hard to test in
 * isolation. These helpers don't.
 */

export const MAX_LOG_LINES = 30

/**
 * Read a file's text. Returns null on any error (missing file,
 * permission denied, etc.) — never throws. Plugin uses this for
 * graceful degradation when vault is incomplete.
 */
export async function safeRead(path: string): Promise<string | null> {
  try {
    return await Bun.file(path).text()
  } catch {
    return null
  }
}

/**
 * Return the last N lines of a multi-line string. Preserves newlines
 * so the output can be embedded verbatim in markdown.
 *
 * Edge case: `slice(-0)` in JavaScript is equivalent to `slice(0)`,
 * which returns the full array. Explicitly handle lines <= 0 to
 * return empty string as the contract implies.
 */
export function tail(text: string, lines: number): string {
  if (lines <= 0) return ""
  return text.split("\n").slice(-lines).join("\n")
}

/**
 * Local date in YYYY-MM-DD format.
 *
 * BUGFIX: previously used `toISOString().slice(0, 10)` which returns
 * UTC date. Users in non-UTC timezones (e.g. America/Los_Angeles)
 * saw the wrong "today" until late afternoon local time — daily
 * note injection would miss the just-rolled-over file or show
 * yesterday as today.
 *
 * Fix: `toLocaleDateString("sv-SE")` returns YYYY-MM-DD (Swedish
 * locale uses ISO 8601 date format) in the local timezone. Honors
 * the TZ env var.
 */
export function todayStr(): string {
  return new Date().toLocaleDateString("sv-SE")
}

/**
 * Local date for yesterday in YYYY-MM-DD format.
 *
 * `setDate(getDate() - 1)` correctly handles month/year boundaries
 * (Date arithmetic is timezone-aware). Result is formatted in local
 * time.
 */
export function yesterdayStr(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toLocaleDateString("sv-SE")
}

/**
 * Tier 1: Tags — always injected. Small (~2K), provides topic routing.
 */
export async function loadTags(vaultPath: string): Promise<string | null> {
  return safeRead(`${vaultPath}/wiki/tags.md`)
}

/**
 * Tier 2: Session context — injected on first call + after compaction.
 * Log tail + today + yesterday daily notes.
 */
export async function loadSessionContext(vaultPath: string): Promise<string> {
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
 *
 * Why 15 lines and not 30 (MAX_LOG_LINES): the compactor is going
 * to summarize the session anyway, so the snapshot only needs to
 * orient the model ("here's what was recent") not provide full
 * context. Smaller is better at this point.
 */
export async function loadCompactionSnapshot(vaultPath: string): Promise<string> {
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

/**
 * Idle re-prompt message — sent to the model on `session.idle` so it
 * has a chance to journal learnings before the session ends.
 *
 * Why a separate helper: pure function, easy to unit-test. The hook
 * handler in vault-context.ts just calls this and sends the result
 * via client.session.prompt().
 *
 * Design choices:
 * - "If you have new learnings" — gives the model a skip condition
 *   so an empty session doesn't trigger a no-op write.
 * - "No response needed" — tells the model that silence is OK if
 *   there's nothing to save. Without this the model feels compelled
 *   to respond, wasting tokens.
 * - Same `vault_write` schema as the ritual block in
 *   system.transform — single source of truth for the call shape.
 *
 * Known limitation: the prompt appears as a user message in
 * conversation history. The OpenCode SDK's `synthetic: true` flag
 * on TextPartInput might suppress this — worth investigating for
 * v0.4.1. For now, accept the visible nudge in the "agent finished
 * naturally" case (user isn't actively watching).
 */
export function buildIdleNudgePrompt(today: string): string {
  return `Session is idle. If you have new learnings, journal them via vault_write(kind="daily", title="${today}", content="## HH:MM — Topic\\n\\nDetails"). Follow the format in the vault learnings ritual. If nothing new since your last entry, no response needed.`
}
