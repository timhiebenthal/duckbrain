---
name: duckbrain-journal
description: Journal this Codex session to the DuckBrain vault, including progress, learnings, decisions, and open work.
---

# Journal the session

1. Review the conversation and any relevant changes. Incorporate the user's additional context. Identify completed work, decisions, root causes, discoveries, and unfinished work; do not invent details.
2. Determine today's local date. Use DuckBrain `vault_context` with `include_dailies=true` and `include_search=false` to read the daily notes. Compare today's entries against the session and omit already recorded information.
3. If there is new information, call `vault_write` with `kind="daily"`, a descriptive section `title` such as `Session journal`, `tags=[]`, and concise Markdown sections for Progress, Learnings, and Open as applicable. Do not use a bare date as the title: the server chooses today's note and adds the timestamp. If nothing is new, do not write.
4. For substantial reusable knowledge, search the vault first and use the existing wiki write workflow only when a new page is appropriate. Avoid duplicates; do not claim an existing page was updated unless a tool actually updated it.
5. Report what was saved and its returned path. If a tool call is denied, fails, or requires approval, say so and do not claim success.
