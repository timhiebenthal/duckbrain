# Configurable Vault Structure — Implementation Tasks

## Overview

Introduce `duckbrain.config.json` — a vault-root config file that makes DuckBrain's
vault structure (page kinds, directories, frontmatter conventions) configurable.
Backward compatible: no config file = exact same behavior as today.

Vault config is **opt-in, manual, and documented**. Users write or copy a JSON file.
`vault_audit` is a diagnostic tool that shows raw vault structure to help users
design their config. No AI wizard — the config is human-edited.

---

## Tasks

## SPRINT 1: Foundation

Config module. No dependencies on other DuckBrain code. Lays the type system
the rest of the pipeline builds on.

### Stream A: config.py — types, loading, defaults

- [x] **Task 1.1: Write failing test** for `test_default_config_values` in `tests/test_config.py`
  - `VaultConfig()` with no args returns config matching current hardcoded behavior
  - 5 scan patterns: entity, concept, source, synthesis, daily
  - entity pattern: glob=`wiki/entities/*.md`, kind=`entity`, frontmatter on, kind_field=`item-type`
  - daily pattern: glob=`daily/*.md`, kind=`daily`, frontmatter off, dates from filename
  - write_rules contain `daily` with mode=append, update_index=False
  - write_default has mode=create, frontmatter on
- [ ] **Run to verify failure**: `uv run pytest tests/test_config.py::test_default_config_values -v` → FAIL
- [ ] **Write minimal implementation** in `src/duckbrain/config.py`
  - `DateSource` enum: `FRONTMATTER`, `FILENAME`, `MTIME`
  - `ScanPattern` dataclass: `glob`, `kind`, `frontmatter_enabled`, `kind_field`, `date_created`, `date_updated`, `created_field`, `updated_field`
  - `WriteRule` dataclass: `mode`, `directory_template`, `filename_template`, `frontmatter`, `frontmatter_fields`, `update_log`, `update_index`, `index_section`, `log_entry_format`, `excluded_tags`
  - `VaultConfig` dataclass: `version`, `scan_patterns`, `write_rules`, `write_default`, `config_path`
  - `_default_scan_patterns()` returns list matching current hardcoded `kind_to_dir` from `scanner.py`
  - `_default_write_rules()` returns dict matching current hardcoded `KIND_TO_SUBDIR`, `KIND_TO_SECTION`, and `_write_daily` behavior
  - Default `WriteRule.__post_init__` fills in `frontmatter_fields`, `index_section`, `log_entry_format`, `excluded_tags` matching current `writer.py` behavior
- [ ] **Run to verify pass**: `uv run pytest tests/test_config.py::test_default_config_values -v` → PASS; `uv run pytest` → all pass
- [ ] **Commit**: `feat: add VaultConfig types and defaults matching current hardcoded behavior`

- [x] **Task 1.2: Write failing test** for `test_load_config_from_file` in `tests/test_config.py`
  - Create `{tmp_path}/duckbrain.config.json` with a custom scan pattern (kind="project")
  - `load_vault_config(str(tmp_path))` returns `VaultConfig` with 1 pattern, kind="project"
  - `config.config_path` matches the file path
- [ ] **Run to verify failure**: `uv run pytest tests/test_config.py::test_load_config_from_file -v` → FAIL
- [ ] **Write minimal implementation**
  - `load_vault_config(vault_path: str) -> VaultConfig` reads `vault_path/duckbrain.config.json`
  - `_parse_config(raw: dict, config_path: str) -> VaultConfig` parses JSON into dataclasses
  - Maps `scan.patterns[].frontmatter.enabled/kind_field`, `dates.created/updated` → `DateSource` enum
  - Maps `write.rules.{kind}` and `write.default` → `WriteRule`
  - Falls back to defaults for missing optional fields
- [ ] **Run to verify pass**: `uv run pytest tests/test_config.py::test_load_config_from_file -v` → PASS; `uv run pytest` → all pass
- [ ] **Commit**: `feat: implement load_vault_config with JSON parsing`

- [x] **Task 1.3: Write failing test** for missing config returns defaults in `tests/test_config.py`
  - `test_missing_config_returns_defaults`: nonexistent path → returns `VaultConfig()` with defaults
  - `test_empty_vault_no_config`: empty temp dir → returns `VaultConfig()` with defaults
- [ ] **Run to verify failure**: `uv run pytest tests/test_config.py::test_missing_config_returns_defaults -v` → FAIL
- [ ] **Write minimal implementation**: `load_vault_config` checks `config_file.is_file()`, returns `VaultConfig()` if not found
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: load_vault_config falls back to defaults when no config file`

- [x] **Task 1.4: Write failing test** for config validation in `tests/test_config.py`
  - `test_invalid_json_returns_defaults_with_warning`: malformed JSON → returns `VaultConfig()`, logged warning
  - `test_unknown_date_source_fallback`: invalid date source string → logs warning, falls back to `FRONTMATTER`
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation**
  - Wrap `json.loads` in try/except `JSONDecodeError` → log warning, return defaults
  - `DateSource(value)` in try/except `ValueError` → log warning, use FRONTMATTER
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: handle invalid config gracefully with warning + defaults`

### Stream B: __init__.py — export config types

- [ ] **Task 1.5: Write failing test** for config imports in `tests/test_config.py`
  - `test_config_types_importable`: `from duckbrain.config import VaultConfig, ScanPattern, WriteRule, DateSource, load_vault_config` all resolve
- [ ] **Run to verify failure** (these don't exist in `__init__.py` yet)
- [ ] **Write minimal implementation**: add imports to `src/duckbrain/__init__.py`
  ```python
  from duckbrain.config import VaultConfig, ScanPattern, WriteRule, DateSource, load_vault_config
  ```
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: export config types from duckbrain package`

---

## SPRINT 2: Core Pipeline Refactor

Refactor scanner, writer, and indexer to accept `VaultConfig` and use it instead of
hardcoded constants. All three run in parallel — they depend on config types but not on
each other.

### Stream A: scanner.py — config-driven scanning

- [x] **Task 2.1: Write failing test** for scan with config in `tests/test_scanner.py`
  - `test_scan_with_config_patterns`: create vault with custom dir `wiki/projects/test.md` (has frontmatter with `item-type: project`), pass config with a `project` scan pattern → returns 1 page with `kind="project"`
  - `test_scan_no_config_unchanged`: `scan_vault(temp_vault)` without config arg returns same pages as today (all 5 existing kinds)
  - Both tests pass through `temp_vault` fixture
- [ ] **Run to verify failure**: `uv run pytest tests/test_scanner.py -v` → FAIL (at least the new ones)
- [ ] **Write minimal implementation** in `src/duckbrain/scanner.py`
  - `scan_vault(vault_path, config=None)` — new `config` param, defaults to `None`
  - When `config` is `None`: behavior identical to today (uses hardcoded `kind_to_dir`)
  - When `config` is `VaultConfig`: iterate `config.scan_patterns` instead of `kind_to_dir`
  - Each pattern drives its own glob, frontmatter parsing rules, date extraction, kind assignment
  - `_infer_kind_from_pattern(filepath, pattern)` — checks `item-type` field against pattern kind if frontmatter enabled
  - `_extract_dates(meta, pattern, filename_stem)` — resolves DateSource to actual created/updated values
  - Keep `scan_daily` as-is until writer is also refactored (but scanner reads it via patterns)
- [ ] **Run to verify pass**: `uv run pytest tests/test_scanner.py -v` → all pass (old + new); `uv run pytest` → all pass
- [ ] **Commit**: `feat: scan_vault accepts optional VaultConfig for dynamic scan patterns`

- [x] **Task 2.2: Write failing test** for custom date sources in `tests/test_scanner.py`
  - `test_scan_date_from_filename`: config pattern with `date_created=FILENAME`, files named `2026-01-15.md` → page.created="2026-01-15"
  - `test_scan_date_from_mtime`: config pattern with `date_created=MTIME` → page.created matches file mtime
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation**: handle `DateSource.FILENAME` (parse from stem, try `YYYY-MM-DD` regex), `DateSource.MTIME` (use `os.path.getmtime`)
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: support FILENAME and MTIME date sources in scanner`

### Stream B: writer.py — config-driven writing

- [ ] **Task 2.3: Write failing test** for write with config in `tests/test_writer.py`
  - `test_write_page_with_custom_config`: create vault with config that defines kind="project", write a project page → file created at `wiki/projects/{slug}.md`, index.md gets entry under `## Projects`
  - `test_write_page_no_config_unchanged`: `write_page(...)` without config creates same files/dirs as today
  - `test_write_page_append_mode`: config with mode="append" for kind="log" → appends to `wiki/log/{date}.md` instead of creating new file
- [ ] **Run to verify failure**: `uv run pytest tests/test_writer.py -v` → FAIL
- [ ] **Write minimal implementation** in `src/duckbrain/writer.py`
  - `write_page(vault_path, kind, title, content, tags, config=None)` — new `config` param
  - `TemplateResolver` class resolves `{kind}`, `{Kind}`, `{slug}`, `{title}`, `{date}`, `{tags}` in template strings
  - When `config is None`: behavior identical to today (`KIND_TO_SUBDIR`, `KIND_TO_SECTION`, `_write_daily` special case)
  - When `config is VaultConfig`:
    - Look up `kind` in `config.write_rules`; fall back to `config.write_default`
    - Use `directory_template` + `TemplateResolver`→ actual directory
    - Use `filename_template` + `TemplateResolver` → actual filename
    - If `mode="append"`: open file in append mode (generalized `_write_daily`)
    - If `frontmatter=True`: `generate_frontmatter()` uses `frontmatter_fields` templates
    - Use `update_log`, `update_index`, `index_section`, `log_entry_format` from rule
    - `excluded_tags` from rule, not hardcoded set
  - Remove `_write_daily` special-case branching — replaced by generic `mode="append"` logic
- [ ] **Run to verify pass**: all tests pass (old + new)
- [ ] **Commit**: `feat: write_page accepts optional VaultConfig for dynamic write rules`

- [ ] **Task 2.4: Write failing test** for template resolution in `tests/test_writer.py`
  - `test_template_resolve_kind`: `{kind}` → `"project"`, `{Kind}` → `"Project"`, `{kinds}` → `"projects"`
  - `test_template_resolve_slug`: `{slug}` → `"my-project"`, `{title}` → `"My Project"`
  - `test_template_resolve_date`: `{date}` → `"2026-05-30"` (or whatever today is)
  - `test_template_no_substitution`: string with no templates → returned unchanged
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** as `TemplateResolver.resolve(template: str, context: dict) -> str`
  - Replaces `{kind}`, `{Kind}`, `{kinds}` from context
  - Uses `slugify()` for `{slug}`, passes through `{title}`, formats `{date}`, joins `{tags}`
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: add TemplateResolver for config template variables`

- [ ] **Task 2.5: Write failing test** for config-driven frontmatter in `tests/test_writer.py`
  - `test_generate_frontmatter_custom_fields`: config rule with `frontmatter_fields={"title": "{title}", "status": "active"}`
  - `test_generate_frontmatter_no_frontmatter`: config rule with `frontmatter=false` → generates no frontmatter
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation**: `generate_frontmatter()` accepts optional `frontmatter_fields` dict, uses `TemplateResolver` to fill values
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: config-driven frontmatter field generation`

- [ ] **Task 2.5b: Write failing test** for config-aware tags index in `tests/test_writer.py`
  - `test_build_tags_index_with_config_scan_paths`: config with scan patterns for `wiki/projects/` and `wiki/notes/` → `build_tags_index` scans those dirs (not hardcoded subdirs)
  - `test_build_tags_index_with_config_excluded_tags`: config with `excluded_tags=["foo"]` → `build_tags_index` excludes "foo" from output
  - `test_build_tags_index_no_config_unchanged`: `build_tags_index(path)` without config scans same 4 dirs as today
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** in `src/duckbrain/writer.py`
  - `build_tags_index(vault_path, config=None)` — new `config` param
  - When `config is None`: behavior identical to today
  - When `config is VaultConfig`: iterate `config.scan_patterns` to get globs, derive directories, use per-kind `excluded_tags` (or `write_default.excluded_tags`)
  - Update `bootstrap_vault()` in `server.py` to pass config when available
  - Update `write_page()` call to `build_tags_index` to pass config
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: build_tags_index uses config scan paths and excluded_tags`

### Stream C: indexer.py — dynamic stats

- [ ] **Task 2.6: Write failing test** for dynamic stats in `tests/test_indexer.py`
  - `test_get_stats_with_config`: build index from pages with kinds found only in config, `get_stats(conn, config)` returns keys matching config kinds + `daily` + `available_tags` + `last_modified`
  - `test_get_stats_no_config_unchanged`: `get_stats(conn)` without config returns same 5 keys as today (`entity`, `concept`, `source`, `synthesis`, `daily`)
  - `test_get_stats_dynamic_keys`: config with only `["project", "note"]` kinds → stats keys are `project`, `note`, `available_tags`, `last_modified`
- [ ] **Run to verify failure**: `uv run pytest tests/test_indexer.py -v` → FAIL
- [ ] **Write minimal implementation** in `src/duckbrain/indexer.py`
  - `get_stats(conn, config=None)` — new `config` param
  - When `config is None`: exact same behavior as today (5 hardcoded kind keys)
  - When `config is VaultConfig`: query `SELECT kind, COUNT(*) FROM pages GROUP BY kind`, build dict dynamically, always include `available_tags` + `last_modified`
  - Config kinds that have 0 pages still appear in output (with count 0)
- [ ] **Run to verify pass**: all tests pass
- [ ] **Commit**: `feat: get_stats returns dynamic keys when VaultConfig is provided`

---

## SPRINT 3: Integration

Wire config through the server, update all tools, add vault_audit diagnostic, document format.

### Stream A: server.py — config plumbing

- [ ] **Task 3.1: Write failing test** for config loading at startup in `tests/test_server.py`
  - `test_load_config_at_startup`: server with config file in `temp_vault` → `get_vault_path()` returns it, config loaded
  - `test_no_config_starts_normally`: server without config file → no error, defaults used
- [ ] **Run to verify failure**: `uv run pytest tests/test_server.py -v` → FAIL
- [ ] **Write minimal implementation** in `src/duckbrain/server.py`
  - Import `load_vault_config`, `VaultConfig`
  - After `get_vault_path()`, call `load_vault_config(vault_path)` → store as module-level `_vault_config`
  - Pass `_vault_config` to all handler calls (or make it available via import)
  - `bootstrap_vault` passes `_vault_config` to `build_tags_index` when available
  - Add `get_vault_config()` helper (mirrors `get_vault_path()`)
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: server loads vault config at startup and exposes via get_vault_config()`

### Stream B: vault_search.py — config passthrough

- [ ] **Task 3.2: Write failing test** for config-aware search in `tests/test_vault_search.py`
  - `test_search_with_config_kind_filter`: index has pages with kinds "project" and "note", search with `kind="project"` → returns only project pages
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** in `src/duckbrain/tools/vault_search.py`
  - `handle_vault_search(vault_path, query, kind, tags, limit, config=None)` — new param
  - Pass `config` through to `scan_vault` (which already supports config via its own changes). `search()` doesn't need config — its SQL `kind` filter works against whatever kinds the scanner produced.
  - `server.py` passes `_vault_config` when calling
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: vault_search passes config through pipeline`

### Stream C: vault_write.py — kind validation

- [ ] **Task 3.3: Write failing test** in `tests/test_writer.py` (or `test_vault_write.py`)
  - `test_write_rejects_unknown_kind`: config defines kinds ["project", "note"], call `write_page(kind="foobar")` → returns warning about unknown kind
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** in `src/duckbrain/tools/vault_write.py`
  - `handle_vault_write(vault_path, kind, title, content, tags, config=None)` — new param
  - Validate `kind` against configured kinds when config is active
  - If unknown kind: add warning but still write (graceful degradation)
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: vault_write validates kind against config, warns on unknown`

### Stream D: vault_info.py — config status

- [ ] **Task 3.4: Write failing test** in `tests/test_vault_info.py`
  - `test_vault_info_reports_config_status`: with config file → returns includes `config_active=True`, `config_kinds=["project", "note"]`
  - `test_vault_info_no_config`: without config → returns `config_active=False`, `config_kinds=["entity", "concept", "source", "synthesis", "daily"]`
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** in `src/duckbrain/tools/vault_info.py`
  - `handle_vault_info(vault_path, config=None)` — new param
  - Merge config status into stats dict: `config_active: bool`, `config_file: str | None`, `config_kinds: list[str]`
  - `server.py` passes `_vault_config`
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: vault_info reports config status and active kinds`

### Stream E: vault_read.py — config-aware kind inference

- [ ] **Task 3.5: Write failing test** in `tests/test_vault_read.py`
  - `test_read_returns_correct_kind_from_config`: read a page from `wiki/projects/` with config defining kind="project" → returns `kind="project"` (not "wiki")
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** in `src/duckbrain/tools/vault_read.py`
  - `handle_vault_read(vault_path, title, filepath, config=None)` — new param
  - When `filepath` is given: scan `config.scan_patterns` to find matching glob → derive kind from pattern
  - Fall back current behavior (dir-based heuristic) when no config or no match
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: vault_read infers kind from config scan patterns`

### Stream F: vault_context.py — config-aware daily location

- [ ] **Task 3.6: Write failing test** in `tests/test_vault_context.py`
  - `test_context_with_config_no_dailies`: config has no daily pattern → `include_dailies=True` returns `today_daily=None, yesterday_daily=None` (no error)
  - `test_context_with_config_custom_daily_dir`: config has daily pattern with glob `journal/*.md` → reads from `journal/` instead of `daily/`
- [ ] **Run to verify failure**
- [ ] **Write minimal implementation** in `src/duckbrain/tools/vault_context.py`
  - `handle_vault_context(vault_path, keywords, include_dailies, include_search, search_limit, config=None)` — new param
  - `_read_daily` uses config'd daily pattern to find the daily directory
  - If no daily pattern exists in config, skip daily reading even if `include_dailies=True`
  - When config is `None`, use current hardcoded `daily/` directory
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: vault_context uses config for daily note location`

### Stream G: vault_audit.py — new diagnostic tool

- [ ] **Task 3.7: Write failing test** for `tests/test_vault_audit.py`
  - `test_vault_audit_standard_vault`: `temp_vault` fixture → detects `daily/` (date pattern), `wiki/entities/` (frontmatter, item-type=entity), 4 wiki subdirs, total 7 pages
  - `test_vault_audit_no_frontmatter`: directory with `.md` files but no frontmatter → pct_with_frontmatter=0, common_fields=[]
  - `test_vault_audit_unknown_dirs`: directory with files but no item-type → listed in `summary.unknown_dirs`
  - `test_vault_audit_custom_dates`: files with `YYYY-MM-DD` filenames → filename_pattern detected
  - `test_vault_audit_already_configured`: if `duckbrain.config.json` exists → `config_exists=true`
- [ ] **Run to verify failure**: `uv run pytest tests/test_vault_audit.py -v` → FAIL
- [ ] **Write minimal implementation** in `src/duckbrain/tools/vault_audit.py`
  - `handle_vault_audit(vault_path) -> dict` with:
    - `config_exists`: checks for `duckbrain.config.json`
    - `directories`: list of detected dirs, each with:
      - `path`, `file_count`
      - `filename_pattern`: `"YYYY-MM-DD.md"` if matches date regex, `"slug.md"` otherwise
      - `frontmatter.pct_with_frontmatter`, `frontmatter.common_fields` (top 5)
      - `item_type_values`: distinct values of `item-type` frontmatter field
      - `heuristic_kinds`: derived from dir name heuristics (parent `wiki/` + subdir name, or date filenames → daily)
    - `summary`: `total_pages`, `known_kinds` (from existing config or heuristics), `unknown_dirs`, `has_dailies`, `has_config`
  - Uses existing `parse_frontmatter()` from `scanner.py`
  - Uses `vault.glob("**/*.md")` to find all markdown files, groups by parent directory
  - Date detection: `re.match(r"^\d{4}-\d{2}-\d{2}", filename_stem)` for each file
  - Heuristics: dir name matches a known kind → that kind; files have date names → `["daily"]`; under `wiki/` → subdir name as heuristic kind
  - Register in `server.py` with `@server.tool()`:
    ```python
    @server.tool()
    def vault_audit() -> dict:
        """Audit vault structure: detect directories, frontmatter patterns,
        date conventions, and page kinds for config design."""
        return handle_vault_audit(vault_path)
    ```
- [ ] **Run to verify pass**: all pass
- [ ] **Commit**: `feat: add vault_audit diagnostic tool for vault structure discovery`

- [ ] **Commit**: `feat: add vault_audit diagnostic tool for vault structure discovery`

### Stream H: backward compat tests — complete regression suite

This stream runs **last, after all other Sprint 3 implementation is done**.
It proves the entire system is backward compatible — not just function-by-function
but through every combination the user hits.

- [ ] **Task 3.8: Write `tests/test_backward_compat.py`** with the following tests (all start red against the old codebase, then go green once changes are done):

  **`test_scan_vault_backward_compat`**:
  - `scan_vault(path)` returns same results as `scan_vault(path, config=None)` and `scan_vault(path, config=VaultConfig())`
  - Same count, same metadata (title, kind, tags, body, created, updated) for every page

  **`test_write_page_backward_compat`**:
  - `write_page(path, "entity", "T", "B", [], config=None)` produces same WriteResult and file contents as `write_page(path, "entity", "T", "B", [])`
  - Same for `config=VaultConfig()`

  **`test_get_stats_backward_compat`**:
  - `get_stats(conn)` matches `get_stats(conn, config=None)` exactly — same dict keys and values

  **`test_vault_info_backward_compat`**:
  - `handle_vault_info(path)` output contains all old keys (`entities`, `concepts`, `sources`, `synthesis`, `daily`) with matching values
  - New keys (`config_active`, `config_kinds`) present but don't affect old behavior

  **`test_search_backward_compat`**:
  - `handle_vault_search(path, "test")` returns same results as `handle_vault_search(path, "test", config=None)`

  **`test_vault_read_backward_compat`**:
  - `handle_vault_read(path, filepath="wiki/concepts/jagged-frontier.md")` with no config vs `config=None` vs `config=VaultConfig()` all return same kind/content/tags

  **`test_vault_context_backward_compat`**:
  - `handle_vault_context(path)` returns same dict as `handle_vault_context(path, config=None)`
  - Verifies `today_daily`, `yesterday_daily`, `search_results` all match

  **`test_write_read_roundtrip_backward_compat`**:
  - Integration: write a page with old API → read it with new API → content matches
  - Write with new API + default config → read with old API → content matches

  **`test_full_stack_custom_config`** (config-aware roundtrip):
  - Create temp vault with `duckbrain.config.json` defining kinds `project` and `note`
  - Create a markdown file with frontmatter `item-type: project` in `wiki/projects/`
  - `scan_vault(path, config)` → returns 1 page with `kind="project"`
  - `write_page(path, "note", "My Note", "body", [], config)` → creates `wiki/notes/my-note.md` with correct frontmatter
  - `handle_vault_read(path, filepath="wiki/notes/my-note.md", config)` → returns `kind="note"`
  - `handle_vault_search(path, "note", kind="note", config)` → returns 1 result
  - `build_tags_index(path, config)` → scans `wiki/projects/` and `wiki/notes/` only
  - `get_stats(conn, config)` → keys include `project` and `note`

- [ ] **Run to verify**: `uv run pytest tests/test_backward_compat.py -v` → first run may show pre-existing test structure, all should eventually PASS once all other streams are complete
- [ ] **Run full suite**: `uv run pytest` → 90+ tests all pass
- [ ] **Commit**: `test: add centralized backward compat regression suite`

### Stream I: README.md — config format documentation

- [ ] **Task 3.9**: Add a new `## Configuration` section to `README.md` with:
  - Purpose of config (adapt DuckBrain to any vault layout)
  - Config file location: `duckbrain.config.json` in vault root
  - Annotated example showing all fields (scan.patterns[].glob, .kind, .frontmatter, .dates; write.rules.{kind}.mode, .directory, .filename, .frontmatter_fields, .update_log, .update_index)
  - Template variables reference table (`{kind}`, `{Kind}`, `{slug}`, `{title}`, `{date}`, `{tags}`)
  - No config = defaults note
  - Link to JSON Schema (once published)
- [ ] **Run to verify**: `cat README.md` has the new section, reads clearly
- [ ] **Commit**: `docs: add vault config format reference to README`

### Stream J: example config file

- [ ] **Task 3.10**: Create `duckbrain.config.example.json` in repo root (not vault)
  - Annotated JSON with comments (using `//` — valid JSON5 or just descriptive example with `_comment` keys)
  - Shows the 5 standard kinds with all fields filled in
  - Includes a commented-out "project" override showing how to add a custom kind
- [ ] **Verify**: example parses correctly with a quick Python check: `json.loads(open("duckbrain.config.example.json").read())`
- [ ] **Commit**: `docs: add annotated example config file`

---

## Summary

### Sprint Overview

| Sprint | Name | Streams | Tasks |
|--------|------|---------|-------|
| 1 | Foundation | A (config.py), B (\_\_init\_\_.py) | 5 |
| 2 | Core Pipeline | A (scanner.py), B (writer.py), C (indexer.py) | 7 |
| 3 | Integration | A-J (server, tools, audit, backward compat, docs) | 10 |

### Total Effort

- **SPRINTS**: 3
- **STREAMS**: 14
- **Tasks**: 22 (including TDD sub-steps)
- **New files**: `config.py`, `vault_audit.py`, `test_config.py`, `test_vault_audit.py`, `test_backward_compat.py`, `duckbrain.config.example.json`
- **Modified files**: `__init__.py`, `scanner.py`, `writer.py`, `indexer.py`, `server.py`, 5 tool files, `README.md`, 3 existing test files

### Dependency Map

```
S1:A config.py ────────▶ S2:A scanner.py ──▶ S3:A server.py ──▶ S3:B-J tools + aud + compat + docs
S1:B __init__.py ───────▶ S2:B writer.py ───┘       │
                          S2:C indexer.py ────────────┘
```

- S2 streams (scanner, writer, indexer) are independent = parallel
- S3 streams (server, tools, audit, docs) depend on S1+S2 = parallel within sprint

### Key Design Decisions

- **Config is JSON, lives in vault root** — simple to validate, no YAML footguns
- **No config = defaults** — zero-change for existing users
- **`TemplateResolver`** centralizes `{kind}`, `{slug}`, `{date}` substitution — single source of truth
- **`vault_audit` is diagnostic only** — does not generate config, just shows structure for user reference
- **Graceful degradation** — unknown kinds get warnings, not errors; invalid JSON falls back to defaults
