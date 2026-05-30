# Daily Note Deduplication - Specification

## Overview

Daily notes accumulate structural corruption from two independent bugs in `_write_daily()` (`writer.py:106-162`):

1. **No dedup on append**: every `vault_write(kind="daily", title=X)` call creates a new `## X` heading. Same title → duplicate headings. The `2026-05-29.md` file ended up with 17 identical `## 2026-05-29` headers.

2. **Wrong target on consolidation**: `_write_daily` hardcodes `today = date.today().isoformat()` as the target file. When the `process-brain` skill consolidates yesterday's note, it calls `vault_write(kind="daily")` which writes into **today's** file — copying all of yesterday's content into today's daily. The `2026-05-30.md` file contains the entire `2026-05-29.md` (lines 64-486).

The OpenCode plugin reads raw file text via `Bun.file().text()` and injects it into the system prompt. Both corruptions become visible to the model as doubled/mixed dates.

## Requirements

### Functional Requirements

- **FR-1**: When `_write_daily` appends an entry whose `## {title}` heading already exists in the file, the existing section is updated in-place instead of creating a duplicate.
- **FR-2**: If the title does not exist, append as before (no regression).
- **FR-3**: Updating an existing section replaces the body text (including trailing tags) but preserves the heading position.
- **FR-4**: The first `# YYYY-MM-DD` H1 heading is never duplicated (already works — guarded by `filepath.exists()` on line 142).
- **FR-5**: Add an optional `target_date: str | None = None` parameter to `_write_daily`. When `None`, uses today (current behavior). When set to a date string like `"2026-05-29"`, writes to that date's file instead.
- **FR-6**: `handle_vault_write` and `write_page` pass through `target_date` when `kind="daily"`.

### Non-Functional Requirements

- **NFR-1**: Read-before-write adds one extra file read per call. For daily notes under 100 KB, negligible.
- **NFR-2**: MCP tool signature gains optional `target_date` parameter — backward compatible (default `None`).
- **NFR-3**: All 113 existing tests pass unchanged.

## Scope

### In Scope

- `_write_daily()` in `src/duckbrain/writer.py` — dedup + target_date
- `write_page()` and `handle_vault_write()` — pass through target_date
- New tests for dedup behavior and target_date in `tests/test_writer.py`

### Out of Scope

- Consolidation skill logic (`process-brain` SKILL.md) — the skill should be updated to pass `target_date` when consolidating past dailies, but that's a separate change to the skill file.
- Plugin injection logic — fixing the file fixes the injection.
- Existing corrupted files — user cleans up `2026-05-29.md` and `2026-05-30.md` manually or via a one-off script.

## Approach

### Bug 1: Dedup on append

```python
# In _write_daily, before appending:
if filepath.exists():
    existing = filepath.read_text()
    heading = f"\n## {title}"
    if heading in existing:
        # Find section boundaries
        start = existing.index(heading)
        after_heading = existing[start + len(heading):]
        next_h2 = after_heading.find("\n## ")
        if next_h2 == -1:
            updated = existing[:start] + heading + "\n\n" + entry_body
        else:
            updated = existing[:start] + heading + "\n\n" + entry_body + after_heading[next_h2:]
        filepath.write_text(updated)
        return {"success": True, "filepath": relative_path, "warnings": warnings}
```

### Bug 2: Optional target_date

```python
def _write_daily(
    vault_path: str,
    title: str,
    content: str,
    tags: list[str],
    target_date: str | None = None,  # NEW
) -> dict[str, Any]:
    ...
    today = target_date or date.today().isoformat()
    relative_path = f"daily/{today}.md"
    ...
```

`write_page` and `handle_vault_write` gain `target_date: str | None = None` and pass it through to `_write_daily`.

### Key Design Decisions

- **Exact string match on `## {title}`** — no fuzzy matching. The `title` parameter is both the user-visible heading and the dedup key.
- **target_date as opt-in parameter** — backward compatible. Existing callers (no target_date) behave identically.
- **Replace entire section** — from matched heading to next `## ` heading. Tags at the end are part of the body.
- **Write-back strategy** — read-modify-write whole file. Safe for daily notes under 100 KB.

### User Experience

No visible change for normal `vault_write` calls. The consolidation skill can now target past dates correctly.

## Dependencies

- `src/duckbrain/writer.py` — `_write_daily()`, `write_page()`
- `src/duckbrain/tools/vault_write.py` — `handle_vault_write()`
- `tests/test_writer.py` — existing daily write tests

## Success Criteria

- Writing the same title twice → single `## {title}` section (not two).
- Writing different titles → separate sections (append preserved).
- `# YYYY-MM-DD` H1 never duplicated.
- `target_date="2026-05-29"` writes to `daily/2026-05-29.md` even when run on May 30.
- All 113 existing tests pass.
- `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` pass.

## Notes

- The `2026-05-29.md` and `2026-05-30.md` files need manual cleanup after the fix. The fix prevents future corruption but doesn't repair existing files.
- The consolidation skill should be updated to pass `target_date=yesterday` when consolidating — but that's a SKILL.md edit, not a code change.
