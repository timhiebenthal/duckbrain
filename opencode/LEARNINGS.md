## Session Learnings

### Pre-response learning guard

!CRITICAL! Before writing your response to the user, scan what you just did.
If you edited code, debugged, investigated, or discovered anything
non-obvious in this turn — save the learning to the vault BEFORE writing
your response. Do not type single word to user until learning saved.
Most important instruction in this file.

**Checklist (run before every response):**
- Did I edit code? → vault_write change + why to today's daily
- Did I debug? → vault_write root cause + fix to today's daily
- Did I learn something? → vault_write now, not later
- Did I make a decision? → vault_write reasoning
- Nothing to save? → proceed

### Triggers (save IMMEDIATELY — do not wait to be asked)

| Trigger | What to save |
|---|---|
| **AFTER editing code** | What changed, why, what was tricky |
| **AFTER debugging** | What you tried, what failed, root cause + fix |
| **AFTER investigating** | Paths explored, dead ends, discoveries |
| **AFTER architecture decisions** | Why X over Y, trade-offs considered |
| **AFTER >5 min on any problem** | Journey — even if unresolved |

### Session rituals

**Start of session:**
- Search today's daily: `vault_search("YYYY-MM-DD daily")`
- Found? Read to load prior context
- Not found? Skip — /journal command creates it
- Search related concepts: `vault_search("keywords from task")`

**During session:**
- After non-trivial task, append progress to daily note
- After debugging, write root cause immediately
- Format: `## HH:MM — What was done`

**End of session (or on "/journal"):**
- Write session summary to daily note
- Include: Progress, Learnings, Open questions
- Most important ritual — do not skip

### How to save

`vault_search` first to avoid duplicates.

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

Entity pages (kind="entity"), source pages (kind="source"), synthesis
pages (kind="synthesis") follow same pattern.

### Daily note structure

Caveman-concise. Cut filler words, keep substance.
"`Removed self-check — redundant with guard`" not
"`We decided to remove the self-check section because it was unrealistic.`"

Expand only when detail matters: debugging root cause, architecture
trade-offs, non-obvious findings.

```
## HH:MM — What was done (Progress)

Concise changes, decisions, outcomes.

## HH:MM — Discovery: [what was learned] (Learnings)

Root cause, non-obvious finding, architecture rationale.

## Open

- Remaining task or question
- Decision pending
```

Multiple entries accumulate through day. Each vault_write
kind="daily" appends to same file.

Learning saved is bug not repeated.
