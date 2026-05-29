/**
 * DuckBrain Session Init Plugin
 *
 * Hooks `session.created` to inject today's + yesterday's daily notes
 * and the learnings ritual into the session context before the AI
 * processes any prompt.
 */

export const DuckBrainSessionInit = async ({ client }) => {
  return {
    event: async ({ event }) => {
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
          "#### Triggers (save IMMEDIATELY)",
          "- AFTER editing code → vault_write what changed + why to today's daily",
          "- AFTER debugging → vault_write root cause + fix to today's daily",
          "- AFTER investigating → vault_write discoveries",
          "- AFTER >5 min on any problem → vault_write journey",
          "- AFTER architecture decisions → vault_write reasoning",
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
      } catch (err) {
        // Plugin must never crash the session
        console.error("[DuckBrainSessionInit] Error injecting session context:", err);
      }
    },
  };
};
