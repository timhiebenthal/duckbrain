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
import plugin from "./vault-context"

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
