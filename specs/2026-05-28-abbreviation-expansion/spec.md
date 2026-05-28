# Abbreviation & Synonym Expansion for vault_search

## Overview

DuckDB FTS matches tokens, not concepts. A query for "SCD" won't find pages that only mention "slowly changing dimensions" — and vice versa. This is the 20% recall gap the original [[duckdb-memory-mcp-build-decision]] page acknowledged ("FTS covers ~80% of recall").

**Solution**: Auto-discover abbreviations from the vault's existing pages (which already contain patterns like `SCD (slowly changing dimensions)`), build an expansion table, and expand queries before running FTS. Manual overrides for edge cases.

This keeps the zero-infra promise — no embeddings, no vector DB, no new dependencies.

## Requirements

### Functional Requirements

- **FR-1: Auto-discover abbreviations from vault pages.** Scan all wiki markdown files for parenthetical definition patterns: `ABBREV (Full Form)`, `Full Form (ABBREV)`, and `**ABBREV** — Full Form`. Build an in-memory expansion table on server startup (or lazily on first query).

- **FR-2: Query expansion on vault_search.** Before executing the FTS query, check the expansion table. If the query contains an abbreviation or its full form, expand to both: `SCD` → `(SCD OR "slowly changing dimensions")`. The expanded query is passed to DuckDB FTS.

- **FR-3: Manual override file.** If `VAULT_PATH/synonyms.json` exists, merge its entries into the expansion table. Format:
  ```json
  {
    "SCD": "slowly changing dimensions",
    "ETL": "extract transform load",
    "SLA": "service level agreement"
  }
  ```
  Manual entries override auto-discovered ones on key collision.

- **FR-4: vault_synonyms tool.** Returns the current expansion table as a dict `{abbrev: full_form, ...}`. Agents can inspect what expansions are active.

- **FR-5: No vault modifications.** The auto-discovery reads existing pages. Manual definitions live in a standalone JSON file. No frontmatter schema changes, no page edits. This is a query-time feature only.

### Non-Functional Requirements

- **NFR-1**: Query expansion adds <10ms to vault_search latency (simple dict lookup + string concatenation).
- **NFR-2**: Auto-discovery re-scans on server restart (or lazily on first query). No persistent cache to invalidate.
- **NFR-3**: Zero new Python dependencies. Regex + dict lookups in stdlib.

## Scope

### In Scope

- Auto-discovery pattern matching for parenthetical definitions
- Query expansion: abbreviation → full form AND full form → abbreviation
- `synonyms.json` manual override file
- `vault_synonyms` MCP tool
- Expansion integrated into existing `vault_search` flow

### Out of Scope (v2)

- Frontmatter schema changes (no `aliases` field added to wiki pages)
- Writing synonyms back to pages (this is query-time only)
- Stemming or fuzzy matching (e.g., "dimension" matching "dimensional")
- Contextual disambiguation (if "SCD" means different things in different contexts)
- Automatic expansion table generation via LLM (manual overrides are human-curated)

## Approach

### Technical Approach

**Auto-discovery patterns to scan for:**

| Pattern | Example in vault | Extraction |
|---------|-----------------|------------|
| `ABBREV (Full Form)` | `SCD (slowly changing dimensions)` | abbrev=SCD, full="slowly changing dimensions" |
| `Full Form (ABBREV)` | `slowly changing dimensions (SCD)` | abbrev=SCD, full="slowly changing dimensions" |
| `**ABBREV** — Full Form` | `**SCD** — slowly changing dimensions` | abbrev=SCD, full="slowly changing dimensions" |

Implementation: a single regex function `discover_abbreviations(body: str) -> dict[str, str]` that extracts all patterns from a page body. Deduplicate across pages (lowercase keys).

**Query expansion logic in `vault_search`:**

```
query = "SCD"
expanded = expand_query(query, expansion_table)
# expanded = '(SCD OR "slowly changing dimensions")'

# Build FTS query with expanded terms
# DuckDB FTS: match_bm25 handles OR syntax in the query string
```

If the user searches for the full form ("slowly changing dimensions"), expand in the other direction to also include "SCD".

**`synonyms.json` location:** `{VAULT_PATH}/synonyms.json` — lives in the vault root, managed by the user.

### User Experience

```
> vault_search("SCD")
→ [
    { title: "Data Warehousing Concepts", snippet: "...slowly changing dimensions (SCD)...", ... },
    { title: "Jagged Frontier", snippet: "...SCD patterns in analytics...", ... },
  ]

> vault_synonyms()
→ {
    "SCD": "slowly changing dimensions",
    "ETL": "extract transform load",
    "SLA": "service level agreement",
    "API": "application programming interface"
  }
```

## Dependencies

### Prerequisites
- Existing vault pages containing parenthetical definitions (the vault already has these)

### External Dependencies
- None. Python stdlib regex only.

### Related Systems
- `src/duckbrain/indexer.py` — `search()` function receives the expanded query
- `src/duckbrain/scanner.py` — auto-discovery scans the same vault pages
- `src/duckbrain/tools/vault_search.py` — `handle_vault_search()` calls the expander before passing to indexer
- `synonyms.json` at vault root — optional manual override file

## Success Criteria

1. **SCD test**: `vault_search("SCD")` returns pages that only contain "slowly changing dimensions" (no literal "SCD" text).
2. **Reverse expansion**: `vault_search("slowly changing dimensions")` returns pages that only contain "SCD".
3. **Auto-discovery**: Pages with the pattern `SCD (slowly changing dimensions)` in their body automatically add an `SCD` → `slowly changing dimensions` entry to the expansion table.
4. **Manual override**: Adding `"SCD": "slowly changing dimension type"` to `synonyms.json` overrides the auto-discovered value.
5. **Performance**: Query expansion adds <10ms overhead to vault_search response time.
6. **synonyms.json optional**: If the file doesn't exist, auto-discovery still works. If auto-discovery finds nothing, queries pass through unchanged.

## Notes

- **Why not page-side tagging?** Adding `aliases` to frontmatter is a v2 option. It makes the knowledge persistent and part of the page schema, which is better long-term. But it requires: (a) frontmatter schema changes to `vault_write`, (b) agent retraining to include aliases, (c) migration of existing pages. Query-side expansion is zero-touch — it works on the existing vault immediately.
- **Case insensitivity**: Expansion keys are lowercased. Queries are lowercased before lookup. The expanded form preserves original casing from the source page.
- **Multi-word abbreviations**: Handled naturally — `"slowly changing dimensions"` is a phrase. DuckDB FTS handles quoted phrases.
- **Conflict resolution**: If two pages define "SCD" differently (e.g., "slowly changing dimensions" vs "source control database"), the first one wins. Manual overrides in `synonyms.json` take priority.
