# Implementation Plan: Codex Journaling

Implement [the approved journaling spec](../SPEC-codex-journaling.md) in small slices: validate CLI event and MCP permission behavior; supply an explicit journal skill and proactive instructions; include an automatic reminder only when its delivery is demonstrated; document and verify the result. Preserve existing vault tools and context integration. Tasks and acceptance checks are in [todo.md](todo.md).

Run tests first for any production behavior. Test with temporary vaults and isolated Codex configuration; do not change the user's global setup. Record event, permission and smoke-test limitations rather than claiming unverified behavior. No installer or changes to other agent integrations are in scope.
