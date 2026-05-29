/**
 * DuckBrain Session Init Plugin
 *
 * Injects today's + yesterday's daily notes, learnings ritual, vault tags
 * overview, and journaling rule into the system prompt. Tags are scanned
 * from wiki YAML frontmatter via node:fs — model knows vault topics without
 * calling vault_info().
 */

export const DuckBrainSessionInit = async (ctx) => {
  console.log("[DuckBrainSessionInit] Plugin loaded successfully");

  const injectedSessions = new Set();
  const sessions = {};

  async function loadContext() {
    const vaultPath = process.env.VAULT_PATH;
    if (!vaultPath) return null;

    const { readdirSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");

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

    // ── Scan wiki directories for tags (model uses this to decide vault relevance) ──
    let vaultTagsBlock = "";
    try {
      const tagSet = new Set();
      const wikiDirs = ["entities", "concepts", "sources", "synthesis"];
      for (const dir of wikiDirs) {
        const dirPath = join(vaultPath, "wiki", dir);
        let files;
        try { files = readdirSync(dirPath); } catch { continue; }
        for (const file of files) {
          if (!file.endsWith(".md")) continue;
          try {
            const text = readFileSync(join(dirPath, file), "utf-8");
            for (const line of text.split("\n")) {
              const m = line.match(/^tags:\s*\[(.+)\]$/);
              if (m) {
                for (const tag of m[1].split(",")) {
                  const cleaned = tag.trim().replace(/^["']+|["']+$/g, "");
                  if (cleaned) tagSet.add(cleaned);
                }
              }
            }
          } catch {}
        }
      }
      if (tagSet.size > 0) {
        vaultTagsBlock = `\n### Vault topic coverage (searchable, not pre-loaded)\nThe vault wiki covers these topics: ${[...tagSet].sort().join(", ")}\n\nIf the user's question relates to any of these → vault_context() or vault_search().\nIf unrelated (e.g. cooking, cars, sports) → skip the vault entirely.`;
      }
    } catch {
      vaultTagsBlock = "\n### Vault topics\nTags scan unavailable. Call vault_info() to discover topics.";
    }

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
      "Save learnings via vault_write(kind=\"daily\", title=\"YYYY-MM-DD\", content=\"## HH:MM — Summary\\n\\n...\"):",
      "- After completing a task or fixing a bug",
      "- After finding root cause of a bug",
      "- After a discovery during investigation",
      "- After >5 min stuck on a problem",
      "- After an architecture decision",
      "- At end of session (/journal)",
      "Format: caveman-concise. Cut filler words. vault_search first to avoid duplicates.",
      "",
      "### Journaling rule",
      "After EVERY non-trivial response, BEFORE your next sentence: vault_write(kind=\"daily\", title=\"YYYY-MM-DD\", content=\"## HH:MM — What was done\\n\\n...\"). Skip trivial Q&A only.",
      "",
      vaultTagsBlock,
    ].join("\n");
  }

  return {
    // ── System prompt injection (context once, journaling nudge on idle) ──
    "experimental.chat.system.transform": async (input, output) => {
      const sid = input.sessionID;
      if (!sid) return;

      output.system = output.system || [];

      // One-time context injection
      if (!injectedSessions.has(sid)) {
        injectedSessions.add(sid);
        const contextBlock = await loadContext();
        if (contextBlock) output.system.push(contextBlock);
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
