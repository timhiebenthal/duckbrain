# OpenCode V2 Plugin Support — Tasks

## 1. Resolve runtime unknowns

- [x] Confirm `Bun.file` works in the OpenCode 2 plugin runtime
      → V2 runs on Bun and provides `Bun`; helpers unchanged
- [x] Confirm V1 `server()` receives the plugin input
      → `@opencode-ai/plugin` types: `PluginModule.server: Plugin`,
        `Plugin = (input: PluginInput, options?) => Promise<Hooks>`

## 2. Extract shared helpers (TDD)

- [x] Write failing tests for `buildVaultContextBlock` + `buildIdentityBlock`
- [x] Implement `buildVaultContextBlock(tags, today)` in `vault-context-helpers.ts`
- [x] Implement `buildIdentityBlock(identity)` in `vault-context-helpers.ts`
- [x] `bun test` green

## 3. Dual export

- [x] Rewrite `vault-context.ts`: `Plugin.define({ id, setup })` for V2
- [x] Add `server(input)` entrypoint for V1
- [x] Default export spreads the V2 definition and adds `server`
- [x] V2 per-session state as `Set<string>`; V1 keeps booleans
- [x] V2 event stream via `ctx.event.subscribe()` + cleanup abort
- [x] V1 keeps `client.session.prompt({ path, body })`

## 4. Tests for the dual shape

- [x] `vault-context.test.ts`: `id`, `setup`, `server` present
- [x] `server()` returns the three hooks when `VAULT_PATH` set
- [x] `server()` returns `{}` without `VAULT_PATH`
- [x] `bun test` + `bun x tsc --noEmit` green

## 5. Packaging + docs

- [x] Add `@opencode/plugin` to `opencode/plugins/package.json`
- [x] Update root `README.md` OpenCode section (V1 + V2, version floor)
- [x] Update `opencode/README.md`
- [x] Add `CHANGELOG.md` Unreleased entry

## 6. Follow-ups (not this PR)

- [ ] Bundle plugin under `src/duckbrain/plugin/opencode/`, mark registry `supported`
- [ ] Evaluate `ctx.session.synthetic()` to stop the idle nudge appearing as a user message
- [ ] Reconsider compaction snapshot injection if V2's compaction semantics allow a cleaner fit
