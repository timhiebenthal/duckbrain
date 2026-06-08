# Wikilink Graph Navigation - Specification

## Overview

Extract `[[wikilinks]]` from vault page bodies during scanning and expose them as
first-class navigational data. Adds backlink discovery (Obsidian's "what links
here?") and outgoing link listing. This also creates the metadata needed for a
future link-based search ranking boost.

The vault already contains explicit link structure — pages like `Recall` link to
`[[Agent Memory Systems]]`, `DuckBrain` links to `[[OpenCode]]`. DuckBrain currently
treats these as opaque body text. This spec makes the link graph queryable.

## Requirements

### Functional Requirements

1. **Wikilink extraction**: During `scan_vault()`, parse `[[wikilinks]]` from body
   text and store them in a new `links: list[str]` field on `PageMetadata`.
2. **Links column in DuckDB**: The indexer stores links as a comma-separated
   `VARCHAR` column (same pattern as `tags`) and backlink queries use exact
   comma-delimited membership, not substring matching.
3. **`vault_backlinks(title)` tool**: Returns all pages whose outgoing links
   include the given title — "what links here?"
4. **`vault_links(title)` tool**: Returns outgoing links from a specific page —
   "what does this page link to?"
5. **Augmented `vault_read`**: When reading a page, include parsed `links`
   (outgoing wikilinks) in the returned dict alongside the body content.
   Backlinks are available via the separate `vault_backlinks` tool — computing
   them requires a full vault scan, which `vault_read` avoids for performance.
6. **Wikilink parsing rules**:
   - `[[Page Name]]` → `"Page Name"`
   - `[[Page Name|alias]]` → `"Page Name"` (strip alias)
   - `[[Page Name#section]]` → `"Page Name"` (strip heading anchor)
   - Malformed (e.g., unclosed `[[`) → ignore
   - Self-links (page links to itself) → skip
   - Duplicate links in same page → deduplicate

### Non-Functional Requirements

- **No new dependencies** — regex-only, zero changes to `pyproject.toml`
- **Backward compatible** — `PageMetadata.links` defaults to `[]`; existing
  tests unaffected
- **Performance** — regex applied once per page during scan; backlinks resolved
  via SQL membership checks on the comma-separated column; O(n) for < 1000
  pages is negligible

## Scope

### In Scope

- Add `links` field to `PageMetadata` dataclass (`__init__.py`)
- Wikilink extraction function (`scanner.py`)
- Store links in DuckDB pages table (`indexer.py`)
- New tool: `vault_backlinks` (`tools/vault_backlinks.py`)
- New tool: `vault_links` (`tools/vault_links.py`)
- Augment `vault_read` to return outgoing `links` alongside body
- Register new tools in `server.py`
- Update README Tools section with `vault_backlinks` and `vault_links`
- Tests for extraction, backlinks query, links query, read integration

### Out of Scope

- Link-based search ranking boost (defer to a future spec — requires ranking
  algorithm design and changes to the search function's scoring model)
- Graph visualization (HTML/vis.js output — this is an MCP server, not a UI)
- Leiden community detection or clustering
- Bidirectional link graph traversal / path finding
- Unlinked mentions (detecting page titles in body text without `[[brackets]]`)

## Approach

### Technical Approach

**1. Wikilink regex** (`scanner.py`, new function):

```python
_WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]')

def extract_wikilinks(body: str, own_title: str) -> list[str]:
    """Extract [[wikilinks]] from body, skip self-links, deduplicate."""
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

Rules:
- `[^\]|#]+` captures the page name, stopping at `|` (alias) or `#` (heading)
- `(?:[|#][^\]]+)?` optionally matches alias/heading after the separator
- Self-links filtered out
- Deduplication preserves order

**2. Scanner integration** (`scanner.py`, `scan_vault()`):

After parsing frontmatter and body, call `extract_wikilinks(body, title)` and
pass to `PageMetadata(links=links)`.

**3. Indexer integration** (`indexer.py`, `build_fts_index()`):

Add `links VARCHAR` column to the pages table. Insert as a comma-separated
string (same as `tags`). The existing FTS index on `'title', 'tags', 'body'`
does not need to include `links` — links are navigational metadata, not
searchable content.

**4. Backlinks query** (`tools/vault_backlinks.py`):

```python
def get_backlinks(conn, title: str) -> list[dict]:
    """Return pages whose outgoing links include *title* exactly."""
    sql = """
        SELECT title, kind, filepath,
               COALESCE(substr(body, 1, 150) || CASE WHEN length(body) > 150 THEN '...' ELSE '' END, '') AS snippet,
               created, updated
        FROM pages
        WHERE list_contains(string_split(links, ','), $title)
        ORDER BY title
    """
```

Use exact membership over `string_split(links, ',')` instead of a broad
`LIKE '%title%'` predicate. This avoids false positives such as `title = "AI"`
matching `"AID"` and avoids wildcard escaping issues for titles containing `%`
or `_`.

**5. `vault_read` augmentation** (`tools/vault_read.py`):

Include outgoing `links` only. Backlinks stay behind the separate
`vault_backlinks(title)` tool because computing them requires scanning/indexing
the full vault.

- For `vault_read(title=...)`, use the `PageMetadata.links` collected by
  `scan_vault()`.
- For `vault_read(filepath=...)`, preserve the current direct-file fast path:
  parse frontmatter/body from the file, infer the title, and call
  `extract_wikilinks(body, title)` directly. Do not build the full index just to
  return outgoing links.

**6. `vault_links` query** (`tools/vault_links.py`):

`handle_vault_links(vault_path, title)` scans the vault, finds the page by
case-insensitive title, and returns its `PageMetadata.links`. Missing pages
return an `error` dict or an empty result consistently with existing tool style;
prefer the existing `vault_read` pattern: `{"error": "Page not found: ..."}`.

### Files Changed

| File | Change |
|---|---|
| `src/duckbrain/__init__.py` | Add `links` field to `PageMetadata` |
| `src/duckbrain/scanner.py` | Add `extract_wikilinks()`, call during scan |
| `src/duckbrain/indexer.py` | Add `links` column to pages table, insert link data |
| `src/duckbrain/tools/vault_backlinks.py` | **New** — `handle_vault_backlinks()` |
| `src/duckbrain/tools/vault_links.py` | **New** — `handle_vault_links()` |
| `src/duckbrain/tools/vault_read.py` | Include outgoing `links` in result |
| `src/duckbrain/server.py` | Register `vault_backlinks` and `vault_links` tools |
| `README.md` | Document `vault_backlinks` and `vault_links` in the Tools section |
| `tests/test_scanner.py` | Test wikilink extraction |
| `tests/test_vault_backlinks.py` | **New** — test backlink queries |
| `tests/test_vault_links.py` | **New** — test outgoing link queries |
| `tests/test_vault_read.py` | Test augmented title and filepath reads with outgoing links |
| `tests/conftest.py` | Add pages with wikilinks to `temp_vault` |

### User Experience

New MCP tools available to agents:

```python
# Discover what links to a page
vault_backlinks("Agent Memory Systems")
# → [{"title": "Recall", "kind": "entity", "filepath": "...", ...},
#    {"title": "DuckBrain", "kind": "entity", "filepath": "...", ...}]

# See what a page links to
vault_links("DuckBrain")
# → ["OpenCode", "Agent Memory Systems", "DuckDB", "MCP"]

# Read a page with navigation context
vault_read(title="DuckBrain")
# → {"title": "DuckBrain", "content": "...", "links": ["OpenCode", "Agent Memory Systems", "DuckDB", "MCP"]}
```

### Design Decision: why comma-separated, not a separate edges table

A normalized `edges(source, target)` table would be cleaner for SQL joins, but:
- DuckDB's FTS extension operates on a single table
- The vault page count is small (< 500) — splitting the comma-separated column
  at query time is fast enough
- Keeps implementation simple — one table, no schema changes to FTS
- Can be migrated to a normalized table later without API changes

## Dependencies

- No new PyPI dependencies
- No external services or APIs

## Success Criteria

- `uv run pytest` passes with new tests
- `uv run ruff check src/duckbrain/` — 0 errors
- `uv run ruff format --check src/duckbrain/` — all formatted
- `uv run mypy src/duckbrain/` — 0 errors
- `[[Page Name]]`, `[[Page|alias]]`, `[[Page#section]]` all extract correctly
- Self-links and duplicates are filtered
- `vault_backlinks("NonexistentPage")` returns `[]` (no crash)
- `vault_backlinks("AI")` does not return pages that only link to `AID`
- Existing scanner and indexer tests pass unchanged
- Links are present in `vault_read` output alongside body content for both
  `title` and `filepath` reads
- README lists `vault_backlinks` and `vault_links`

## Notes

- This is a prerequisite for future link-based search ranking — once links are
  extracted and stored, boosting BM25 scores by backlink count becomes trivial.
- The `vault_links` tool could later support filtering by link target kind
  (e.g., "show only concept pages linked from this page").
- Unlinked mentions (detecting page titles in body without `[[brackets]]`) is
  a common Obsidian plugin but adds significant complexity (needs title list,
  substring matching with false-positive risk). Explicitly deferred.
