# Configurable Vault Structure - Specification

## Overview

DuckBrain currently hardcodes a specific vault layout: five page kinds (`entity`, `concept`, `source`, `synthesis`, `daily`) with fixed directory mappings (`wiki/{entities,concepts,sources,synthesis}/`, `daily/`). This works for its original design but limits adoption — users with different Obsidian wiki structures can't adapt DuckBrain to match their vault.

This feature introduces a **vault config file** that lets users declare their vault's structure: which page kinds exist, where they live, which get frontmatter, how they're indexed. DuckBrain reads the config to adapt its scanning, writing, indexing, and tools dynamically.

The result: DuckBrain works with any Obsidian vault structure, not just the original template.

---

## Requirements

### Functional Requirements

- **FR-1**: Users can declare vault structure in a config file placed in the vault root
- **FR-2**: Config defines which page kinds exist (e.g. `["entity", "concept", "source"]` — or a completely different set)
- **FR-3**: For each kind, config defines:
  - Directory path (relative to vault root)
  - Whether pages get YAML frontmatter
  - Frontmatter field layout (which fields, default values)
  - Whether pages are written as new files or appended to existing files
  - Whether pages appear in `index.md`, `log.md`, `tags.md`
  - Section header name for `index.md`
  - How `created`/`updated` dates are determined (filename date, frontmatter field, filesystem mtime)
- **FR-4**: Config defines whether daily notes exist and their directory/format
- **FR-5**: Config defines which directories are scanned for indexing (glob patterns)
- **FR-6**: A `vault_audit` tool scans the vault and reports its current structure — directories, frontmatter patterns, date conventions, kinds present — as a diagnostic aid for users writing their config
- **FR-7**: Config format is documented in README so users can write/edit it manually without tool assistance
- **FR-8**: Existing vaults without a config file continue to work with current defaults
- **FR-9**: Invalid or missing config fields produce clear warnings and fall back to defaults

### Non-Functional Requirements

- **NFR-1 — Backward compat**: Zero config required. Old vaults, no file needed = same behavior as today.
- **NFR-2 — Validation**: Config errors are reported at startup with specific messages (file not found, bad kind reference, unknown field).
- **NFR-3 — Performance**: Config is read once at startup, not per-tool-call. No measurable perf impact.
- **NFR-4 — Simplicity**: Config file is a single JSON or YAML file. Flat structure, minimal required fields.
- **NFR-5 — Discoverability**: `vault_info` reports whether config is loaded and shows the active page kinds.
- **NFR-6 — Discoverability**: Config format reference lives in README so users can look it up without source-diving.

---

## Scope

### In Scope

- Config file format design (JSON schema)
- Config loading and validation module
- Scanner: dynamic directory scanning from config
- Writer: dynamic subdirectory/section/frontmatter mapping from config
- Indexer: dynamic stats keys from config
- Tools: `kind` parameter validation against config
- Server: load config at startup, pass through pipeline
- `vault_info`: report active config status
- `vault_audit` tool: diagnostic scanner that reports vault structure to help users design their config
- Config format reference in README (JSON Schema + annotated example)
- Backward compatibility layer (defaults match current hardcoded behavior)
- Tests: config loading, validation, full stack with custom config

### Out of Scope

- Runtime config reload (restart to pick up changes)
- Config-driven UI or admin panel
- Multi-vault support (one vault per server instance)
- Migration tools for existing vaults to add config
- AI-driven config generation (config is human-written or human-copied from examples)
- Obsidian plugin integration (config is for MCP server, not Obsidian itself)
- Custom per-user frontmatter field validation rules (beyond field name mapping)
- Config-driven body parsing (extracting structured data from body beyond frontmatter)
- Template-driven page creation (config drives layout but not content templates)

---

## Approach

### Technical Approach

#### Phase 1: Config file design and loading

A JSON file `duckbrain.config.json` in the vault root:

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/schemas/vault-config.json",
  "version": 1,

  "scan": {
    // Glob patterns for vault pages. Each pattern defines a known page kind
    // and how its metadata is extracted.
    "patterns": [
      {
        "glob": "wiki/entities/*.md",
        "kind": "entity",
        "frontmatter": {
          "enabled": true,
          "kind_field": "item-type"    // frontmatter key that indicates kind
        },
        "dates": {
          "created": "frontmatter:created",   // source:field | filename | mtime
          "updated": "frontmatter:updated"
        }
      },
      {
        "glob": "wiki/concepts/*.md",
        "kind": "concept",
        "frontmatter": { "enabled": true, "kind_field": "item-type" },
        "dates": { "created": "frontmatter:created", "updated": "frontmatter:updated" }
      },
      {
        "glob": "wiki/sources/*.md",
        "kind": "source",
        "frontmatter": { "enabled": true, "kind_field": "item-type" },
        "dates": { "created": "frontmatter:created", "updated": "frontmatter:updated" }
      },
      {
        "glob": "wiki/synthesis/*.md",
        "kind": "synthesis",
        "frontmatter": { "enabled": true, "kind_field": "item-type" },
        "dates": { "created": "frontmatter:created", "updated": "frontmatter:updated" }
      },
      {
        "glob": "daily/*.md",
        "kind": "daily",
        "frontmatter": { "enabled": false },
        "dates": { "created": "filename", "updated": "filename" }
      }
    ]
  },

  "write": {
    // Per-kind writing rules
    "rules": {
      "daily": {
        "mode": "append",
        "directory": "daily/",
        "filename": "{date}.md",       // {date} = today ISO, {title} = slugified title
        "frontmatter": false,
        "update_log": true,
        "update_index": false,
        "log_entry_format": "## [{date}] daily | {title}\n- Added to daily note: {title}\n"
      }
    },
    // Default write rules (applied to kinds not explicitly listed)
    "default": {
      "mode": "create",               // create = new file, append = add to existing
      "directory": "wiki/{kind}s/",    // {kind} = kind name, {kinds} = pluralized
      "filename": "{slug}.md",
      "frontmatter": true,
      "frontmatter_fields": {
        "title": "{title}",
        "item-type": "{kind}",
        "tags": "{tags}",
        "created": "{date}",
        "updated": "{date}"
      },
      "update_log": true,
      "update_index": true,
      "index_section": "{Kind}",       // capitalized kind name
      "log_entry_format": "## [{date}] ingest | {title}\n- Created {kind}: {title}\n",
      "excluded_tags": ["source", "concept", "entity", "synthesis", "clippings"]
    }
  }
}
```

When no config file exists, DuckBrain uses **built-in defaults** that match current behavior exactly.

#### Phase 2: Config module (`src/duckbrain/config.py`)

New module with:
- `load_vault_config(vault_path) -> VaultConfig` — loads and validates config
- `VaultConfig` dataclass — parsed config with defaults applied
- Validation: required fields, directory existence warnings, unknown kind references
- Returns defaults when no config file found (with a debug log)

```python
@dataclass
class VaultConfig:
    version: int
    scan_patterns: list[ScanPattern]
    write_rules: dict[str, WriteRule]
    write_default: WriteRule
    config_path: str | None  # None when using defaults (no config file found)

@dataclass
class ScanPattern:
    glob: str
    kind: str
    frontmatter_enabled: bool
    kind_field: str | None       # None if frontmatter disabled
    date_created: DateSource     # enum: FRONTMATTER, FILENAME, MTIME
    date_updated: DateSource     # enum: FRONTMATTER, FILENAME, MTIME
    created_field: str           # e.g. "created"
    updated_field: str           # e.g. "updated"

@dataclass
class WriteRule:
    mode: Literal["create", "append"]
    directory_template: str          # e.g. "wiki/{kind}s/"
    filename_template: str           # e.g. "{slug}.md" or "{date}.md"
    frontmatter: bool
    frontmatter_fields: dict[str, str] | None  # template → field mapping
    update_log: bool
    update_index: bool
    index_section: str | None
    log_entry_format: str | None
    excluded_tags: list[str] | None
```

#### Phase 3: Scanner changes (`src/duckbrain/scanner.py`)

Current:
```python
kind_to_dir = {"entity": "entities", ...}
glob_pattern = f"wiki/{subdir}/*.md"
```

New:
- `scan_vault(vault_path, config=None)` — accepts optional `VaultConfig`
- Iterates `config.scan_patterns` instead of fixed `kind_to_dir`
- Each pattern knows whether frontmatter exists, where `kind` is stored, how dates work
- `scan_daily(vault_path)` becomes a pattern like any other — no special-casing at scanner level
- Backward compat: when `config is None`, use built-in defaults matching today's behavior

#### Phase 4: Writer changes (`src/duckbrain/writer.py`)

Current:
```python
KIND_TO_SUBDIR = {"entity": "entities", ...}
KIND_TO_SECTION = {"entity": "Entities", ...}
if kind == "daily": return _write_daily(...)
```

New:
- `write_page(vault_path, kind, title, content, tags, config=None)` — accepts optional config
- Looks up `kind` in `config.write_rules` to determine mode (create/append), directory, filename
- `_write_daily()` generalizes to handle any `mode="append"` kind
- `generate_frontmatter()` uses `frontmatter_fields` template from config
- Index/log/tags updates skip for kinds with `update_index=False` / `update_log=False`
- `excluded_tags` per-kind instead of global hardcoded set
- Backward compat: when `config is None`, use built-in defaults

#### Phase 5: Indexer changes (`src/duckbrain/indexer.py`)

Current:
```python
kind_counts = {"entity": 0, "concept": 0, ...}
```

New:
- `get_stats(conn, config=None)` — returns dynamic keys based on configured kinds
- Instead of fixed dict keys, count by whatever kinds exist in the index
- Add `config.active: bool` and `config.kinds: list[str]` to stats output

#### Phase 6: Vault audit tool (`src/duckbrain/tools/vault_audit.py`)

New MCP tool that scans the vault structure and returns enough signal for the AI to infer the correct config:

```python
@server.tool()
def vault_audit() -> dict:
    """Audit vault structure: detects directories, frontmatter patterns,
    date conventions, and page kinds for AI-assisted config generation."""
```

**What it detects:**

- **All `.md` directories** at depth 1-3 from vault root, with file counts (e.g. `daily/` has 42 files, `wiki/entities/` has 15)
- **Frontmatter presence**: what % of files in each directory have YAML frontmatter, and what fields they commonly use (top 5)
- **Date patterns**: whether filenames match `YYYY-MM-DD` patterns (per directory), what date fields appear in frontmatter
- **`item-type` field**: detection of the DuckBrain convention — if `item-type` is set, what values are used
- **Directory purpose heuristics**: directories with `YYYY-MM-DD` filenames → likely daily notes; directories under `wiki/` → likely page collections
- **Existing config**: whether `duckbrain.config.json` already exists (no need to run audit if it does)

**Return format:**

```jsonc
{
  "config_exists": false,
  "directories": [
    {
      "path": "daily/",
      "file_count": 42,
      "filename_pattern": "YYYY-MM-DD.md",    // detected
      "frontmatter": {
        "pct_with_frontmatter": 0,
        "common_fields": []
      },
      "heuristic_kinds": ["daily"]
    },
    {
      "path": "wiki/entities/",
      "file_count": 15,
      "filename_pattern": "slug.md",
      "frontmatter": {
        "pct_with_frontmatter": 100,
        "common_fields": ["title", "item-type", "tags", "created", "updated"]
      },
      "item_type_values": ["entity"],
      "heuristic_kinds": ["entity"]
    },
    {
      "path": "wiki/projects/",
      "file_count": 8,
      "filename_pattern": "slug.md",
      "frontmatter": {
        "pct_with_frontmatter": 100,
        "common_fields": ["title", "tags", "status"]
      },
      "item_type_values": [],   // no item-type field — novel structure
      "heuristic_kinds": []
    }
  ],
  "summary": {
    "total_pages": 65,
    "known_kinds": ["entity", "concept", "source", "synthesis"],
    "unknown_dirs": ["wiki/projects/", "wiki/people/"],
    "has_dailies": true,
    "has_config": false
  }
}
```

The AI receives this output, spots `unknown_dirs`, asks the user about them, then generates the config.

#### Phase 7: Tool and server changes

- `server.py`: Load config at startup, pass through to all handlers. Register `vault_audit` tool.
- Tools: Validate `kind` parameter against configured kinds when config is active
- `vault_info`: Include config status, active kinds
- `vault_context`: Use config to locate daily notes (or skip if no daily kind)

### User Experience

**With config**: User writes `duckbrain.config.json` (or copies from example), places it in vault root. All DuckBrain tools adapt to the declared structure. `vault_info` shows "Config: active (5 kinds)".

**Without config**: Zero-change. Everything works exactly as today. `vault_info` shows "Config: none (defaults)".

**Configuration is opt-in.** Most users with standard vault layouts never need it. Users with custom layouts write the config once, then forget about it.

**Diagnostic tool**: If a user isn't sure what their vault looks like from DuckBrain's perspective, `vault_audit()` shows the raw structure — useful when designing a config or debugging unexpected behavior.

### File Changes Summary

| File | Change |
|---|---|
| `src/duckbrain/config.py` | **New** — VaultConfig dataclass, loading, validation, defaults |
| `src/duckbrain/__init__.py` | Add `VaultConfig` to public API (or keep internal) |
| `src/duckbrain/scanner.py` | Accept `config`, use `scan_patterns` instead of hardcoded globs |
| `src/duckbrain/writer.py` | Accept `config`, use `write_rules` instead of hardcoded maps |
| `src/duckbrain/indexer.py` | Accept `config`, dynamic stats keys |
| `src/duckbrain/server.py` | Load config at startup, pass to all tools |
| `src/duckbrain/tools/vault_search.py` | Accept `config` param (pass-through from server) |
| `src/duckbrain/tools/vault_write.py` | Validate kind against config |
| `src/duckbrain/tools/vault_info.py` | Include config status in output |
| `src/duckbrain/tools/vault_read.py` | Config-aware kind inference |
| `src/duckbrain/tools/vault_context.py` | Config-aware daily location |
| `src/duckbrain/tools/vault_audit.py` | **New** — diagnostic vault structure scanner |
| `tests/test_config.py` | **New** — config loading, validation, integration tests |
| `tests/test_vault_audit.py` | **New** — audit accuracy tests |
| `README.md` | Add config format reference section |
| `tests/test_scanner.py` | Test with custom config patterns |
| `tests/test_writer.py` | Test with custom write rules |
| `tests/test_indexer.py` | Test dynamic stats with custom kinds |
| `.env.example` | No change needed (config lives in vault, not env) |

---

## Dependencies

- **Prerequisites**: None. This is pure DuckBrain — no new libraries.
- **External**: None beyond existing `duckdb`, `pyyaml`, `python-dotenv`.
- **Related systems**: OpenCode AGENTS.md and LEARNINGS.md reference current kind names — will need doc updates but no code changes.

---

## Success Criteria

1. All existing tests pass without modification (backward compat)
2. A vault with `duckbrain.config.json` (custom kinds, dirs) scans correctly
3. Writing to custom kinds creates files in the configured directories
4. `vault_info` reports config status and dynamic kind counts
5. `vault_search(kind="my_custom_kind")` filters correctly
6. Missing config file = exact same behavior as before
7. Invalid config fields produce clear error messages
8. Config with `daily: false` (or no daily pattern) makes `vault_context` skip daily notes

---

## Notes

### Template Variables

Config fields like `directory`, `filename`, `frontmatter_fields`, and `log_entry_format` support variable substitution:

| Variable | Resolves to |
|---|---|
| `{kind}` | Page kind string (e.g. `"entity"`, `"concept"`) |
| `{Kind}` | Capitalized kind (e.g. `"Entity"`, `"Concept"`) |
| `{kinds}` | Kind with `s` appended (e.g. `"entities"`, `"concepts"`) |
| `{slug}` | Slugified title (e.g. `"my-page-title"`) |
| `{title}` | Original page title |
| `{date}` | Today's date in ISO format (`YYYY-MM-DD`) |
| `{tags}` | Comma-separated tag list |

These are resolved at write time from the current operation context.

### Design Rationale

- **JSON over YAML**: Simpler to validate, no YAML footguns (tab indentation, implicit types), can ship a JSON Schema. YAML readers are already a dep, so YAML could be supported too if desired.
- **Config in vault root, not env**: The config describes the vault structure, not the server. It belongs with the data.
- **Template strings** (`{kind}`, `{slug}`, `{date}`) avoid a complex nested config structure. Simple, readable, composable.
- **Default write rule** keeps per-kind config concise — users only override what's different.

### Risk: Config surface area

The config file introduces 15+ configurable fields. Each one is a potential support issue. Mitigation: sensible defaults, JSON Schema for IDE autocomplete, validation errors pointing to docs.

### Risk: Maintenance burden

Every new tool needs to be config-aware. Mitigation: central config object passed through the pipeline — no scattered config lookups.

### Risk: Scan/write misalignment

If a scan pattern adds a kind like `"note"` but no matching write rule exists, it falls to `write_default` which may guess wrong (`wiki/notes/` via `{kind}s`). Mitigation: config validation at startup checks that every scanned kind has either an explicit write rule or a default that produces a reasonable path. Warning logged if not.

### Risk: Scan/write field contract break

ScanPattern declares how dates are extracted (e.g. `date_created: FRONTMATTER:"created"`). WriteRule declares what frontmatter fields are written (e.g. `frontmatter_fields: {"title": "{title}", "item-type": "{kind}"}`). If the writer doesn't include the fields the scanner expects, DuckBrain-written pages won't re-scan their metadata correctly. Mitigation: config option in Open Questions; in the short term, example config and docs must show consistent field sets.

### Risk: Over-generalization

Some users may never use this. Mitigation: it's opt-in. Zero overhead when not used. The refactoring also makes the codebase cleaner (no scattered hardcoded constants).

### Open Questions

1. **Migration path**: If a user's vault structure is incompatible with defaults, do they need to write the full config from scratch, or can they inherit defaults and override selectively?
   → **Suggested**: Full config with JSON Schema defaults annotated. JSON Schema `default` keyword lets validators fill in blanks. Provide a commented example file they can copy and edit.

2. **Config location**: Vault root vs `wiki/` subdirectory vs environment variable?
   → **Suggested**: Vault root. It's a vault-wide concern, not wiki-specific. Environment variable could override the path to an external config file.

3. **Pluralization**: The `{kind}s` pattern assumes English pluralization (append `s`). For kinds ending in `y` (e.g. `category` → `categories`) this breaks.
   → **Suggested**: Explicit `directory` template per kind. `{kind}s` is a convenience for simple cases only.

4. **Config versioning**: If config format evolves, how do we handle old configs?
   → **Suggested**: `version` field in config. Server warns on unknown version but tries to interpret with current defaults for missing fields.
