---
description: Journal the session — save all progress, learnings, and open items to today's daily note
---

You are journaling the current session. Execute these steps immediately:

## 1. Review the session

Scan what happened:
- What code was changed? (check git diff if available)
- What was debugged? What was the root cause?
- What decisions were made? Why?
- What was investigated but not yet completed?

## 2. Search for today's daily note

vault_search(query="YYYY-MM-DD") where YYYY-MM-DD is today's date.

If a daily note exists, vault_read it to understand what's already logged.
If none exists, you'll create one in step 3.

## 3. Write the session summary

Be concise — caveman-style. Skip filler words and pretty sentences.
Cut noise, not information. Expand only when detail matters.

**Progress entries:** terse. "`Added build step to CI`" not
"`I went ahead and added a build step to the CI pipeline.`"

**Learnings:** expand when it matters. Debugging root cause, architecture
trade-offs, non-obvious findings — keep the detail. Routine changes — keep it brief.

Use vault_write(kind="daily", title="YYYY-MM-DD", ...) with this structure:

```
## Session journal — [time range or brief label]

## Progress
- [concise, chronological]

## Learnings
- [terse unless detail matters]
- [bug root cause + how it was found]
- [architecture decision + trade-off]

## Open
- [concise bullets]
```

If the user provided context after the /journal command, incorporate it in the summary.

## 4. Permanent learnings check

For each significant learning in this session, ask: "Is this reusable knowledge?"
If yes → also create a wiki concept page or update an existing one.

## 5. Confirm

Tell the user what was saved and where. Example:
"Saved session summary to daily/2026-06-08.md: 3 progress items, 2 learnings, 1 open question."
