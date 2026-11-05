# Implementation Plan: Codex Context

## Overview

Implement the approved [context specification](../SPEC-codex-context.md) as an opt-in integration. Start by testing Codex CLI behavior, then build the smallest verified path to startup context. Journaling and full setup are separate capabilities in the [capability map](../CAPABILITY-MAP.md).

## Architecture decisions

- Test MCP handshake instructions in an isolated temporary vault before choosing the transport. Codex CLI 0.166.0 is installed; record the version and observed results.
- If a fresh CLI session reliably receives handshake instructions, configure opt-in server instructions at startup. Otherwise, supply Codex instructions that request the same snapshot through MCP. Do not change default behavior for existing clients.
- Reuse the existing vault filesystem conventions and MCP server. Context is a startup snapshot; document observed refresh and compaction behavior rather than promising parity.
- Maintain test-first development and avoid changing the current machine's global Codex configuration during experiments.

## Ordered tasks

1. Probe Codex handshake and fallback behavior in a temporary environment.
2. Build and test the vault context snapshot.
3. Expose the snapshot through the verified opt-in path and test the MCP boundary.
4. Document and smoke-test the context-only setup; run quality gates.

The completed task checklist and checkpoints are in [codex-context-todo.md](codex-context-todo.md).

## Risks and mitigation

| Risk | Mitigation |
|---|---|
| Codex may ignore or retain stale handshake instructions | Test startup and resume; use instruction-driven MCP retrieval if startup injection fails; document refresh limitations. |
| Existing clients may receive duplicate context | Require explicit opt-in and test the default initialize response. |
| Daily notes may contain private or large content | Send only the agreed vault files to the configured local client; document snapshot contents and avoid storing real vault data in test artifacts. |

## Open question

The precise startup injection path remains contingent on the first task's CLI evidence, as required by the approved spec. If neither path passes the smoke test, stop and report the observed blocker instead of claiming automatic context works.
