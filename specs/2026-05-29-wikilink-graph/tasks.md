# Wikilink Graph Navigation - Implementation Tasks

## Overview

Extract `[[wikilinks]]` from vault pages during scanning, store them in DuckDB,
and expose two new MCP tools (`vault_backlinks`, `vault_links`) plus augmented
`vault_read` output. Zero new dependencies — regex only.

## Tasks

---

## SPRINT 1: Foundation

> Goal: `PageMetadata` carries links; `extract_wikilinks()` exists and is wired into `scan_vault()`.
> Streams A and B are independent and can run in parallel.

### Stream A: `src/duckbrain/__init__.py`

- [ ] **Write failing test** for `links` field presence in `test_scanner.py`:
  ```python
  def test_page_metadata_has_links_field() -> None:
      from duckbrain import PageMetadata
      p = PageMetadata(filepath="x.md", title="T", kind="concept")
      assert p.links == []
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_scanner.py::test_page_metadata_has_links_field -v` → expect `AttributeError` / FAIL
- [ ] **Write implementation**: add `links: list[str] = field(default_factory=list)` to `PageMetadata` after `tags`
- [ ] **Run to verify pass**: `uv run pytest tests/test_scanner.py::test_page_metadata_has_links_field -v` → PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(metadata): add links field to PageMetadata`

---

### Stream B: `src/duckbrain/scanner.py` + `tests/test_scanner.py`

⚠️ Depends on: SPRINT 1 — Stream A (`PageMetadata.links` field)

- [ ] **Write failing tests** for `extract_wikilinks` in `tests/test_scanner.py`:
  ```python
  def test_extract_wikilinks_basic() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("See [[Foo]] and [[Bar]].", "Self") == ["Foo", "Bar"]

  def test_extract_wikilinks_alias() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("See [[Page Name|alias]].", "Self") == ["Page Name"]

  def test_extract_wikilinks_anchor() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("See [[Page Name#section]].", "Self") == ["Page Name"]

  def test_extract_wikilinks_self_link_skipped() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("Links to [[Self]] here.", "Self") == []

  def test_extract_wikilinks_dedup_preserves_order() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("[[Foo]] and [[Bar]] and [[Foo]] again.", "Self") == ["Foo", "Bar"]

  def test_extract_wikilinks_malformed_ignored() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("Unclosed [[Foo and normal text.", "Self") == []

  def test_extract_wikilinks_empty_body() -> None:
      from duckbrain.scanner import extract_wikilinks
      assert extract_wikilinks("", "Self") == []
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_scanner.py -k "extract_wikilinks" -v` → expect `ImportError` / FAIL
- [ ] **Write implementation** in `scanner.py`:
  - Add module-level constant: `_WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]')`
  - Add function:
    ```python
    def extract_wikilinks(body: str, own_title: str) -> list[str]:
        matches = _WIKILINK_RE.findall(body)
        seen: set[str] = set()
        result: list[str] = []
        for m in matches:
            link = m.strip()
            if link and link != own_title and link not in seen:
                seen.add(link)
                result.append(link)
        return result
    ```
  - In `scan_vault()`, after `meta, body = parse_frontmatter(content)` and `title = meta.get(...)`, call `links = extract_wikilinks(body, title)` and pass `links=links` to `PageMetadata(...)`
  - In `scan_daily()`, call `links = extract_wikilinks(body, date_str)` and pass `links=links` to `PageMetadata(...)`
- [ ] **Write scan integration test** in `tests/test_scanner.py` (requires conftest update from Sprint 2 Stream B — add after that stream):
  ```python
  def test_scan_vault_populates_links(temp_vault: Path) -> None:
      from duckbrain.scanner import scan_vault
      pages = scan_vault(str(temp_vault))
      recall = next((p for p in pages if p.title == "Recall"), None)
      assert recall is not None
      assert "Agent Memory Systems" in recall.links

  def test_scan_vault_page_without_wikilinks_has_empty_links(temp_vault: Path) -> None:
      from duckbrain.scanner import scan_vault
      pages = scan_vault(str(temp_vault))
      claude_mem = next((p for p in pages if p.title == "Claude Mem"), None)
      assert claude_mem is not None
      assert claude_mem.links == []
  ```
- [ ] **Run to verify pass**: `uv run pytest tests/test_scanner.py -k "extract_wikilinks" -v` → PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(scanner): add extract_wikilinks() and wire into scan_vault()`

---

## SPRINT 2: Storage + Fixtures

> Goal: DuckDB has a `links` column; test fixtures include pages with wikilinks.
> Streams A and B are independent and can run in parallel.

### Stream A: `src/duckbrain/indexer.py`

⚠️ Depends on: SPRINT 1 — Stream A (`PageMetadata.links` field)

- [ ] **Write failing test** for links column in `tests/test_indexer.py`:
  ```python
  def test_build_fts_index_stores_links(sample_pages) -> None:
      from duckbrain.indexer import build_fts_index
      # Add a page with links to sample_pages before calling
      from duckbrain import PageMetadata
      pages = sample_pages + [
          PageMetadata(
              filepath="wiki/entities/recall.md",
              title="Recall",
              kind="entity",
              tags=[],
              body="See [[Agent Memory Systems]].",
              links=["Agent Memory Systems"],
          )
      ]
      conn = build_fts_index(pages)
      row = conn.execute(
          "SELECT links FROM pages WHERE title = 'Recall'"
      ).fetchone()
      conn.close()
      assert row is not None
      assert row[0] == "Agent Memory Systems"
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_indexer.py::test_build_fts_index_stores_links -v` → expect `OperationalError` (no `links` column) / FAIL
- [ ] **Write implementation** in `indexer.py`:
  - Add `links VARCHAR` to `CREATE TABLE pages (...)` after `updated VARCHAR`
  - Add `",".join(p.links)` as 8th value in `conn.execute("INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [...])`
- [ ] **Run to verify pass**: `uv run pytest tests/test_indexer.py -v` → all PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(indexer): add links column to pages table`

---

### Stream B: `tests/conftest.py`

⚠️ Depends on: SPRINT 1 — Stream A (`PageMetadata.links` field)

- [ ] **Write implementation** (no standalone test — fixtures are verified by consumer tests):
  - In `temp_vault` fixture, add a "Recall" entity page with `[[Agent Memory Systems]]` and `[[DuckBrain]]` in the body:
    ```python
    recall_page = """---
    title: Recall
    item-type: entity
    tags: [memory, ai]
    created: 2026-05-28
    updated: 2026-05-28
    ---

    # Recall

    Recall links to [[Agent Memory Systems]] as its primary taxonomy.
    It also references [[DuckBrain]] for implementation context.
    """
    (wiki / "entities" / "recall.md").write_text(recall_page)
    ```
  - Add a "AID Tool" entity page that links to `[[AID]]` (not `[[AI]]`) to support the false-positive test:
    ```python
    aid_page = """---
    title: AID Tool
    item-type: entity
    tags: []
    created: 2026-05-28
    updated: 2026-05-28
    ---

    # AID Tool

    See [[AID]] for more.
    """
    (wiki / "entities" / "aid-tool.md").write_text(aid_page)
    ```
  - Update the `assert len(pages) == 6` count in `test_scanner.py` tests to `== 8` (6 original + Recall + AID Tool)
  - In `sample_pages` fixture, add a `PageMetadata` entry for "Recall" with `links=["Agent Memory Systems", "DuckBrain"]`
- [ ] **Run to verify**: `uv run pytest tests/test_scanner.py -v` → all PASS (count assertions updated)
- [ ] **Commit**: `test(conftest): add pages with wikilinks to temp_vault and sample_pages fixtures`

---

## SPRINT 3: New Tools + vault_read Augmentation

> Goal: `vault_backlinks`, `vault_links`, and updated `vault_read` all functional with tests.
> Streams A, B, C are independent and can run in parallel.

### Stream A: `src/duckbrain/tools/vault_backlinks.py` + `tests/test_vault_backlinks.py`

⚠️ Depends on: SPRINT 2 — Stream A (indexer `links` column)
⚠️ Depends on: SPRINT 2 — Stream B (conftest fixtures with wikilinks)

- [ ] **Write failing tests** in `tests/test_vault_backlinks.py` (new file):
  ```python
  """Tests for vault_backlinks tool."""
  from pathlib import Path

  def test_vault_backlinks_returns_linking_pages(temp_vault: Path) -> None:
      from duckbrain.tools.vault_backlinks import handle_vault_backlinks
      result = handle_vault_backlinks(str(temp_vault), "Agent Memory Systems")
      titles = [r["title"] for r in result]
      assert "Recall" in titles

  def test_vault_backlinks_result_shape(temp_vault: Path) -> None:
      from duckbrain.tools.vault_backlinks import handle_vault_backlinks
      result = handle_vault_backlinks(str(temp_vault), "Agent Memory Systems")
      assert len(result) > 0
      r = result[0]
      assert "title" in r
      assert "kind" in r
      assert "filepath" in r
      assert "snippet" in r

  def test_vault_backlinks_empty_for_unlinked_page(temp_vault: Path) -> None:
      from duckbrain.tools.vault_backlinks import handle_vault_backlinks
      result = handle_vault_backlinks(str(temp_vault), "Nonexistent Page")
      assert result == []

  def test_vault_backlinks_no_false_positives(temp_vault: Path) -> None:
      """'AI' must not match pages that only link to 'AID'."""
      from duckbrain.tools.vault_backlinks import handle_vault_backlinks
      result = handle_vault_backlinks(str(temp_vault), "AI")
      titles = [r["title"] for r in result]
      assert "AID Tool" not in titles

  def test_vault_backlinks_ordered_by_title(temp_vault: Path) -> None:
      from duckbrain.tools.vault_backlinks import handle_vault_backlinks
      result = handle_vault_backlinks(str(temp_vault), "Agent Memory Systems")
      titles = [r["title"] for r in result]
      assert titles == sorted(titles)
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_vault_backlinks.py -v` → expect `ModuleNotFoundError` / FAIL
- [ ] **Write implementation** in `src/duckbrain/tools/vault_backlinks.py` (new file):
  ```python
  """MCP tool: vault_backlinks — find pages that link to a given title."""

  from typing import Any

  from duckbrain.indexer import build_fts_index
  from duckbrain.scanner import scan_vault


  def handle_vault_backlinks(vault_path: str, title: str) -> list[dict[str, Any]]:
      pages = scan_vault(vault_path)
      conn = build_fts_index(pages)
      try:
          sql = """
              SELECT title, kind, filepath,
                     COALESCE(substr(body, 1, 150) ||
                         CASE WHEN length(body) > 150 THEN '...' ELSE '' END, '') AS snippet,
                     created, updated
              FROM pages
              WHERE list_contains(string_split(links, ','), $title)
              ORDER BY title
          """
          rows = conn.execute(sql, {"title": title}).fetchall()
      finally:
          conn.close()

      return [
          {
              "title": row[0],
              "kind": row[1],
              "filepath": row[2],
              "snippet": row[3],
              "created": row[4],
              "updated": row[5],
          }
          for row in rows
      ]
  ```
- [ ] **Run to verify pass**: `uv run pytest tests/test_vault_backlinks.py -v` → all PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(tools): add vault_backlinks tool`

---

### Stream B: `src/duckbrain/tools/vault_links.py` + `tests/test_vault_links.py`

⚠️ Depends on: SPRINT 1 — Stream B (`scan_vault()` populates `links`)
⚠️ Depends on: SPRINT 2 — Stream B (conftest fixtures with wikilinks)

- [ ] **Write failing tests** in `tests/test_vault_links.py` (new file):
  ```python
  """Tests for vault_links tool."""
  from pathlib import Path

  def test_vault_links_returns_outgoing_links(temp_vault: Path) -> None:
      from duckbrain.tools.vault_links import handle_vault_links
      result = handle_vault_links(str(temp_vault), "Recall")
      assert isinstance(result, list)
      assert "Agent Memory Systems" in result
      assert "DuckBrain" in result

  def test_vault_links_empty_for_page_without_links(temp_vault: Path) -> None:
      from duckbrain.tools.vault_links import handle_vault_links
      result = handle_vault_links(str(temp_vault), "Claude Mem")
      assert result == []

  def test_vault_links_not_found_returns_error(temp_vault: Path) -> None:
      from duckbrain.tools.vault_links import handle_vault_links
      result = handle_vault_links(str(temp_vault), "Nonexistent Page")
      assert "error" in result

  def test_vault_links_case_insensitive_lookup(temp_vault: Path) -> None:
      from duckbrain.tools.vault_links import handle_vault_links
      result = handle_vault_links(str(temp_vault), "recall")
      assert isinstance(result, list)
      assert "Agent Memory Systems" in result
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_vault_links.py -v` → expect `ModuleNotFoundError` / FAIL
- [ ] **Write implementation** in `src/duckbrain/tools/vault_links.py` (new file):
  ```python
  """MCP tool: vault_links — list outgoing wikilinks from a page."""

  from typing import Any

  from duckbrain.scanner import scan_vault


  def handle_vault_links(vault_path: str, title: str) -> list[str] | dict[str, Any]:
      pages = scan_vault(vault_path)
      title_lower = title.strip().lower()
      for page in pages:
          if page.title.lower() == title_lower:
              return page.links
      return {"error": f"Page not found: {title}"}
  ```
- [ ] **Run to verify pass**: `uv run pytest tests/test_vault_links.py -v` → all PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(tools): add vault_links tool`

---

### Stream C: `src/duckbrain/tools/vault_read.py` + `tests/test_vault_read.py`

⚠️ Depends on: SPRINT 1 — Stream B (`extract_wikilinks()` available in `scanner.py`)
⚠️ Depends on: SPRINT 2 — Stream B (conftest fixtures with wikilinks)

- [ ] **Write failing tests** (add to `tests/test_vault_read.py`):
  ```python
  def test_vault_read_includes_links_by_title(temp_vault: Path) -> None:
      result = handle_vault_read(str(temp_vault), title="Recall")
      assert "links" in result
      assert "Agent Memory Systems" in result["links"]
      assert "DuckBrain" in result["links"]

  def test_vault_read_includes_links_by_filepath(temp_vault: Path) -> None:
      result = handle_vault_read(
          str(temp_vault), filepath="wiki/entities/recall.md"
      )
      assert "links" in result
      assert "Agent Memory Systems" in result["links"]

  def test_vault_read_empty_links_for_page_without_wikilinks(temp_vault: Path) -> None:
      result = handle_vault_read(str(temp_vault), title="Claude Mem")
      assert "links" in result
      assert result["links"] == []

  def test_vault_read_filepath_links_does_not_include_self(temp_vault: Path) -> None:
      result = handle_vault_read(
          str(temp_vault), filepath="wiki/entities/recall.md"
      )
      assert "Recall" not in result["links"]
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_vault_read.py -k "links" -v` → expect `KeyError` / FAIL
- [ ] **Write implementation** in `vault_read.py`:
  - Add `from duckbrain.scanner import extract_wikilinks` to imports
  - In the `filepath` branch: after reading `content`, derive `title_for_links = filepath.rsplit("/", 1)[-1].removesuffix(".md")` and add `"links": extract_wikilinks(content, title_for_links)` to the returned dict
  - In the `title` branch: after finding `page`, add `"links": page.links` to the returned dict
- [ ] **Run to verify pass**: `uv run pytest tests/test_vault_read.py -v` → all PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(vault_read): include outgoing links in read result`

---

## SPRINT 4: Integration + Docs

> Goal: New tools registered in the server; README updated.
> Streams A and B are independent and can run in parallel.

### Stream A: `src/duckbrain/server.py`

⚠️ Depends on: SPRINT 3 — Stream A (`handle_vault_backlinks`)
⚠️ Depends on: SPRINT 3 — Stream B (`handle_vault_links`)

- [ ] **Write failing test** in `tests/test_server.py` or a new `tests/test_e2e.py` entry:
  ```python
  def test_server_registers_vault_backlinks() -> None:
      import importlib, inspect
      import duckbrain.server as srv
      src = inspect.getsource(srv)
      assert "vault_backlinks" in src

  def test_server_registers_vault_links() -> None:
      import inspect
      import duckbrain.server as srv
      src = inspect.getsource(srv)
      assert "vault_links" in src
  ```
- [ ] **Run to verify failure**: `uv run pytest tests/test_server.py -k "vault_backlinks or vault_links" -v` → FAIL
- [ ] **Write implementation** in `server.py`:
  - Add imports: `from duckbrain.tools.vault_backlinks import handle_vault_backlinks` and `from duckbrain.tools.vault_links import handle_vault_links`
  - Register `vault_backlinks` tool:
    ```python
    @server.tool()
    def vault_backlinks(title: str) -> list[dict]:
        """Find all pages that link to the given page title. Returns titles, kinds, and snippets."""
        return handle_vault_backlinks(vault_path, title)
    ```
  - Register `vault_links` tool:
    ```python
    @server.tool()
    def vault_links(title: str) -> list[str] | dict:
        """List all outgoing [[wikilinks]] from the given page title."""
        return handle_vault_links(vault_path, title)
    ```
- [ ] **Run to verify pass**: `uv run pytest tests/test_server.py -v` → all PASS; then `uv run pytest` → all pass
- [ ] **Commit**: `feat(server): register vault_backlinks and vault_links tools`

---

### Stream B: `README.md`

⚠️ Depends on: SPRINT 3 — Stream A and B (tool signatures confirmed)

- [ ] **Write implementation**: add two rows to the Tools table (line ~188):
  ```markdown
  | `vault_backlinks` | Find all pages that link to a given title |
  | `vault_links` | List outgoing wikilinks from a page |
  ```
- [ ] **Verify**: `grep -c "vault_backlinks\|vault_links" README.md` → returns `2` or more
- [ ] **Commit**: `docs(readme): document vault_backlinks and vault_links tools`

---

## Final Verification

- [ ] **Run full suite**: `uv run pytest` → all pass, no warnings
- [ ] **Lint**: `uv run ruff check src/duckbrain/` → 0 errors
- [ ] **Format check**: `uv run ruff format --check src/duckbrain/` → clean
- [ ] **Type check**: `uv run mypy src/duckbrain/` → 0 errors

---

## Summary

### Sprint Overview

| Sprint | Name | Streams | Key Deliverable |
|--------|------|---------|----------------|
| 1 | Foundation | A, B | `PageMetadata.links` + `extract_wikilinks()` |
| 2 | Storage + Fixtures | A, B | DuckDB `links` column + test fixtures |
| 3 | Tools + vault_read | A, B, C | All three tool implementations |
| 4 | Integration + Docs | A, B | Server registration + README |

### Total Effort

- Sprints: 4
- Streams: 9
- Source files changed: 7
- New files: 4 (`vault_backlinks.py`, `vault_links.py`, `test_vault_backlinks.py`, `test_vault_links.py`)
- Test files modified: 4

## Notes

- `vault_backlinks` uses the DuckDB index (requires full scan + index build); `vault_links` uses `scan_vault()` directly (no index). Both are O(n) for < 500 pages — acceptable.
- `list_contains(string_split(links, ','), $title)` is DuckDB-native exact membership — no LIKE wildcard issues.
- In the `filepath` fast path of `vault_read`, title is inferred from the filename stem. This matches how `scan_vault()` derives titles (`title = meta.get("title", filepath.stem)`). For pages with a `title:` frontmatter field that differs from the filename, self-link filtering may miss self-links — acceptable edge case given it only affects filtering, not correctness.
- `scan_daily()` also calls `extract_wikilinks()` for completeness, though daily notes rarely contain wiki-style links.

### Quality Standards

- No placeholders — every task item is fully functional when checked
- TDD: tests written before implementation in every stream
- All existing tests pass unchanged after each sprint
