/**
 * Tests for vault-context-helpers.
 *
 * These are pure-function tests against a real temp vault directory.
 * No mocks of Bun.file or Date — bun:test's setSystemTime handles
 * time control, and Bun.write creates real files. This is the same
 * "no mocks" testing convention duckbrain's Python tests use.
 */

import { describe, test, expect, beforeEach, afterEach, setSystemTime } from "bun:test"
import { mkdtemp, rm, writeFile, mkdir } from "fs/promises"
import { tmpdir } from "os"
import { join } from "path"
import {
  tail,
  todayStr,
  yesterdayStr,
  loadTags,
  loadIdentity,
  loadSessionContext,
  loadCompactionSnapshot,
  buildIdleNudgePrompt,
  MAX_LOG_LINES,
} from "./vault-context-helpers"

let vaultPath: string
const originalTz = process.env.TZ

beforeEach(async () => {
  vaultPath = await mkdtemp(join(tmpdir(), "vault-test-"))
})

afterEach(async () => {
  await rm(vaultPath, { recursive: true, force: true })
  process.env.TZ = originalTz
  setSystemTime() // reset
})

/** Write a file at vaultPath/rel, creating parent dirs. */
async function vaultWrite(rel: string, content: string) {
  const fullPath = join(vaultPath, rel)
  await mkdir(fullPath.substring(0, fullPath.lastIndexOf("/")), { recursive: true })
  await writeFile(fullPath, content, "utf-8")
}

// ─── tail ────────────────────────────────────────────────────────────────────

describe("tail", () => {
  test("returns last N lines", () => {
    expect(tail("a\nb\nc\nd\ne", 3)).toBe("c\nd\ne")
  })

  test("returns full text when N >= line count", () => {
    expect(tail("a\nb", 5)).toBe("a\nb")
  })

  test("handles empty string", () => {
    expect(tail("", 5)).toBe("")
  })

  test("handles N=0", () => {
    expect(tail("a\nb\nc", 0)).toBe("")
  })

  test("preserves trailing newline character count", () => {
    // "a\nb\nc" has 3 elements when split — tail returns them
    const result = tail("a\nb\nc", 2)
    expect(result.split("\n")).toEqual(["b", "c"])
  })
})

// ─── todayStr / yesterdayStr ─────────────────────────────────────────────────

describe("todayStr", () => {
  test("returns local YYYY-MM-DD format", () => {
    setSystemTime(new Date("2026-06-15T12:00:00"))
    expect(todayStr()).toBe("2026-06-15")
  })

  test("returns YYYY-MM-DD with zero-padded month and day", () => {
    setSystemTime(new Date("2026-01-05T12:00:00"))
    expect(todayStr()).toBe("2026-01-05")
  })

  test("TZ bug fix: uses local timezone, not UTC", () => {
    // 2026-06-15T03:00:00Z = 2026-06-14 20:00 in America/Los_Angeles
    // UTC date is 2026-06-15, LA local date is 2026-06-14.
    // Before fix: would return "2026-06-15" (wrong for LA user at 8pm).
    // After fix: returns "2026-06-14" (correct — it's still Sunday night in LA).
    process.env.TZ = "America/Los_Angeles"
    setSystemTime(new Date("2026-06-15T03:00:00Z"))
    expect(todayStr()).toBe("2026-06-14")
  })

  test("TZ bug fix: Tokyo user gets correct local date", () => {
    // 2026-06-14T16:00:00Z = 2026-06-15 01:00 in Asia/Tokyo
    // UTC date is 2026-06-14, Tokyo local date is 2026-06-15.
    process.env.TZ = "Asia/Tokyo"
    setSystemTime(new Date("2026-06-14T16:00:00Z"))
    expect(todayStr()).toBe("2026-06-15")
  })

  test("UTC user gets same answer as before (no regression)", () => {
    process.env.TZ = "UTC"
    setSystemTime(new Date("2026-06-15T03:00:00Z"))
    expect(todayStr()).toBe("2026-06-15")
  })
})

describe("yesterdayStr", () => {
  test("returns local date for yesterday", () => {
    setSystemTime(new Date("2026-06-15T12:00:00"))
    expect(yesterdayStr()).toBe("2026-06-14")
  })

  test("handles month boundary", () => {
    setSystemTime(new Date("2026-07-01T12:00:00"))
    expect(yesterdayStr()).toBe("2026-06-30")
  })

  test("handles year boundary", () => {
    setSystemTime(new Date("2026-01-01T12:00:00"))
    expect(yesterdayStr()).toBe("2025-12-31")
  })

  test("TZ bug fix: uses local timezone for subtraction", () => {
    // 2026-06-15T03:00:00Z in LA = 2026-06-14 20:00 LA local
    // Yesterday in LA = 2026-06-13
    process.env.TZ = "America/Los_Angeles"
    setSystemTime(new Date("2026-06-15T03:00:00Z"))
    expect(yesterdayStr()).toBe("2026-06-13")
  })
})

// ─── loadTags ────────────────────────────────────────────────────────────────

describe("loadTags", () => {
  test("returns content of wiki/tags.md", async () => {
    await vaultWrite("wiki/tags.md", "# tags\n- foo\n- bar")
    expect(await loadTags(vaultPath)).toBe("# tags\n- foo\n- bar")
  })

  test("returns null when file missing", async () => {
    expect(await loadTags(vaultPath)).toBeNull()
  })

  test("returns null when wiki/ directory missing", async () => {
    expect(await loadTags(vaultPath)).toBeNull()
  })
})

// ─── loadIdentity ─────────────────────────────────────────────────────────────

describe("loadIdentity", () => {
  test("returns content of imprint.md", async () => {
    await vaultWrite("imprint.md", "# Environment\n- OS: WSL")
    expect(await loadIdentity(vaultPath)).toBe("# Environment\n- OS: WSL")
  })

  test("returns null when imprint.md missing", async () => {
    expect(await loadIdentity(vaultPath)).toBeNull()
  })

  test("returns null when vault directory is empty", async () => {
    expect(await loadIdentity(vaultPath)).toBeNull()
  })
})

// ─── loadSessionContext ──────────────────────────────────────────────────────

describe("loadSessionContext", () => {
  test("includes log tail, today, and yesterday when all present", async () => {
    await vaultWrite("wiki/log.md", "log line 1\nlog line 2\nlog line 3")
    await vaultWrite("daily/2026-06-15.md", "# today content")
    await vaultWrite("daily/2026-06-14.md", "# yesterday content")

    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadSessionContext(vaultPath)

    expect(result).toContain("## Recent vault writes")
    expect(result).toContain("log line 3")
    expect(result).toContain("## 📅 Today's daily note (2026-06-15)")
    expect(result).toContain("today content")
    expect(result).toContain("## 📅 Yesterday's daily note (2026-06-14)")
    expect(result).toContain("yesterday content")
  })

  test("trims daily note content", async () => {
    await vaultWrite("daily/2026-06-15.md", "  \n# today\n\n  with whitespace  \n  ")
    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadSessionContext(vaultPath)
    expect(result).not.toMatch(/  \n/)
    expect(result).toContain("with whitespace")
  })

  test("respects MAX_LOG_LINES limit", async () => {
    const lines = Array.from({ length: 100 }, (_, i) => `line ${i + 1}`).join("\n")
    await vaultWrite("wiki/log.md", lines)

    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadSessionContext(vaultPath)

    // Should include last MAX_LOG_LINES lines but not earlier ones
    expect(result).toContain(`line 100`)
    expect(result).toContain(`line ${100 - MAX_LOG_LINES + 1}`)
    expect(result).not.toContain("line 1\n")
  })

  test("returns empty string when vault is empty", async () => {
    const result = await loadSessionContext(vaultPath)
    expect(result).toBe("")
  })

  test("skips missing files gracefully", async () => {
    await vaultWrite("wiki/log.md", "only log line")
    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadSessionContext(vaultPath)
    expect(result).toContain("only log line")
    expect(result).not.toContain("📅 Today's daily note")
    expect(result).not.toContain("📅 Yesterday's daily note")
  })

  test("uses local date for 'today' label (TZ fix)", async () => {
    // 2026-06-15T03:00:00Z in LA = 2026-06-14 local
    // File is named for local date, not UTC date
    process.env.TZ = "America/Los_Angeles"
    setSystemTime(new Date("2026-06-15T03:00:00Z"))
    await vaultWrite("daily/2026-06-14.md", "the LA today")
    // No file for 2026-06-15 (UTC date) — would only load if buggy
    await vaultWrite("daily/2026-06-13.md", "the LA yesterday")

    const result = await loadSessionContext(vaultPath)
    expect(result).toContain("📅 Today's daily note (2026-06-14)")
    expect(result).toContain("the LA today")
    expect(result).toContain("📅 Yesterday's daily note (2026-06-13)")
    expect(result).toContain("the LA yesterday")
  })
})

// ─── loadCompactionSnapshot ──────────────────────────────────────────────────

describe("loadCompactionSnapshot", () => {
  test("includes compact log tail (15 lines, not 30)", async () => {
    const lines = Array.from({ length: 50 }, (_, i) => `entry ${i + 1}`).join("\n")
    await vaultWrite("wiki/log.md", lines)
    await vaultWrite("daily/2026-06-15.md", "today content")

    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadCompactionSnapshot(vaultPath)

    // Should contain the last 15 entries
    expect(result).toContain("entry 50")
    expect(result).toContain("entry 36") // 15th from end
    // Should NOT contain entries from the first half
    expect(result).not.toContain("entry 35\n")
    expect(result).not.toContain("entry 1\n")
  })

  test("includes today's daily note", async () => {
    await vaultWrite("daily/2026-06-15.md", "today stuff")
    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadCompactionSnapshot(vaultPath)
    expect(result).toContain("### Today's daily note (2026-06-15)")
    expect(result).toContain("today stuff")
  })

  test("does NOT include yesterday's daily (snapshot is tighter)", async () => {
    await vaultWrite("daily/2026-06-15.md", "today")
    await vaultWrite("daily/2026-06-14.md", "yesterday")
    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadCompactionSnapshot(vaultPath)
    expect(result).toContain("today")
    expect(result).not.toContain("yesterday")
  })

  test("includes journal checkpoint nudge", async () => {
    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadCompactionSnapshot(vaultPath)
    expect(result).toContain("⚠️ Journal checkpoint")
    expect(result).toContain('vault_write(kind="daily"')
    expect(result).toContain("## Topic")
    expect(result).toContain("server prepends HH:MM")
  })

  test("includes preservation preamble", async () => {
    const result = await loadCompactionSnapshot(vaultPath)
    expect(result).toMatch(/^The following vault context was active at compaction time/)
  })

  test("returns preamble + journal nudge when vault empty", async () => {
    setSystemTime(new Date("2026-06-15T12:00:00"))
    const result = await loadCompactionSnapshot(vaultPath)
    expect(result).toContain("active at compaction time")
    expect(result).toContain("⚠️ Journal checkpoint")
    expect(result).not.toContain("### Recent vault writes")
    expect(result).not.toContain("### Today's daily note")
  })
})

// ─── tunables ────────────────────────────────────────────────────────────────

describe("MAX_LOG_LINES", () => {
  test("is 30 (matches spec tier 2 claim)", () => {
    expect(MAX_LOG_LINES).toBe(30)
  })
})

// ─── buildIdleNudgePrompt ────────────────────────────────────────────────────

describe("buildIdleNudgePrompt", () => {
  test("includes the supplied date in vault_write title", () => {
    const prompt = buildIdleNudgePrompt("2026-06-15")
    expect(prompt).toContain('title="2026-06-15"')
  })

  test("uses a generic Topic template (no HH:MM — server adds it)", () => {
    const prompt = buildIdleNudgePrompt("2026-06-15")
    expect(prompt).toContain("## Topic\\n\\nDetails")
    // Defensive: should NOT contain a literal HH:MM, since the model
    // is not responsible for the timestamp.
    expect(prompt).not.toMatch(/\d{2}:\d{2}/)
  })

  test("references vault_write with the daily kind", () => {
    const prompt = buildIdleNudgePrompt("2026-06-15")
    expect(prompt).toContain('vault_write(kind="daily"')
  })

  test("instructs the model to skip if nothing new", () => {
    const prompt = buildIdleNudgePrompt("2026-06-15")
    expect(prompt).toMatch(/nothing new|skip/i)
  })

  test("mentions the trigger (session is idle)", () => {
    const prompt = buildIdleNudgePrompt("2026-06-15")
    expect(prompt.toLowerCase()).toContain("idle")
  })
})

// (currentTimeStr was removed in v0.4.0 — timestamp guarantee moved to
//  the server's writer.py, applied uniformly to every MCP client.)
