# Plugin Versioning and `install-plugin` CLI — Implementation Tasks

## Overview

Three tightly coupled changes: stamp `plugin.json` with a version, warn at session start on version drift, and ship `duckbrain install-plugin` as the canonical fix path. Covers `plugin.json`, `vault-context.sh`, `src/duckbrain/install_plugin.py`, `src/duckbrain/cli.py`, and package bundling.

## Tasks

---

## SPRINT 1: Foundation

Static changes with no runtime logic. Both streams are parallel and independent.

---

### Stream A: `plugin.json` + sync script (`scripts/sync-plugin-version.py`)

- [x] Add `"version": "0.7.0"` field to `claude/.claude-plugin/plugin.json` (match current `pyproject.toml` version exactly)

- [x] Create `scripts/sync-plugin-version.py`:
  - Reads `version` from `pyproject.toml` using `tomllib` (stdlib, Python 3.11+) or `tomli` fallback
  - Writes `version` field into `claude/.claude-plugin/plugin.json` (preserves all other fields, pretty-prints JSON)
  - Usage: `python scripts/sync-plugin-version.py` — idempotent, exits 0

- [x] **Write failing test** `test_sync_sets_version_in_plugin_json` in `tests/test_sync_plugin_version.py`:
  ```python
  def test_sync_sets_version_in_plugin_json(tmp_path):
      # Create fake pyproject.toml and plugin.json in tmp_path
      # Run sync script against them via subprocess or direct import
      # Assert plugin.json["version"] matches pyproject.toml [project].version
  ```

- [x] **Run to verify failure**: `uv run pytest tests/test_sync_plugin_version.py::test_sync_sets_version_in_plugin_json -v` → expect FAIL (script doesn't exist)

- [x] **Write minimal implementation** in `scripts/sync-plugin-version.py` (as above)

- [x] **Run to verify pass**: `uv run pytest tests/test_sync_plugin_version.py::test_sync_sets_version_in_plugin_json -v` → PASS; then `uv run pytest` → all pass

- [x] Add `python scripts/sync-plugin-version.py` to `CONTRIBUTING.md` release checklist under "Before tagging a release"

- [x] **Commit**: `feat: add version field to plugin.json and sync-plugin-version.py script`

---

### Stream B: Bundle plugin files inside package (`src/duckbrain/plugin/`)

- [x] Create `src/duckbrain/plugin/` directory with `__init__.py` (empty, makes it a package so `importlib.resources` can locate it)

- [x] Create `src/duckbrain/plugin/claude/` and copy all files from `claude/` into it:
  - `plugin/claude/.claude-plugin/plugin.json`
  - `plugin/claude/.claude-plugin/marketplace.json`
  - `plugin/claude/hooks/hooks.json`
  - `plugin/claude/scripts/` (all scripts)
  - `plugin/claude/LEARNINGS.md`
  - Do NOT copy `.mcp.json` (local dev config, not plugin artifact)

- [x] Add `src/duckbrain/plugin/` to git and verify it is not in `.gitignore`

- [x] **Write failing test** `test_bundled_plugin_files_exist` in `tests/test_install_plugin.py`:
  ```python
  def test_bundled_plugin_files_exist():
      from importlib.resources import files
      plugin_dir = files("duckbrain").joinpath("plugin/claude")
      assert (plugin_dir / ".claude-plugin" / "plugin.json").is_file()
      assert (plugin_dir / "hooks" / "hooks.json").is_file()
  ```

- [x] **Run to verify failure**: `uv run pytest tests/test_install_plugin.py::test_bundled_plugin_files_exist -v` → expect FAIL (directory doesn't exist)

- [x] **Verify pass**: after creating the directory and files above, run `uv run pytest tests/test_install_plugin.py::test_bundled_plugin_files_exist -v` → PASS

- [x] **Commit**: `feat: bundle claude plugin files inside Python package`

---

## SPRINT 2: Core Logic (TDD)

⚠️ Stream A depends on SPRINT 1 — Stream B (bundled files must exist).
Stream B depends on SPRINT 2 — Stream A (`install_plugin.run()` must exist to import).

---

### Stream A: `src/duckbrain/install_plugin.py`

- [x] **Write failing tests** in `tests/test_install_plugin.py` (extend file from Sprint 1):

  ```python
  def test_detect_installed_editors_finds_claude_code(tmp_path):
      # Create fake claude-code plugin dir at tmp_path
      # Monkeypatch DEFAULT_EDITOR_PATHS["claude-code"] to tmp_path
      # Assert detect_installed_editors() returns [("claude-code", tmp_path)]

  def test_install_to_editor_copies_files(tmp_path):
      dest = tmp_path / "claude-plugins" / "duckbrain-local"
      install_to_editor("claude-code", dest)
      assert (dest / ".claude-plugin" / "plugin.json").exists()
      assert (dest / "hooks" / "hooks.json").exists()

  def test_install_to_editor_is_idempotent(tmp_path):
      dest = tmp_path / "claude-plugins" / "duckbrain-local"
      install_to_editor("claude-code", dest)
      install_to_editor("claude-code", dest)  # second call must not raise
      assert (dest / "hooks" / "hooks.json").exists()

  def test_install_to_editor_returns_post_install_step():
      step = get_post_install_step("claude-code")
      assert "claude plugin update" in step

  def test_install_to_unknown_editor_raises():
      with pytest.raises(ValueError, match="Unsupported editor"):
          install_to_editor("notepad", Path("/tmp/nowhere"))
  ```

- [x] **Run to verify failure**: `uv run pytest tests/test_install_plugin.py -v` → all new tests FAIL

- [x] **Write `src/duckbrain/install_plugin.py`**:
  - `EDITOR_REGISTRY`: dict mapping editor slug → `EditorTarget(default_path, post_install_step, status)`
  - `get_plugin_dir(editor: str) -> Path` using `importlib.resources.files("duckbrain").joinpath(f"plugin/{editor}")`
  - `detect_installed_editors() -> list[tuple[str, Path]]` — checks `EDITOR_REGISTRY` default paths, returns those that exist
  - `install_to_editor(editor: str, dest: Path, force: bool = False) -> None` — copies all files from bundled plugin dir to dest using `shutil.copytree(dirs_exist_ok=True)`; raises `ValueError` for unknown editor
  - `get_post_install_step(editor: str) -> str` — returns post-install instruction string
  - `run(argv: list[str] | None = None) -> None` — argparse entry: `--editor`, `--dest`, `--force`; auto-detect when no flags given; prints confirmation prompt; calls `install_to_editor`

  Editor registry (initial):
  ```python
  "claude-code": EditorTarget(
      default_path=Path.home() / ".local/share/claude-plugins/duckbrain-local",
      post_install_step="claude plugin update duckbrain@duckbrain-local",
      status="supported",
  )
  # opencode, cursor: status="tbd", printed as unsupported in output
  ```

- [x] **Run to verify pass**: `uv run pytest tests/test_install_plugin.py -v` → all PASS; `uv run pytest` → all pass

- [x] **Commit**: `feat: add install_plugin module with editor registry and install logic`

---

### Stream B: `src/duckbrain/cli.py` + `pyproject.toml` entry point

⚠️ Depends on: SPRINT 2 — Stream A — `install_plugin.run()` must be importable

- [x] **Write failing tests** in `tests/test_cli.py`:

  ```python
  def test_no_args_starts_mcp_server(monkeypatch):
      # monkeypatch duckbrain.server.main to a no-op
      # call cli.main([]) (or sys.argv = ["duckbrain"])
      # assert server.main was called

  def test_serve_subcommand_starts_mcp_server(monkeypatch):
      # monkeypatch duckbrain.server.main to a no-op
      # call cli.main(["serve"])
      # assert server.main was called

  def test_install_plugin_subcommand_calls_run(monkeypatch):
      # monkeypatch install_plugin.run to a no-op
      # call cli.main(["install-plugin", "--editor", "claude-code"])
      # assert install_plugin.run was called with ["install-plugin", "--editor", "claude-code"]
  ```

- [x] **Run to verify failure**: `uv run pytest tests/test_cli.py -v` → all FAIL (module doesn't exist)

- [x] **Write `src/duckbrain/cli.py`**:
  ```python
  import sys
  from duckbrain import server, install_plugin

  def main(argv: list[str] | None = None) -> None:
      args = argv if argv is not None else sys.argv[1:]
      if not args or args[0] == "serve":
          server.main()
      elif args[0] == "install-plugin":
          install_plugin.run(args)
      else:
          print(f"Unknown subcommand: {args[0]}", file=sys.stderr)
          sys.exit(1)
  ```

- [x] Update `pyproject.toml` entry point:
  ```toml
  [project.scripts]
  duckbrain = "duckbrain.cli:main"
  ```

- [x] **Run to verify pass**: `uv run pytest tests/test_cli.py -v` → all PASS; `uv run pytest` → all pass

- [x] Manually verify: `uv run duckbrain --help` still works (or returns the MCP server startup, not an error)

- [x] **Commit**: `feat: add cli.py dispatcher, update entry point to duckbrain.cli:main`

---

## SPRINT 3: Version-check + Integration

⚠️ Stream A has no code dependency on earlier sprints but the version-check is only meaningful after Sprint 1 Stream A (plugin.json has a version field).

---

### Stream A: `claude/scripts/vault-context.sh` version-check block

- [x] Insert version-check block at the top of `claude/scripts/vault-context.sh`, before the vault output section:

  ```bash
  # Version drift check — warn if plugin files are older than installed package
  _PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
  if command -v python3 &>/dev/null && [ -f "$_PLUGIN_JSON" ]; then
    _PLUGIN_VER=$(python3 -c "
  import json, sys
  try:
      print(json.load(open('$_PLUGIN_JSON')).get('version', ''))
  except Exception:
      sys.exit(0)
  " 2>/dev/null)
    _PKG_VER=$(python3 -c "
  import importlib.metadata, sys
  try:
      print(importlib.metadata.version('duckbrain'))
  except Exception:
      sys.exit(0)
  " 2>/dev/null)
    if [ -n "$_PLUGIN_VER" ] && [ -n "$_PKG_VER" ] && [ "$_PLUGIN_VER" != "$_PKG_VER" ]; then
      echo "⚠ duckbrain plugin (v${_PLUGIN_VER}) is out of sync with package (v${_PKG_VER}). Run: duckbrain install-plugin"
      echo ""
    fi
  fi
  ```

  Use `_`-prefixed local variables to avoid polluting the shell environment.

- [x] **Manual test — versions in sync**: temporarily set `PLUGIN_VERSION` equal to installed package version → no warning appears in Claude session context

- [x] **Manual test — versions out of sync**: temporarily edit `plugin.json` version to `"0.0.0"` → warning line appears at top of session context

- [x] **Manual test — duckbrain not installed**: run script in a venv without duckbrain → no error, no warning

- [x] Restore `plugin.json` version to `0.7.0` after manual tests

- [x] **Commit**: `feat: add version drift warning to vault-context.sh SessionStart hook`

---

### Stream B: Full integration test (`tests/test_install_plugin.py` extension)

⚠️ Depends on: all SPRINT 2 streams complete

- [x] **Write integration test** `test_full_install_flow_claude_code` in `tests/test_install_plugin.py`:

  ```python
  def test_full_install_flow_claude_code(tmp_path):
      """Install to a temp dir, verify all expected files are present and non-empty."""
      dest = tmp_path / "duckbrain-local"
      install_to_editor("claude-code", dest)
      # Verify key files
      assert (dest / ".claude-plugin" / "plugin.json").stat().st_size > 0
      assert (dest / "hooks" / "hooks.json").stat().st_size > 0
      # Verify plugin.json in dest has a version field
      import json
      data = json.loads((dest / ".claude-plugin" / "plugin.json").read_text())
      assert "version" in data
      assert data["version"] != "unknown"
  ```

- [x] **Run to verify pass**: `uv run pytest tests/test_install_plugin.py::test_full_install_flow_claude_code -v` → PASS

- [x] **Run full suite**: `uv run pytest` → all tests pass, no warnings

- [x] **Commit**: `test: add integration test for full claude-code install flow`

---

## Summary

### Sprint Overview

| Sprint | Name | Streams | Key outputs |
|--------|------|---------|-------------|
| 1 | Foundation | A, B | `plugin.json` has `version`, files bundled in package |
| 2 | Core Logic | A, B | `install_plugin.py`, `cli.py`, updated entry point |
| 3 | Integration | A, B | Version-check in `vault-context.sh`, integration tests green |

### Total Effort

- SPRINTS: 3
- STREAMS: 6 (2 per sprint)
- Tasks: ~30
- New files: `scripts/sync-plugin-version.py`, `src/duckbrain/plugin/claude/` (directory), `src/duckbrain/install_plugin.py`, `src/duckbrain/cli.py`, `tests/test_sync_plugin_version.py`, `tests/test_cli.py`
- Modified files: `claude/.claude-plugin/plugin.json`, `claude/scripts/vault-context.sh`, `pyproject.toml`, `CONTRIBUTING.md`, `tests/test_install_plugin.py`

## Notes

- `scripts/sync-plugin-version.py` must be run before every release tag — add to release checklist
- `src/duckbrain/plugin/claude/` must be kept in sync with `claude/` at release — same sync script or CI step
- `opencode` and `cursor` editor targets are intentionally stubs in `EDITOR_REGISTRY` (status="tbd") — `install-plugin` prints them as unsupported rather than silently ignoring them
- The `cli.py` dispatcher is thin by design — `install_plugin.py` owns its own argparse, so `cli.py` just routes `argv` through
- `shutil.copytree(dirs_exist_ok=True)` handles the idempotency requirement without custom logic

### Quality Standards

- No placeholders — every task produces fully functional output when checked
- TDD enforced — all runtime logic in Sprint 2 has failing test before implementation
- Idempotency verified by explicit test (`test_install_to_editor_is_idempotent`)
- `uv run pytest` must stay green after every commit
