## Session Learnings

When you encounter problems, debug issues, or discover non-obvious solutions,
save the learning to the vault so it's available in future sessions.

### When to save

Write to the vault proactively — don't wait to be asked. Especially after:

- **Debugging** — regardless of success. What you tried, what didn't work, what finally fixed it.
- **Rabbit holes** — paths that led nowhere. Know what NOT to try next time.
- **Architecture decisions** — why you chose X over Y, with trade-offs.
- **Non-obvious findings** — things the docs don't tell you, undocumented behavior, quirks.

### How to save

Always check the vault first with vault_search to see if a related note already exists.

**Daily notes** (session log, debugging, one-off learnings):

```
vault_write(
  kind="daily",
  title="short descriptive heading",
  content="what you learned, what went wrong, what fixed it",
  tags=["relevant", "tags"]
)
```

**Wiki pages** (reusable knowledge worth permanent reference):

```
vault_write(
  kind="concept",
  title="Concept Name",
  content="# Concept Name\n\nDetailed explanation...",
  tags=["relevant", "tags"]
)
```

A learning saved is a bug not repeated.
