# Daily Note Deduplication - Implementation Tasks

## Overview

Fix two bugs in `_write_daily()` that corrupt daily notes:
1. No dedup on append → duplicate `## {title}` headings
2. Hardcoded `today` → consolidation writes to wrong date's file

## Tasks

---

## SPRINT 1: Core writer.py (dedup only)

> Only `_write_daily()` in `src/duckbrain/writer.py`. `write_page` and `handle_vault_write` unchanged.

### Stream A: writer.py

- [ ] **Write failing test** `test_write_daily_dedup_merges_same_title` in `tests/test_writer.py`:
  ```python
  def test_write_daily_dedup_merges_same_title(temp_vault: Path) -> None:
      """Writing same title twice merges, not duplicates."""
      from duckbrain.writer import write_page

      today = date.today().isoformat()
      write_page(str(temp_vault), "daily", "Dup test", "Version one.", ["a"])
      write_page(str(temp_vault), "daily", "Dup test", "Version two.", ["b"])
      filepath = temp_vault / f"daily/{today}.md"
      content = filepath.read_text()
      assert content.count("## Dup test") == 1, f"Expected 1 heading, got {content.count('## Dup test')}"
      assert "Version two." in content
      assert "Version one." not in content
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_writer.py::test_write_daily_dedup_merges_same_title -v` → expect FAIL

---

- [ ] **Implement dedup logic** in `_write_daily()` — replace blind append (lines 133-147) with:
  ```python
  # Build the entry body
  entry_body = f"\n\n{content}\n"
  if tags:
      entry_body += f"\n**Tags:** {', '.join(tags)}\n"
  heading = f"\n## {title}"

  # Create daily directory if needed
  filepath.parent.mkdir(parents=True, exist_ok=True)

  # If file doesn't exist yet, prepend a top-level date heading
  if not filepath.exists():
      full_entry = f"# {today}{heading}{entry_body}\n"
      with filepath.open("a") as f:
          f.write(full_entry)
  else:
      existing = filepath.read_text()
      if heading in existing:
          # Dedup: replace existing section body
          start = existing.index(heading)
          after_heading = existing[start + len(heading):]
          next_h2 = after_heading.find("\n## ")
          if next_h2 == -1:
              updated = existing[:start] + heading + entry_body + "\n"
          else:
              updated = existing[:start] + heading + entry_body + "\n" + after_heading[next_h2:]
          filepath.write_text(updated)
      else:
          # New section: append
          with filepath.open("a") as f:
              f.write(f"{heading}{entry_body}\n")
  ```
- [ ] **Run to verify pass**: `uv run pytest tests/test_writer.py::test_write_daily_dedup_merges_same_title -v` → expect PASS
- [ ] **Run full writer suite**: `uv run pytest tests/test_writer.py -v` → expect all PASS
- [ ] **Commit**: `feat: deduplicate daily note sections in _write_daily`

---

- [ ] **Run quality gates**:
  ```bash
  uv run ruff check src/duckbrain/writer.py
  uv run ruff format --check src/duckbrain/writer.py
  uv run mypy src/duckbrain/writer.py
  ```
- [ ] **Commit** (if any fixes needed)

---

## SPRINT 2: target_date + pass-through

> Adds `target_date` to `_write_daily`, `write_page`, and `handle_vault_write`. Depends on SPRINT 1 (dedup logic must exist).

### Stream A: writer.py — target_date parameter

- [ ] **Add `target_date` parameter** to `_write_daily()` signature:
  ```python
  def _write_daily(
      vault_path: str,
      title: str,
      content: str,
      tags: list[str],
      target_date: str | None = None,  # NEW
  ) -> dict[str, Any]:
  ```
- [ ] **Update target logic**: `today = target_date or date.today().isoformat()`
- [ ] **Commit**: `feat: add target_date param to _write_daily`

---

- [ ] **Write failing test** `test_write_daily_target_date_writes_past_file` in `tests/test_writer.py`:
  ```python
  def test_write_daily_target_date_writes_past_file(temp_vault: Path) -> None:
      """target_date writes to a specific date's file, not today."""
      from duckbrain.writer import write_page

      write_page(str(temp_vault), "daily", "Past entry", "Yesterday content.", ["tag"], target_date="2025-01-15")
      filepath = temp_vault / "daily/2025-01-15.md"
      assert filepath.exists()
      content = filepath.read_text()
      assert "# 2025-01-15" in content
      assert "Past entry" in content
      assert "Yesterday content." in content
      today = date.today().isoformat()
      assert not (temp_vault / f"daily/{today}.md").exists()
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_writer.py::test_write_daily_target_date_writes_past_file -v` → expect FAIL (param not in write_page yet)
- [ ] **Run to verify pass**: `uv run pytest tests/test_writer.py::test_write_daily_target_date_writes_past_file -v` → expect PASS (param added above)
- [ ] **Commit**: `test: target_date writes to correct daily file`

---

### Stream B: write_page + handle_vault_write pass-through

> ⚠️ Depends on: Stream A — `_write_daily` must accept `target_date`

- [ ] **Add `target_date` param** to `write_page()` signature:
  ```python
  def write_page(
      vault_path: str,
      kind: str,
      title: str,
      content: str,
      tags: list[str],
      target_date: str | None = None,  # NEW
  ) -> dict[str, Any]:
  ```
- [ ] **Pass through** in daily branch:
  ```python
  if kind == "daily":
      return _write_daily(vault_path, title, content, tags, target_date=target_date)
  ```
- [ ] **Add `target_date` param** to `handle_vault_write()`:
  ```python
  def handle_vault_write(
      vault_path: str,
      kind: str,
      title: str,
      content: str,
      tags: list[str],
      target_date: str | None = None,  # NEW
  ) -> dict[str, Any]:
  ```
- [ ] **Pass through**:
  ```python
  return write_page(vault_path, kind, title, content, tags, target_date=target_date)
  ```
- [ ] **Commit**: `feat: pass target_date through write_page and handle_vault_write`

---

- [ ] **Write failing test** `test_handle_vault_write_target_date` in `tests/test_writer.py`:
  ```python
  def test_handle_vault_write_target_date(temp_vault: Path) -> None:
      """handle_vault_write passes target_date through to writer."""
      from duckbrain.tools.vault_write import handle_vault_write

      result = handle_vault_write(
          str(temp_vault), "daily", "Tool past entry", "Tool content.", ["t"],
          target_date="2025-06-01",
      )
      assert result["success"] is True
      filepath = temp_vault / "daily/2025-06-01.md"
      assert filepath.exists()
      assert "Tool past entry" in filepath.read_text()
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_writer.py::test_handle_vault_write_target_date -v` → expect FAIL
- [ ] **Run to verify pass**: `uv run pytest tests/test_writer.py::test_handle_vault_write_target_date -v` → expect PASS
- [ ] **Commit**: `test: handle_vault_write target_date passthrough`

---

- [ ] **Run full test suite**: `uv run pytest -v` → all pass
- [ ] **Run quality gates**:
  ```bash
  uv run ruff check src/duckbrain/
  uv run ruff format --check src/duckbrain/
  uv run mypy src/duckbrain/
  ```
- [ ] **Commit** (if any fixes needed)

---

## Summary

### Sprint Overview

| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| 1 | Core dedup | 5 | A |
| 2 | target_date + pass-through | 14 | A, B |

### Total Effort

- **Sprints**: 2
- **Streams**: 3 (A, A, B)
- **Tasks**: 19

### Key Design Decisions

- `target_date: str | None = None` — backward compatible, opt-in
- Dedup key is exact `## {title}` string match — no fuzzy logic
- Read-modify-write for dedup — safe for daily notes under 100 KB
- H1 `# YYYY-MM-DD` never duplicated (existing guard preserved)

### Quality Standards

- No placeholders — all code fully functional when marked complete
- TDD: test first, verify fail, implement, verify pass
- All quality gates pass before commit
- Existing tests never broken
