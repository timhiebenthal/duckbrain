/**
 * DuckBrain Session Init Plugin
 *
 * Injects today's + yesterday's daily notes and the learnings ritual into
 * the system prompt (invisible to user). Adds guard hook (nudge after N
 * vault-free tool calls) and compaction hook (preserve vault context).
 *
 * Injection is via `experimental.chat.system.transform` — the model sees
 * the context, the user doesn't. `session.created` is observational only;
 * it reads + caches the daily notes for the transform hook to inject.
 */

export const DuckBrainSessionInit = async ({ client }) => {
  const sessions = {};
  const injectedSessions = new Set();

  function getSession(id) {
    if (!sessions[id]) {
      sessions[id] = { toolCount: 0, lastVaultSearch: 0, nudgeFiredForGap: 0 };
    }
    return sessions[id];
  }

  function buildContextBlock(todayStr, yesterdayStr, todayContent, yesterdayContent) {
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
    ].join("\n");
  }

  return {
    // ── System prompt injection (invisible context loading) ──
    "experimental.chat.system.transform": (input, output) => {
      const sid = input.sessionID;
      if (!sid) return;
      if (injectedSessions.has(sid)) return;

      const session = sessions[sid];
      if (!session?.contextBlock) return; // not yet loaded

      injectedSessions.add(sid);
      output.system = output.system || [];
      output.system.push(session.contextBlock);
    },

    // ── Guard hook: nudge after N vault-free tool calls ──
    "tool.execute.after": (input, output) => {
      const session = getSession(input.sessionID);
      session.toolCount++;

      if (input.tool === "vault_search" || input.tool === "vault_context") {
        session.lastVaultSearch = session.toolCount;
        return;
      }

        const threshold = 15;
      const gap = session.toolCount - session.lastVaultSearch;

      if (gap >= threshold && gap > session.nudgeFiredForGap) {
        session.nudgeFiredForGap = gap;
        const nudge = `\n\n---\n💡 Haven't searched the vault in ${gap} tool calls. Consider vault_search() or vault_context() for relevant context.`;
        output.output = (output.output || "") + nudge;
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

    // ── Session lifecycle events ──
    event: async ({ event }) => {
      if (event.type === "session.deleted") {
        const sessionID = event.properties?.info?.id;
        if (sessionID) {
          delete sessions[sessionID];
          injectedSessions.delete(sessionID);
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

        // ── Scan vault for available tags (model uses this to decide if vault is relevant) ──
        let vaultTagsBlock = "";
        try {
          const vaultFiles = new Bun.Glob("wiki/**/*.md");
          const tagSet = new Set();
          for await (const filepath of vaultFiles.scan({ cwd: vaultPath, absolute: true })) {
            try {
              const text = await Bun.file(filepath).text();
              for (const line of text.split("\n")) {
                const m = line.match(/^tags:\s*\[(.+)\]$/);
                if (m) {
                  for (const tag of m[1].split(",")) {
                    const cleaned = tag.trim().replace(/^"+|"+$/g, "").replace(/^'+|'+$/g, "");
                    if (cleaned) tagSet.add(cleaned);
                  }
                }
              }
            } catch {}
          }
          if (tagSet.size > 0) {
            vaultTagsBlock = `\n### Vault overview\nAvailable tags (${tagSet.size}): ${[...tagSet].sort().join(", ")}\n\nTopics covered by the vault — use this to decide if vault_context() or vault_search() is worth calling.`;
          }
        } catch {
          // Silent — vault scanning is a nice-to-have, not critical
        }

        const contextBlock = buildContextBlock(todayStr, yesterdayStr, todayContent, yesterdayContent) + vaultTagsBlock;

        // Cache context block for system.transform to inject (no client.session.prompt — that creates visible UI bloat)
        sessions[sessionID] = {
          ...getSession(sessionID),
          contextBlock,
        };
      } catch (err) {
        console.error("[DuckBrainSessionInit] Error loading session context:", err);
      }
    },
  };
};
