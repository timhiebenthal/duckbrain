# install-plugin for OpenCode — Tasks

## 1. Bundle

- [x] Create `src/duckbrain/plugin/opencode/`
- [x] Copy `vault-context.ts`, `vault-context-helpers.ts`, `package.json`

## 2. Registry + CLI (TDD)

- [x] Add bundle-presence test
- [x] Add drift-guard test (byte-compare against `opencode/plugins/`)
- [x] Add install + idempotency tests for opencode
- [x] Flip `EDITOR_REGISTRY["opencode"]` to `supported`, fix `default_path`
- [x] Add marker-based detection + test (opencode dir without marker is not a hit)

## 3. Verify

- [x] `uv run pytest` (113 pass)
- [x] `uv run ruff check` / `ruff format --check` / `uv run mypy`
- [ ] `uv build --wheel` + confirm bundle present in wheel (manual, release step)

## 4. Docs

- [x] CHANGELOG entry
- [x] Root README + `opencode/README.md`
