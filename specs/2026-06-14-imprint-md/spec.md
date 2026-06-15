# imprint.md — AI-Maintained Identity Document — Specification

## Overview

AI coding agents know the project (via CLAUDE.md, .cursorrules, AGENTS.md) but have no structured knowledge of the *person* using them. Each agent infers user preferences independently — there's no cross-agent user profile, so preferences learned in one session (e.g., "don't use em dashes") are lost across agents or forgotten after context compaction.

**imprint.md** is a single markdown file at the vault root that captures durable user identity — environment, communication preferences, work patterns, technical domains, pet peeves. The AI maintains it; the human audits it; every connected agent reads it at session start.

Zero new infrastructure. The existing context injection pipeline — OpenCode plugin (`Bun.file().text()`), Claude Code hooks (shell scripts), Cursor rules (`.cursorrules`), and DuckBrain's own MCP context tools — already supports reading arbitrary files from the vault. This spec wires those injection points to a new `imprint.md` file.

## Requirements

### Functional Requirements

- **FR1** Create `imprint.md` at vault root with seeded content covering: environment, communication preferences, work patterns, writing style, technical domains, and project values
- **FR2** Every connected agent reads `imprint.md` at session start and behaves according to its contents
- **FR3** The AI updates `imprint.md` when the user states a durable fact, corrects tone/approach, or when a repeated pattern across sessions implies a stable preference
- **FR4** The AI deletes or updates lines in `imprint.md` when the user contradicts them (treats as signal: old fact was wrong, update it)
- **FR5** Lines that go untouched for 6+ months with evidence of staleness get flagged for review or removed
- **FR6** The user never has to manually edit `imprint.md` — all maintenance is agent-driven

### Non-Functional Requirements

- **NFR1** `imprint.md` injection must not regress startup time — file read is sub-millisecond with `Bun.file()` / `cat`
- **NFR2** Missing `imprint.md` must not crash any agent — graceful degradation (no file = no fingerprint, continue normally)
- **NFR3** `imprint.md` content must be human-readable, human-editable, version-controllable plain markdown (not locked in an API or database)
- **NFR4** Individual facts should age well — prefer stable, durable statements over session-specific ones
- **NFR5** No new MCP tools — the file is injected via existing pipelines, not fetched via a new tool

## Scope

### In Scope

- Creating `imprint.md` at vault root with seeded content from the concept wiki page
- Adding `Bun.file("imprint.md").text()` to the OpenCode plugin (`vault-context.ts` / `vault-context-helpers.ts`) — injection into system prompt
- Adding `cat "$VAULT_PATH/imprint.md"` to Claude Code's `SessionStart` hook script (`vault-context.sh`)
- Adding instructions to Cursor's `.cursorrules` to read `imprint.md` at session start
- Adding instructions to DuckBrain's own `AGENTS.md` for Hermes agent
- Documenting the maintenance triggers (agent notices durable fact → updates file)
- Documenting the deletion heuristic (contradiction → update; 6-month staleness → flag)

### Out of Scope

- A new MCP tool to read/write `imprint.md` — the file is injected via existing pipelines, not fetched through DuckBrain's tool interface. If this proves insufficient (e.g., agents don't maintain it), a dedicated tool can be added in a follow-up
- Batch discovery cron job — the concept wiki mentions it as optional. Skip for now; conversational path is primary
- Cross-agent sync protocol — each agent independently reads and writes the same file. If two agents race on edits, last-writer-wins via the filesystem. This is acceptable for a single-user vault
- Validation/linting of `imprint.md` content — agents are relied upon to maintain valid markdown. A follow-up can add automated checks if content quality degrades
- Migration of existing user preferences from Hermes memory, Claude Code `memory.md`, or any other per-agent storage — this is a best-effort seed, not portability guarantee

## Approach

### Technical Approach

The feature has two sides: **read** (injection at session start, all agents) and **write** (AI maintenance triggers, primarily via the agent that's in conversation).

**Read side — four agent injection points, same pattern:**

| Agent | Mechanism | Change Required |
|-------|-----------|-----------------|
| **OpenCode** | TypeScript plugin: `Bun.file()` in `experimental.chat.system.transform` hook | Add `imprint.md` read in `vault-context-helpers.ts`; inject as third tier (after tags, before session context) in `vault-context.ts` |
| **Claude Code** | SessionStart shell hook: `vault-context.sh` | Add `cat "$VAULT_PATH/imprint.md"` to the existing script |
| **Cursor** | `.cursorrules` instruction block | Add instruction: "Read `<vault_root>/imprint.md` at session start" |
| **Hermes** | `AGENTS.md` instruction | Add instruction: "Read `imprint.md` at session start" |

**Write side — triggered by agent noticing during conversation:**

The agent that is in conversation with the user is the same agent that should update `imprint.md`. No cross-agent coordination needed — the agent that learns the fact writes it. The file is plain markdown; any agent can edit it.

**Trigger conditions (agents self-evaluate after each turn):**
- User states a fact about their setup, preferences, or constraints
- User corrects the agent's tone or approach
- Agent notices a repeated pattern across the current session that implies a stable preference
- User explicitly asks the agent to update a preference

**Deletion heuristic:**
- User contradicts a line → agent updates the line
- Line untouched for 6+ months AND agent has evidence it's stale → flag for review (or delete if directly contradicted)

**File structure:**

```
<vault_root>/imprint.md
```

Not inside `wiki/` — imprint.md is metadata *about* the vault's user, not a knowledge page. Same level as `wiki/`, `daily/`.

Frontmatter:
```yaml
---
kind: imprint
last_updated: 2026-06-14
---
```

Content sections (seeded from concept wiki — evolves organically):
- `## Environment` — OS, shell, editor, PKM, agent tools
- `## Communication Preferences` — direct language, avoid AI-typical phrasing, punctuation style
- `## Work Patterns` — TDD, proactive verification, source-code-backed analysis
- `## Writing (Substack / Blog)` — format constraints
- `## Technical Domains` — areas of expertise
- `## Project Values` — engineering philosophy

### User Experience

**For the user:** Nothing changes day-to-day. They interact with the agent as usual. When they say "I work in WSL" or "Don't use em dashes", the agent writes to `imprint.md` silently (as part of its normal response). The user can audit the file anytime.

**Session start flow (all agents):**
```
1. Agent reads imprint.md (sub-millisecond)
2. Agent adjusts tone, style, and behavior based on stored preferences
3. Agent proceeds with user's request, now personalized
```

### Implementation Outline

#### Phase 1: Seed imprint.md

Create the file at vault root with content from the concept wiki page. This is a one-time human+AI action — the file then evolves organically.

#### Phase 2: OpenCode plugin injection

In `vault-context-helpers.ts`, add:

```typescript
export async function loadIdentity(vaultPath: string): Promise<string | null> {
  return safeRead(`${vaultPath}/imprint.md`)
}
```

In `vault-context.ts`, add a third tier after tags (Tier 1) and session context (Tier 2):

```typescript
// Tier 3: Imprint — always injected, small file
const identity = await loadIdentity(vaultPath)
if (identity) {
  output.system.push(`
<vault-identity>
${identity}
</vault-identity>
  `.trim())
}
```

Placement: after tags (always-injected routing signal) and before session context (expensive, may not load every call). Imprint is small like tags, so it joins Tier 1.

#### Phase 3: Claude Code hook injection

In `claude/scripts/vault-context.sh`, add after the existing vault-context output:

```bash
echo "<vault-identity>"
cat "$VAULT_PATH/imprint.md" 2>/dev/null || echo "<!-- no imprint.md found -->"
echo "</vault-identity>"
```

#### Phase 4: Cursor .cursorrules instruction

In `cursor/.cursorrules`, add a block:

```
## User identity

Read <vault_root>/imprint.md at session start to learn communication preferences,
environment, work patterns, and technical domains. Adjust your tone and approach
accordingly. If the user states a durable fact about themselves, update imprint.md.
```

#### Phase 5: Hermes AGENTS.md instruction

In `AGENTS.md`, add:

```
## User identity

Read <vault_root>/imprint.md at session start — contains communication
preferences, environment details, and work patterns. Maintain it: when
the user states a durable fact or corrects your approach, update imprint.md.
```

#### Maintenance instruction for agents

Each agent's instruction file (`.cursorrules`, `AGENTS.md`, etc.) should include:

```
### imprint.md maintenance

When the user:
- States a fact about their setup, preferences, or constraints → update imprint.md
- Corrects your tone or approach → update imprint.md
- Demonstrates a repeated work pattern → consider adding to imprint.md
- Contradicts an existing line → update or remove that line

Do NOT add session-specific details (one-off tasks, current bugs). Only durable facts.
```

## Dependencies

- **OpenCode plugin** — `vault-context.ts` and `vault-context-helpers.ts` — already at `opencode/plugins/`. No new dependencies; `Bun.file()` is stdlib
- **Claude Code hooks** — `claude/scripts/vault-context.sh` — already exists. No new dependencies beyond `cat` (POSIX)
- **Cursor** — `cursor/.cursorrules` and project `.cursorrules` — already exist. No dependencies beyond the file being present
- **DuckBrain server** — no changes needed. The `vault_read` tool is already available for agents to read `imprint.md` if they need programmatic access
- **No new Python/Typescript packages** — all changes are configuration and file creation

## Success Criteria

1. `imprint.md` exists at vault root with seeded content (environment, communication, work patterns, domains, values)
2. OpenCode session start injects `<vault-identity>` block with `imprint.md` content into system prompt
3. Claude Code `SessionStart` hook outputs `imprint.md` content readable by the agent
4. Cursor agent reads `imprint.md` at session start and adjusts behavior (verify: ask a tone-sensitive question, confirm it matches preferences)
5. Agent notices a durable fact in conversation and writes it to `imprint.md` (verify: say "I prefer tabs over spaces", check `imprint.md` was updated)
6. Agent updates a line when user contradicts it (verify: say "Actually, I changed my mind about X", check update)
7. Missing `imprint.md` produces no crash — graceful degradation
8. Vault context injection unchanged — no regression in existing behavior

## Notes

- **Why not a new MCP tool?** The file is read once at session start and is tiny (<2K). A tool call adds latency and complexity. Direct file read via the plugin/hook layer is zero-cost and already available
- **Why not store in wiki/?** imprint.md is metadata *about* the vault's user, not a knowledge page. It doesn't belong in the wiki taxonomy (entity/concept/source/synthesis). Vault root keeps it distinct
- **Race conditions on writes:** Two agents could theoretically write to `imprint.md` simultaneously. For a single-user vault this is acceptably rare. Last-writer-wins via filesystem. If this becomes a problem, a future MCP tool can serialize writes
- **Seeding strategy:** The concept wiki page already has a draft. The first implementation should copy it verbatim to `imprint.md`. The AI will evolve it from there
- **Relation to other memory files:**
  - `imprint.md` = who the user is (durable identity)
  - `CLAUDE.md` / `.cursorrules` / `AGENTS.md` = how the project works (project config)
  - Daily notes = what happened in a session (session memory)
  - Claude Code `memory.md` = recent decisions and progress (working memory)
