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
        vaultTagsBlock = `\n### Vault topics (${tagSet.size} tags)\n${[...tagSet].sort().join(", ")}\n\nUse vault_context() or vault_search() for topics above. Skip vault for unrelated queries.`;
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
      vaultTagsBlock,
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
