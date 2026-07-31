# Plugin Versioning and `install-plugin` CLI — Specification

## Overview

Claude Code plugin files (`hooks/`, `scripts/`, `plugin.json`) are installed once and never auto-updated. When the Python package is upgraded via `pip install -U duckbrain`, the plugin files stay at the old version silently. Users have no way to detect the drift, and `plugin.json` carries no `version` field today (registered as `"unknown"` in the Claude plugin registry).

This spec covers three tightly coupled changes: stamping `plugin.json` with a version, warning at session start when versions diverge, and shipping a `duckbrain install-plugin` subcommand as the canonical fix path the warning points to.

## Requirements

### Functional Requirements

- **FR1** `plugin.json` carries a `version` field that matches the Python package version exactly (1:1, same release)
- **FR2** On session start, `vault-context.sh` compares the installed plugin version against the running package version and emits a one-line warning if they diverge
- **FR3** The warning text ends with `Run: duckbrain install-plugin` so the user knows the fix path without consulting docs
- **FR4** `duckbrain install-plugin` copies the bundled plugin files from the installed package onto disk, targeting the correct location for the chosen editor
- **FR5** The command supports `--editor` (explicit target) and `--dest` (generic fallback path)
- **FR6** Without `--editor` or `--dest`, the command auto-detects which editors have a duckbrain plugin installed and prompts the user to confirm before overwriting
- **FR7** After a successful install, the command prints the post-install step the user must run (e.g., `claude plugin update duckbrain@duckbrain-local`)
- **FR8** Plugin files for each editor are bundled inside the Python package under `src/duckbrain/plugin/<editor>/`

### Non-Functional Requirements

- **NFR1** The version check must not break the session start on any setup where `duckbrain` is not installed — the check is skipped silently if the package is unavailable
- **NFR2** The version check must not add measurable latency to session start (`importlib.metadata` is a stdlib in-process call, not a subprocess)
- **NFR3** `install-plugin` must be idempotent — running it twice leaves the destination in the same state as running it once
- **NFR4** `install-plugin` must not overwrite user-modified files without warning — detect and surface diffs before clobbering
- **NFR5** The `version` field in `plugin.json` must be set automatically at build time (not manually), so it can never drift from `pyproject.toml`

## Scope

### In Scope

- Add `version` field to `claude/.claude-plugin/plugin.json`
- Automate setting `plugin.json` version from `pyproject.toml` at build/release time (via a script or build hook)
- Add version-check block to `claude/scripts/vault-context.sh`
- Create `src/duckbrain/plugin/claude/` directory with all Claude Code plugin files (copied from `claude/` at release)
- Add `duckbrain install-plugin` subcommand to `src/duckbrain/server.py` (or a dedicated `cli.py`)
- Update `pyproject.toml` entry point and package data to include the bundled plugin files
- Support `--editor claude-code` and `--dest <path>` flags
- Print post-install steps per editor

### Out of Scope

- Auto-update on `pip install` (hook would require pip plugin machinery — too invasive)
- Plugin support for `opencode` and `cursor` in the `install-plugin` command — `claude-code` is the first target; others are scaffolded as stubs with `TBD` status
- Rollback / uninstall subcommand — not needed for the first version
- Checksum verification of bundled plugin files — overkill at this scale
- Automatic version bump tooling beyond what is needed to keep `plugin.json` in sync

## Approach

### Technical Approach

#### 1. `plugin.json` versioning

Add a `version` field to `claude/.claude-plugin/plugin.json`:

```json
{
  "name": "duckbrain",
  "version": "0.7.0",
  "displayName": "DuckBrain",
  ...
}
```

The version must stay in sync with `pyproject.toml`. Enforce this via a `scripts/sync-plugin-version.py` helper that reads `pyproject.toml` and writes the version into `plugin.json`. Run this script as part of the release process (added to `CONTRIBUTING.md` release checklist or wired into a `Makefile` / `just` recipe).

#### 2. Version-check in `vault-context.sh`

Insert a version-check block near the top of `claude/scripts/vault-context.sh`, before the vault output:

```bash
# Version drift check
PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
if command -v python3 &>/dev/null && [ -f "$PLUGIN_JSON" ]; then
  PLUGIN_VER=$(python3 -c "
import json, sys
try:
    print(json.load(open('$PLUGIN_JSON')).get('version',''))
except Exception:
    sys.exit(0)
" 2>/dev/null)
  PKG_VER=$(python3 -c "
import importlib.metadata, sys
try:
    print(importlib.metadata.version('duckbrain'))
except Exception:
    sys.exit(0)
" 2>/dev/null)
  if [ -n "$PLUGIN_VER" ] && [ -n "$PKG_VER" ] && [ "$PLUGIN_VER" != "$PKG_VER" ]; then
    echo "⚠ duckbrain plugin (v${PLUGIN_VER}) is out of sync with package (v${PKG_VER}). Run: duckbrain install-plugin"
    echo ""
  fi
fi
```

Using `importlib.metadata` instead of `pip show` avoids subprocess overhead and works in any Python environment where duckbrain is installed.

#### 3. Bundling plugin files inside the package

Create a directory `src/duckbrain/plugin/claude/` and populate it by copying the contents of `claude/` at release time (same sync script or CI step). Include the directory in the package via `pyproject.toml`:

```toml
[tool.uv.build-system]
# uv_build includes all files under src/ by default;
# ensure plugin/ is not gitignored
```

Add an `__init__.py`-free marker so uv picks up the directory. Use `importlib.resources` (Python 3.9+) or `importlib.files` (3.9+) to locate the bundled files at runtime:

```python
from importlib.resources import files

def get_plugin_dir(editor: str) -> Path:
    return Path(str(files("duckbrain").joinpath(f"plugin/{editor}")))
```

#### 4. `duckbrain install-plugin` CLI subcommand

Extend `server.py` (or extract to `cli.py`) with argparse subcommands:

```
duckbrain                        → existing MCP server (default)
duckbrain serve                  → explicit alias for MCP server
duckbrain install-plugin         → auto-detect + prompt
duckbrain install-plugin --editor claude-code
duckbrain install-plugin --dest /path/to/target/
```

**Auto-detect logic (no flags):**

1. Check known editor default paths for each supported editor
2. If a duckbrain plugin directory exists at that path, add it to the candidate list
3. Print candidates with current vs bundled version
4. Prompt: `Install to <path>? [y/N]`
5. On confirmation, copy bundled files, print post-install step

**Editor registry (extensible dict/dataclass):**

| Editor | Default path | Post-install step |
|---|---|---|
| `claude-code` | `~/.local/share/claude-plugins/duckbrain-local/` | `claude plugin update duckbrain@duckbrain-local` |
| `opencode` | TBD | TBD |
| `cursor` | TBD | TBD |

**Overwrite guard:** Before copying, check if any destination file differs from the bundled version. If diffs exist, print a summary and ask for confirmation (or accept `--force` to skip).

**Implementation module:** `src/duckbrain/install_plugin.py` — keeps `server.py` focused on MCP server concerns.

#### 5. Entry point wiring

Update `pyproject.toml` to point the CLI at the new dispatcher:

```toml
[project.scripts]
duckbrain = "duckbrain.cli:main"
```

Where `cli.py` dispatches to `server.main()` or `install_plugin.run()` based on argv.

### User Experience

**Normal session (versions in sync):** Nothing visible. The version check runs and exits silently.

**After `pip install -U duckbrain` (versions out of sync):**
```
⚠ duckbrain plugin (v0.7.0) is out of sync with package (v0.8.0). Run: duckbrain install-plugin
```

**Running `duckbrain install-plugin`:**
```
Detected duckbrain plugin installations:
  claude-code  ~/.local/share/claude-plugins/duckbrain-local/  (v0.7.0 → v0.8.0)

Install? [y/N] y
✓ Copied plugin files to ~/.local/share/claude-plugins/duckbrain-local/
  Next step: claude plugin update duckbrain@duckbrain-local
```

## Dependencies

- **`importlib.metadata`** — stdlib (Python 3.8+), no new dependency
- **`importlib.resources` / `importlib.files`** — stdlib (Python 3.9+), no new dependency; minimum Python version in `pyproject.toml` is already 3.10
- **`scripts/sync-plugin-version.py`** — new helper script, pure Python, no deps
- **`src/duckbrain/plugin/claude/`** — new directory; must be kept in sync with `claude/` at release. Sync is a file copy, no special tooling
- **`src/duckbrain/install_plugin.py`** — new module, stdlib only (`shutil`, `pathlib`, `importlib.resources`)
- **`src/duckbrain/cli.py`** — new module, replaces direct `server:main` entry point; thin dispatcher

## Success Criteria

1. `claude/.claude-plugin/plugin.json` contains `"version": "<current-package-version>"`
2. `scripts/sync-plugin-version.py` sets `plugin.json` version from `pyproject.toml` and is idempotent
3. Session start with matching versions: no warning emitted
4. Session start with mismatched versions: warning line appears in Claude context, ends with `Run: duckbrain install-plugin`
5. Session start when duckbrain is not installed (e.g., bare system): no error, no crash
6. `duckbrain install-plugin --editor claude-code` copies all plugin files to `~/.local/share/claude-plugins/duckbrain-local/` and prints the `claude plugin update` step
7. Running install twice produces the same result (idempotent)
8. `duckbrain` with no subcommand still starts the MCP server (no regression)
9. Plugin files are present under `src/duckbrain/plugin/claude/` in the installed package (verify with `python -c "from importlib.resources import files; print(list(files('duckbrain').joinpath('plugin/claude').iterdir()))"`)

## Notes

- **Why 1:1 versioning?** Plugin files only ship with package releases (same repo). There is no scenario where the plugin version could legitimately diverge from the package version. 1:1 keeps the release process simple and the check unambiguous.
- **Why `importlib.metadata` over `pip show`?** `pip show` spawns a subprocess, adds ~200ms, and may not be on PATH in all environments. `importlib.metadata` is in-process, instant, and works in any Python environment where the package is installed.
- **Why a separate `install_plugin.py` module?** `server.py` is already doing two things (MCP setup and bootstrapping). The install subcommand involves file I/O, user prompts, and editor-specific knowledge — better isolated.
- **Sync script vs build hook:** A `sync-plugin-version.py` script called manually (and in CI) is simpler than a `uv_build` plugin hook. The risk of forgetting is mitigated by adding it to the release checklist and CI.
- **`opencode` and `cursor` stubs:** The editor registry should include entries for these with `path=None` and `status="tbd"` so `install-plugin` prints them as unsupported rather than silently ignoring them — sets expectation for contributors.
- **Origin of this feature:** Discovered after session-end spam caused by stale local plugin files; `SessionEnd` hook removal fix was never propagated from the repo to the installed plugin. This entire class of bug is prevented by keeping versions in sync.
