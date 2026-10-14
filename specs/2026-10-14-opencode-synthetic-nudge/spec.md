# OpenCode 2 idle nudge via `synthetic()` — Specification

## Overview

The plugin's `session.idle` handler nudges the model to journal before the session ends. On V2 it uses `ctx.session.prompt({ sessionID, text })`, which lands in conversation history as if the **user** typed it. V2 has `ctx.session.synthetic({ sessionID, text })` for messages that are not attributed to the user.

This spec switches the V2 nudge to `synthetic()` and makes the V2 wiring testable so the change is covered.

## Requirements

- **FR1** V2 idle nudge uses `ctx.session.synthetic()`, not `ctx.session.prompt()`
- **FR2** V1 keeps `client.session.prompt(...)` (V1 has no synthetic API)
- **FR3** The nudge still fires at most once per session-segment (recursion guard intact)
- **FR4** The V2 wiring is unit-testable without a live OpenCode session

### Non-Functional Requirements

- **NFR1** No behaviour change to the injected system context (tags, identity, session context, compaction)
- **NFR2** The bundled copy under `src/duckbrain/plugin/opencode/` stays in sync (drift guard from the install PR)

## Scope

### In Scope

- Extract the V2 wiring into an exported `setup(ctx)` referenced by `Plugin.define`
- Swap `prompt` -> `synthetic` in the idle handler
- Unit tests driving `setup` with a fake context: hook registration, idle nudge uses `synthetic`, once-per-session guard, inert without `VAULT_PATH`
- Update the helper docstring + CHANGELOG

### Out of Scope

- V1 nudge delivery (no synthetic API to switch to)

## Approach

`setup` is exported and typed as `(ctx: Plugin.Context)`. `Plugin.define({ id, setup })` references it. Tests build a fake context exposing only `session.hook`, `session.synthetic`, `session.prompt`, and `event.subscribe`, then assert:

1. `context` and `compaction` hooks are registered
2. a `session.idle` event calls `synthetic` (and never `prompt`)
3. two `session.idle` events for the same session produce one nudge
4. without `VAULT_PATH`, no hooks register and `setup` returns nothing

## Verification

- `cd opencode/plugins && bun test` — 52 pass
- `bun x tsc --noEmit` — clean
- `uv run pytest` — 113 pass (drift guard included)

## ⚠️ Live verification still required

The unit test proves the call shape, not that OpenCode acts on a synthetic message the way it acts on a user prompt. The whole point of the nudge is to make the model call `vault_write`. Before merging, confirm in a live V2 session that a synthetic idle message still triggers a model turn that can journal. If it does not, revert to `ctx.session.prompt(...)`.
