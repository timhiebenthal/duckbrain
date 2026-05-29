/**
 * DuckBrain Session Init Plugin
 *
 * Hooks `session.created` to inject today's + yesterday's daily notes
 * and the learnings ritual into the session context before the AI
 * processes any prompt.
 */

export const DuckBrainSessionInit = async ({ client }) => {
  const sessions = {};

  function getSession(id) {
    if (!sessions[id]) {
      sessions[id] = { toolCount: 0, lastVaultSearch: 0, nudgeFiredForGap: 0 };
    }
    return sessions[id];
  }

  return {
    hooks: {
      "tool.execute.after": (input, output) => {
        const session = getSession(input.sessionID);
        session.toolCount++;

        // Track vault tool usage
        if (input.tool === "vault_search" || input.tool === "vault_context") {
          session.lastVaultSearch = session.toolCount;
          return; // don't nudge on vault tools themselves
        }

        const threshold = 8;
        const gap = session.toolCount - session.lastVaultSearch;

        if (gap >= threshold && gap > session.nudgeFiredForGap) {
          session.nudgeFiredForGap = gap;
          const nudge = `\n\n---\n💡 Haven't searched the vault in ${gap} tool calls. Consider vault_search() or vault_context() for relevant context.`;
          output.output = (output.output || "") + nudge;
        }
      },
      "experimental.session.compacting": (input, output) => {
        // Find the most recent vault context from any tracker
        // For now, push a preservation reminder
        output.context = output.context || [];
        output.context.push(`## Vault context preservation

If vault context was loaded this session (dailies, search results), include a brief summary here:
- Today's daily note highlights
- Any search results the agent referenced
- Key learnings or decisions documented

The goal: vault-loaded knowledge survives session compaction.`);
      },
    },
    event: async ({ event }) => {
      if (event.type === "session.deleted") {
        const sessionID = event.properties?.info?.id;
        if (sessionID) {
          delete sessions[sessionID];
        }
        return;
      }

      if (event.type !== "session.created") return;

      try {
        const sessionID = event.properties?.info?.id;
        if (!sessionID) return;

        const vaultPath = process.env.VAULT_PATH;
        if (!vaultPath) return;

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

        const contextBlock = [
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
        ].join("\n");

        await client.session.prompt({
          path: { id: sessionID },
          body: {
            noReply: true,
            parts: [{ type: "text", text: contextBlock }],
          },
        });

        sessions[sessionID] = { toolCount: 0, lastVaultSearch: 0, nudgeFiredForGap: 0, dailyContext: true };
      } catch (err) {
        // Plugin must never crash the session
        console.error("[DuckBrainSessionInit] Error injecting session context:", err);
      }
    },
  };
};
