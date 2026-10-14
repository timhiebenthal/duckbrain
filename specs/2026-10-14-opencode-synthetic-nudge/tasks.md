# OpenCode 2 idle nudge via `synthetic()` — Tasks

## 1. Refactor for testability (TDD)

- [x] Failing tests: fake-context drives `setup` (hooks registered, `synthetic` used, once-per-session, inert without `VAULT_PATH`)
- [x] Extract exported `setup(ctx: Plugin.Context)`; `Plugin.define({ id, setup })`
- [x] Swap idle nudge `prompt` -> `synthetic`
- [x] Update `buildIdleNudgePrompt` docstring

## 2. Keep bundle in sync

- [x] Copy `vault-context.ts` + `vault-context-helpers.ts` into `src/duckbrain/plugin/opencode/`
- [x] Drift guard passes

## 3. Verify

- [x] `bun test` (52 pass) + `bun x tsc --noEmit`
- [x] `uv run pytest` (113 pass) + ruff + mypy
- [ ] **Live V2 session**: confirm a synthetic idle message still triggers a journaling turn

## 4. Docs

- [x] CHANGELOG "Changed" entry
