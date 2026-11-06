# Codex CLI setup

Install DuckBrain and configure its MCP server, replacing the vault path:

```bash
codex mcp add duckbrain --env VAULT_PATH=/absolute/path/to/vault --env DUCKBRAIN_CODEX_CONTEXT=1 -- uvx duckbrain
```

The `uvx` command requires a published DuckBrain release containing this feature. To try it from a checkout before release, replace `uvx duckbrain` with `uv run --directory /absolute/path/to/duckbrain duckbrain`.

If DuckBrain is already registered, inspect its configuration with `codex mcp get duckbrain` and update the existing entry instead of adding a duplicate. Check registration with `codex mcp list`.

Add the following to `~/.codex/AGENTS.md` for all projects, or to a project's `AGENTS.md`:

```markdown
At the start of each session, discover the duckbrain MCP server and its tools to load its vault context before responding. Use each tool's advertised input schema when calling it; if validation fails, correct the arguments from the error and retry once.
```

Start a new session and ask Codex to summarize its vault context. The opt-in server sends a startup snapshot containing `wiki/tags.md`, `imprint.md`, the last 30 lines of `wiki/log.md`, and today's and yesterday's daily notes when present. Dates use the server's local timezone. Vault content is shared with the configured Codex session; only enable this for a vault you want to share with it.

Discovery is instruction-driven and depends on Codex following the instruction. On Codex CLI 0.166.0 a fresh session received this snapshot after discovering the server without calling a tool. The snapshot is generated when the server starts; changes made afterwards require a fresh server connection. Refresh on resume and behavior after compaction have not been verified. MCP tool calls may require approval separately from discovery.

## Journal the session

From a DuckBrain checkout, install the skill for your user:

```bash
mkdir -p ~/.agents/skills/duckbrain-journal
cp -R codex/skills/duckbrain-journal/. ~/.agents/skills/duckbrain-journal/
```

Start a new Codex session and ask it to use `$duckbrain-journal`. It reads today's note, records new progress, learnings and open work, and reports the result. MCP tool calls may prompt for approval. In a temporary-vault test on Codex CLI 0.166.0, the skill successfully read and wrote a daily note when that test server's tools were configured for approval.

To verify the setup safely, register a separate empty temporary directory as the vault and start a new session. Give Codex a distinctive test decision, invoke `$duckbrain-journal`, and approve the tool call if prompted. Check the reported path under `daily/` in that temporary vault for the decision. Invoke the skill again without adding new information and check that it skips a duplicate. Restore your intended vault configuration when finished.

To encourage capture during work, add this to your Codex `AGENTS.md`:

```markdown
Capture meaningful new decisions, root causes and discoveries in DuckBrain's daily note as work progresses. Check for duplicates first and skip the write if there is nothing new.
```

### Optional automatic reminder

To remind Codex on each submitted prompt, copy `codex/hooks/journal-reminder.sh` to a stable path and add this to `~/.codex/config.toml`, replacing the path with the absolute path to that copy:

```toml
[[hooks.UserPromptSubmit]]
hooks = [{ type = "command", command = "sh /absolute/path/to/journal-reminder.sh" }]
```

Merge this entry with any existing hook configuration. Codex may ask you to review and trust the hook. The hook supplies a reminder on every prompt; it does not itself write to the vault. Delivery of a `UserPromptSubmit` hook's output to the model was verified on Codex CLI 0.166.0. This does not guarantee a write or capture after an abrupt terminal close.
