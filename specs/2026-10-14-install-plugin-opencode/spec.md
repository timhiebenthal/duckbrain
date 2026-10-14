# install-plugin for OpenCode — Specification

## Overview

`duckbrain install-plugin` copies bundled editor plugin files from the installed package onto disk (see `specs/2026-06-16-plugin-versioning-install-cli/`). That spec shipped `claude-code` as the only supported editor; `opencode` was scaffolded as a stub with `status="tbd"`, so the CLI refuses to run for it.

Meanwhile the OpenCode plugin files live only at the repo root (`opencode/plugins/`) and are delivered by `curl`-ing raw GitHub files (see the root README). Users who `uv tool install duckbrain` get the Claude bundle but not the OpenCode one.

This spec bundles the OpenCode plugin inside the package and enables the CLI for it.

## Requirements

- **FR1** OpenCode plugin files are bundled inside the package at `src/duckbrain/plugin/opencode/`
- **FR2** `EDITOR_REGISTRY["opencode"].status` is `supported`; `bundle_name` is `opencode`
- **FR3** The default destination is `~/.config/opencode/plugins` (OpenCode's global discovery dir)
- **FR4** `duckbrain install-plugin --editor opencode` copies the bundled files and prints the post-install step (`bun install`, then restart OpenCode)
- **FR5** Editor auto-detection requires a marker file, not just directory existence
- **FR6** A test fails if the bundled copy drifts from `opencode/plugins/`

### Non-Functional Requirements

- **NFR1** Installing twice is idempotent
- **NFR2** No OpenCode-specific logic leaks into the Python server; `install_plugin.py` stays stdlib-only

## Scope

### In Scope

- Bundle `vault-context.ts`, `vault-context-helpers.ts`, `package.json` under `src/duckbrain/plugin/opencode/`
- Flip the `opencode` registry entry to supported with a real path + post-install step
- Marker-based detection (`vault-context.ts` for opencode, `.claude-plugin/plugin.json` for claude-code)
- Tests: bundle presence, install, idempotency, post-install step, marker detection, drift guard
- Docs + CHANGELOG

### Out of Scope

- Bundling `LEARNINGS.md` / `commands/journal.md` (they install to `~/.config/opencode/`, the parent of the plugins dir — a different shape than a single-dir copy)
- Overwrite guard for user-modified files (NFR4 of the original spec, still open)
- Publishing the plugin as an npm package
- `cursor` (stays `tbd`)

## Approach

### Bundle layout

The bundled directory is copied verbatim into the destination. OpenCode discovers both direct `.ts`/`.js` files and immediate package directories under `plugins/`, so flat files are the intersection that works for V1 and V2 — the same shape the README already uses.

```
opencode/plugins/                     src/duckbrain/plugin/opencode/
  vault-context.ts          ─copy─▶     vault-context.ts
  vault-context-helpers.ts              vault-context-helpers.ts
  package.json                          package.json
```

### Drift guard

The bundle is a file copy, not a symlink (same model as the Claude bundle). A pytest byte-compares the three files against `opencode/plugins/` so a stale copy fails CI.

### Marker-based detection

`detect_installed_editors` previously treated "directory exists" as "DuckBrain installed". For OpenCode that is wrong: `~/.config/opencode/plugins` exists for anyone using OpenCode. `EditorTarget` gains an optional `marker` (relative path that must exist) — `vault-context.ts` for opencode, `.claude-plugin/plugin.json` for claude-code.

## Verification

- `uv run pytest` — all pass (includes bundle + drift + detection tests)
- `uv run ruff check` / `ruff format --check` / `mypy` — clean
- `uv build --wheel` then confirm `duckbrain/plugin/opencode/` is present in the wheel
