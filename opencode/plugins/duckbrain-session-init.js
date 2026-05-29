/**
 * DuckBrain Session Init Plugin
 *
 * Injects today's + yesterday's daily notes, the learnings ritual, vault
 * usage instructions, and journaling rule into the system prompt. Invisible
 * injection via `experimental.chat.system.transform`.
 *
 * Loads dailies synchronously on first model call — no event hooks, no race
 * conditions. Compaction hook preserves vault context.
 */

export const DuckBrainSessionInit = async (ctx) => {
  console.log("[DuckBrainSessionInit] Plugin loaded successfully");

  const injectedSessions = new Set();

  async function loadContext() {
    const vaultPath = process.env.VAULT_PATH;
    if (!vaultPath) return null;

    const now = new Date();
    const todayStr = now.toISOString().slice(0, 10);

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().slice(0, 10);

    const readDaily = async (dateStr) => {
      try {
        const file = Bun.file(`${vaultPath}/daily/${dateStr}.md`);
        const text = await file.text();
        return text.trim() || "(no daily note yet)";
      } catch {
        return "(no daily note yet)";
      }
    };

    const todayContent = await readDaily(todayStr);
    const yesterdayContent = await readDaily(yesterdayStr);

    return [
      "## Session context (auto-loaded from vault)",
      "",
      `### Today's daily: ${todayStr}`,
      todayContent,
      "",
      `### Yesterday's daily: ${yesterdayStr}`,
      yesterdayContent,
      "",
      "### Vault learnings ritual",
      "",
      "#### Triggers (save when you finish something, not after every edit)",
      "- AFTER completing a task or fixing a bug → vault_write summary to today's daily",
      "- AFTER finding root cause of a bug → vault_write root cause + fix",
      "- AFTER making a discovery during investigation → vault_write findings",
      "- AFTER >5 min stuck on a problem → vault_write progress/journey so far",
      "- AFTER an architecture decision → vault_write reasoning + trade-offs",
      "",
      "#### Session rituals",
      "- At session start: call vault_context(keywords=[...]) with prompt-extracted keywords",
      "- During session: after non-trivial task, vault_write progress to daily note (format: ## HH:MM — What was done)",
      '- End of session (or on "/journal"): vault_write session summary to daily note',
      "  Include: Progress, Learnings, Open questions",
      "",
      "#### How to save",
      "- vault_search first to avoid duplicates",
      "- Daily notes → session log, progress, debugging, one-off learnings",
      "- Wiki concepts → reusable knowledge worth permanent reference",
      "",
      "#### Daily note structure",
      "- Caveman-concise. Cut filler words, keep substance",
      "- Expand only when detail matters: debugging root cause, architecture trade-offs",
      "",
      "### Journaling rule (FOLLOW THIS)",
      "After EVERY response where you accomplished real work (not just answered a question),",
      "call vault_write(kind=\"daily\", title=\"YYYY-MM-DD\", content=\"## HH:MM — What was done\\n\\n...\").",
      "Do this at the START of your next response, before answering the user.",
      "Skip for trivial: small questions, single-line answers, reading files.",
      "",
      "### Vault usage",
      "FIRST: call vault_info() to learn what topics/tags the vault covers.",
      "THEN for each user query: if it matches vault topics → vault_context(keywords=[...]) or vault_search(...).",
      "If the query is about something unrelated (e.g. nuclear energy, cooking, sports) → skip vault entirely.",
      "Don't waste tool calls checking the vault for topics it doesn't cover.",
    ].join("\n");
  }

  return {
    // ── System prompt injection (loads dailies, injects everything once per session) ──
    "experimental.chat.system.transform": async (input, output) => {
      const sid = input.sessionID;
      if (!sid || injectedSessions.has(sid)) return;

      injectedSessions.add(sid);

      const contextBlock = await loadContext();
      if (!contextBlock) return;

      output.system = output.system || [];
      output.system.push(contextBlock);
    },

    // ── Compaction hook: preserve vault context ──
    "experimental.session.compacting": (input, output) => {
      output.context = output.context || [];
      output.context.push(`## Vault context preservation

If vault context was loaded this session (dailies, search results), include a brief summary here:
- Today's daily note highlights
- Any search results the agent referenced
- Key learnings or decisions documented

The goal: vault-loaded knowledge survives session compaction.`);
    },

    // ── Clean up on session deleted ──
    event: async ({ event }) => {
      if (event.type === "session.deleted") {
        const sessionID = event.properties?.info?.id;
        if (sessionID) injectedSessions.delete(sessionID);
      }
    },
  };
};
