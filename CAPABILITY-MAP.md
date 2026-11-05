# Capability Map: Codex Support

| Module id | Responsibility | Depends on |
|---|---|---|
| codex-context | Supply vault context automatically to Codex, with an MCP retrieval fallback | Existing DuckBrain MCP server |
| codex-journaling | Provide a journal skill and verified automatic reminders | Existing DuckBrain MCP server |
| codex-setup | Document configuration and verification of both capabilities | codex-context, codex-journaling |

Build order: codex-context → codex-journaling → codex-setup.
