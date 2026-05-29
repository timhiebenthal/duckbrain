/**
 * DuckBrain Session Init Plugin
 *
 * Injects today's + yesterday's daily notes, learnings ritual, vault
 * usage instruction, and journaling rule into the system prompt.
 */

export const DuckBrainSessionInit = async (ctx) => {
  console.log("[DuckBrainSessionInit] Plugin loaded successfully");

  const injectedSessions = new Set();
  const sessions = {};

  async function loadContext() {
    const vaultPath = process.env.VAULT_PATH;
    if (!vaultPath) {
      process.stderr.write("[duckbrain] loadContext: VAULT_PATH not set\n");
      return null;
    }
    process.stderr.write(`[duckbrain] loadContext: VAULT_PATH=${vaultPath}\n`);

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
    process.stderr.write(`[duckbrain] loadContext: dailies loaded (${todayContent.length}+${yesterdayContent.length} chars)\n`);

    // ── Vault usage (sandbox blocks all filesystem APIs except Bun.file) ──
    const vaultOverview = "\n### Vault usage\nCall vault_info() to learn vault topics, then check relevance before searching.";

    return [
      "IMPORTANT: After analyzing code, debugging, running tests, or making architecture decisions — call vault_write(kind=\"daily\", title=\"" + todayStr + "\", content=\"## HH:MM — What was done\\n\\n...\") to save learnings to today's daily note. Do this BEFORE continuing your response.",
      "",
      "## Session context (auto-loaded from vault)",
      "",
      `### Today's daily: ${todayStr}`,
      todayContent,
      "",
      `### Yesterday's daily: ${yesterdayStr}`,
      yesterdayContent,
      "",
      "### Vault learnings ritual",
      "Save learnings via vault_write(kind=\"daily\", title=\"YYYY-MM-DD\", content=\"## HH:MM — Summary\\n\\n...\"):",
      "- After completing a task or fixing a bug",
      "- After finding root cause of a bug",
      "- After a discovery during investigation",
      "- After >5 min stuck on a problem",
      "- After an architecture decision",
      "- At end of session (/journal)",
      "Format: caveman-concise. Cut filler words. vault_search first to avoid duplicates.",
      "",
      vaultOverview,
    ].join("\n");
  }

  return {
    // ── System prompt injection (context once, journaling nudge on idle) ──
    "experimental.chat.system.transform": async (input, output) => {
      const sid = input.sessionID;
      if (!sid) {
        process.stderr.write("[duckbrain] system.transform: no sessionID, skipping\n");
        return;
      }

      output.system = output.system || [];

      if (!injectedSessions.has(sid)) {
        process.stderr.write(`[duckbrain] system.transform: first call for ${sid}, loading context...\n`);
        injectedSessions.add(sid);
        const contextBlock = await loadContext();
        if (contextBlock) {
          output.system.push(contextBlock);
          process.stderr.write(`[duckbrain] system.transform: context injected (${contextBlock.length} chars)\n`);
        } else {
          process.stderr.write("[duckbrain] system.transform: loadContext returned null, nothing injected\n");
        }
      } else {
        process.stderr.write(`[duckbrain] system.transform: already injected for ${sid}\n`);
      }

      // Journaling nudge after session.idle
      const session = sessions[sid];
      if (session?.shouldJournal) {
        session.shouldJournal = false;
        output.system.push(
          "💡 The previous exchange included non-trivial work. " +
          "If not yet journaled: vault_write(kind=\"daily\", title=\"" +
          new Date().toISOString().slice(0, 10) + "\", " +
          "content=\"## HH:MM — What was done\\n\\n...\")"
        );
      }
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

    // ── Session lifecycle ──
    event: async ({ event }) => {
      if (event.type === "session.deleted") {
        const sessionID = event.properties?.info?.id;
        if (sessionID) {
          injectedSessions.delete(sessionID);
          delete sessions[sessionID];
        }
      }

      // Flag journaling after session goes idle (user stopped typing)
      if (event.type === "session.idle") {
        const sessionID = event.properties?.info?.id;
        if (sessionID) {
          sessions[sessionID] = { shouldJournal: true };
        }
      }
    },
  };
};
