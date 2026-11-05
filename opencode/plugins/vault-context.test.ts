/**
 * Tests for the dual OpenCode v1 + v2 plugin entrypoint.
 *
 * These assert the *shape* of the default export, not hook behaviour:
 *   - v2 reads `id` + `setup`
 *   - v1 (>= 1.18.29) reads `server`
 * Hook behaviour is covered by vault-context-helpers.test.ts via the pure
 * helpers both runtimes share.
 */

import { describe, test, expect, beforeEach, afterEach } from "bun:test"
import plugin, { setup } from "./vault-context"

// Minimal fake of the OpenCode 2 context, just enough to drive `setup`.
// Not a full SDK mock - only the surfaces setup actually touches.
type IdleEvent = { type: "session.idle"; data: { sessionID: string } }

function makeFakeCtx(events: IdleEvent[]) {
  const hooks: Record<string, (event: unknown) => Promise<void>> = {}
  const synthetic: { sessionID: string; text: string }[] = []
  const prompt: unknown[] = []

  const ctx = {
    session: {
      hook: async (name: string, cb: (event: unknown) => Promise<void>) => {
        hooks[name] = cb
        return { dispose: async () => {} }
      },
      synthetic: async (input: { sessionID: string; text: string }) => {
        synthetic.push(input)
      },
      prompt: async (input: unknown) => {
        prompt.push(input)
      },
    },
    event: {
      subscribe: () =>
        (async function* () {
          for (const e of events) yield e
        })(),
    },
  }

  return { ctx, hooks, synthetic, prompt }
}

const originalVaultPath = process.env.VAULT_PATH

beforeEach(() => {
  delete process.env.VAULT_PATH
})

afterEach(() => {
  if (originalVaultPath === undefined) delete process.env.VAULT_PATH
  else process.env.VAULT_PATH = originalVaultPath
})

describe("default export", () => {
  test("exposes the v2 plugin definition (id + setup)", () => {
    expect(plugin.id).toBe("duckbrain.vault-context")
    expect(typeof plugin.setup).toBe("function")
  })

  test("exposes the v1 server entrypoint", () => {
    expect(typeof plugin.server).toBe("function")
  })
})

describe("v1 server", () => {
  test("returns the expected hook map when VAULT_PATH is set", async () => {
    process.env.VAULT_PATH = "/tmp/does-not-need-to-exist"
    const hooks = await plugin.server({} as never)
    expect(Object.keys(hooks).sort()).toEqual([
      "event",
      "experimental.chat.system.transform",
      "experimental.session.compacting",
    ])
  })

  test("is inert (empty hook map) without VAULT_PATH", async () => {
    const hooks = await plugin.server({} as never)
    expect(hooks).toEqual({})
  })
})

describe("v2 setup", () => {
  test("registers context + compaction hooks and returns a cleanup", async () => {
    process.env.VAULT_PATH = "/tmp/does-not-need-to-exist"
    const { ctx, hooks } = makeFakeCtx([])
    const cleanup = await setup(ctx as never)
    expect(Object.keys(hooks).sort()).toEqual(["compaction", "context"])
    expect(typeof cleanup).toBe("function")
  })

  test("idle nudge uses synthetic(), not prompt()", async () => {
    process.env.VAULT_PATH = "/tmp/does-not-need-to-exist"
    const { ctx, synthetic, prompt } = makeFakeCtx([
      { type: "session.idle", data: { sessionID: "ses_1" } },
    ])
    await setup(ctx as never)
    await Bun.sleep(5)

    expect(prompt).toHaveLength(0)
    expect(synthetic).toHaveLength(1)
    expect(synthetic[0].sessionID).toBe("ses_1")
    expect(synthetic[0].text).toContain('vault_write(kind="daily"')
  })

  test("idle nudge fires once per session (recursion guard)", async () => {
    process.env.VAULT_PATH = "/tmp/does-not-need-to-exist"
    const { ctx, synthetic } = makeFakeCtx([
      { type: "session.idle", data: { sessionID: "ses_1" } },
      { type: "session.idle", data: { sessionID: "ses_1" } },
    ])
    await setup(ctx as never)
    await Bun.sleep(5)
    expect(synthetic).toHaveLength(1)
  })

  test("is inert (no hooks, no cleanup) without VAULT_PATH", async () => {
    const { ctx, hooks } = makeFakeCtx([])
    const cleanup = await setup(ctx as never)
    expect(hooks).toEqual({})
    expect(cleanup).toBeUndefined()
  })
})
