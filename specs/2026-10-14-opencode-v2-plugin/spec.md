# OpenCode V2 Plugin Support — Specification

## Overview

DuckBrain's OpenCode integration ships a session plugin (`opencode/plugins/vault-context.ts`) that injects vault context into the system prompt, preserves a snapshot across compaction, and nudges the model to journal on `session.idle`.

OpenCode 2 replaced the plugin API. Per the migration guide, *"V1 plugin implementations do not run in V2."* The runtime changed from "export a function that returns a hook map" to "default-export `Plugin.define({ id, setup(ctx) })` and register hooks on the context." Moving or renaming the file is not enough.

This spec adds OpenCode 2 support **without dropping OpenCode 1**. Both runtimes read one default export: V2 reads `id` + `setup`, V1 (>= 1.18.29) reads `server`.

## Requirements

### Functional Requirements

- **FR1** The default export of `vault-context.ts` exposes a V2 plugin definition (`id`, `setup`)
- **FR2** The same default export exposes a V1 `server` entrypoint returning the three existing hooks
- **FR3** Injected text (tags + learnings ritual, identity block) is produced by shared pure helpers so V1 and V2 output cannot drift
- **FR4** V2 injection uses content parts (`event.system.push({ type: "text", text })`); V1 keeps raw strings (`output.system.push(text)`)
- **FR5** V2 per-session state is keyed by `sessionID` (one instance serves every session in the location); V1 keeps per-process booleans
- **FR6** V2 idle handling subscribes to the event stream via `ctx.event.subscribe()` and aborts on cleanup
- **FR7** Missing `VAULT_PATH` leaves both runtimes inert (no injection, no nudge)
- **FR8** Both runtimes keep graceful degradation — a vault read failure never crashes the session

### Non-Functional Requirements

- **NFR1** No behaviour regression for OpenCode 1 users beyond the version floor (1.18.29)
- **NFR2** The pure helpers stay runtime-agnostic and unit-testable with `bun test`
- **NFR3** No new MCP tools; no changes to the Python server

## Scope

### In Scope

- Rewriting `opencode/plugins/vault-context.ts` as a dual V1 + V2 default export
- Extracting `buildVaultContextBlock` / `buildIdentityBlock` into `vault-context-helpers.ts`
- Adding `@opencode/plugin` to `opencode/plugins/package.json`
- Tests: helper builders + dual-export shape
- Docs (`README.md`, `opencode/README.md`) and `CHANGELOG.md`
- Documenting the V1 version floor and the `plugin` → `plugins` config rename

### Out of Scope

- Bundling the OpenCode plugin under `src/duckbrain/plugin/opencode/` and flipping `EDITOR_REGISTRY["opencode"].status` to `supported` (the `install-plugin` CLI). Follow-up
- Migrating V1 MCP/agent config to native V2 shape (V2 reads V1 config; optional)
- Replacing the idle nudge with `ctx.session.synthetic()` — noted as a possible follow-up, kept as `ctx.session.prompt()` for parity with V1

## Approach

### Two unknowns, resolved before implementation

Both were verified against the installed packages, not assumed:

1. **`Bun.file` in the V2 runtime** — confirmed working. V2 runs on Bun and provides `Bun`; the helpers use it unchanged. (V1's sandbox blocked `import("fs")`; `Bun.file` remains the common tool.)
2. **`server()` arguments** — V1's types declare `PluginModule.server: Plugin` and `Plugin = (input: PluginInput, options?) => Promise<Hooks>`. V1 therefore passes the same `{ client, directory, project, worktree, serverUrl, $ }` input as the function form, so the idle nudge keeps using `input.client.session.prompt(...)`.

### Dual export

```ts
const plugin = Plugin.define({ id: "duckbrain.vault-context", async setup(ctx) { /* V2 */ } })

export default {
  ...plugin,                        // V2 reads id + setup
  async server(input) { /* V1 */ }, // V1 reads server
}
```

`Plugin.define` is an identity function; spreading it and adding `server` yields one object that each runtime partially reads. The other runtime ignores the extra key.

### Shared helpers

Tags, identity, session context, compaction snapshot, and idle nudge text all come from `vault-context-helpers.ts`. Extract the two large inline strings into `buildVaultContextBlock(tags, today)` and `buildIdentityBlock(identity)` so both adapters emit identical output.

## Verification

- `cd opencode/plugins && bun test` — all pass (helper builders + dual-export shape)
- `bun x tsc --noEmit` — clean
- Manual: plugin appears in the active plugin list on OpenCode 1 (>= 1.18.29) and OpenCode 2; tier-1 injection, compaction, and idle paths exercised on V2
