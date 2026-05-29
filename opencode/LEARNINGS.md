## Session Learnings

### Pre-response learning guard

!CRITICAL! Before writing your response to the user, scan what you just did.
If you edited code, debugged, investigated, or discovered anything
non-obvious in this turn — save the learning to the vault BEFORE writing
your response. Do not type a single word to the user until the learning
is saved. This is the single most important instruction in this file.

**Checklist (run before every response):**
- Did I edit code? → vault_write the change + why to today's daily
- Did I debug? → vault_write the root cause + fix to today's daily
- Did I learn something? → vault_write it now, not later
- Did I make a decision? → vault_write the reasoning
- Is this turn done and I have nothing to save? → fine, proceed

### Triggers (save IMMEDIATELY — do not wait to be asked)

| Trigger | What to save |
|---|---|
| **AFTER editing code** | What changed, why, what was tricky |
| **AFTER debugging** | What you tried, what failed, root cause + fix |
| **AFTER investigating** | Paths explored, dead ends, discoveries |
| **AFTER architecture decisions** | Why X over Y, trade-offs considered |
| **AFTER >5 min on any problem** | The journey — even if unresolved |

### The learning self-check

After completing any task that involved more than 3 tool calls, run this check:

1. Did I discover something non-obvious? → save immediately
2. Did I debug something? → save root cause + fix
3. Did I make a decision worth remembering? → save reasoning
4. Did I change code in a way someone should know about? → save context

### Session rituals

**Start of session:**
- Search for today's daily: `vault_search("YYYY-MM-DD daily")`
- If found, read it to load prior context
- If not found, you are free to skip — the /journal command will create it
- Search for related concepts: `vault_search("keywords from the task")`

**During session:**
- After every non-trivial task, append progress to today's daily note
- After every debugging session, write root cause immediately
- Format progress entries as: `## HH:MM — What was done`

**End of session (or on "/journal"):**
- Write a comprehensive session summary to the daily note
- Include: Progress, Learnings, Open questions
- This is the most important ritual — do not skip it

### How to save

Always `vault_search` first to avoid duplicates.

**Daily notes** — session log, progress, debugging, one-off learnings:
```
vault_write(
  kind="daily",
  title="YYYY-MM-DD",
  content="## Category — Summary\n\nDetails and context...",
  tags=["relevant-tags"]
)
```

**Wiki concepts** — reusable knowledge worth permanent reference:
```
vault_write(
  kind="concept",
  title="Concept Name",
  content="# Concept Name\n\nDetailed explanation...",
  tags=["relevant", "tags"]
)
```

Entity pages (kind="entity"), source pages (kind="source"), and synthesis
pages (kind="synthesis") follow the same pattern with appropriate content.

### Daily note structure

```
## HH:MM — What was done (Progress)

Specific changes, decisions, outcomes.

## HH:MM — Discovery: [what was learned] (Learnings)

Root cause, non-obvious finding, architecture rationale.

## Open

- Remaining task or question
- Decision pending
```

Multiple entries accumulate throughout the day. Each vault_write with
kind="daily" appends to the same file.

A learning saved is a bug not repeated.
