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

Use vault_write(kind="daily", title="YYYY-MM-DD", ...) with this structure:

```
## Session journal — [time range or brief label]

## Progress
- [what was accomplished, chronologically]

## Learnings
- [every non-obvious discovery]
- [bug root cause + how it was found]
- [architecture decision + trade-off]

## Open
- [what remains to be done]
- [open questions]
- [next steps for the next session]
```

If the user provided context (e.g., "/journal finished auth, blocked on DB"), incorporate it.

## 4. Permanent learnings check

For each significant learning in this session, ask: "Is this reusable knowledge?"
If yes → also create a wiki concept page or update an existing one.

## 5. Confirm

Tell the user what was saved and where. Example:
"Saved session summary to daily/YYYY-MM-DD.md: 3 progress items, 2 learnings, 1 open question."

$ARGUMENTS: Additional context the user wants included in the journal entry.
