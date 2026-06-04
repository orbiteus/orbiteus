import { describe, expect, it } from "vitest";

/**
 * Realtime hook contract — DoD §15.2 / §12.6.
 *
 * Connection multiplexing lives in `realtimeHub.ts` (leader + BroadcastChannel).
 * Pure topic/URL helpers are covered in `realtimeTopics.test.ts`.
 */

describe("realtime module surface", () => {
  it("exports list hooks from a single entry point", async () => {
    const mod = await import("./realtime");
    expect(typeof mod.useRealtimeList).toBe("function");
    expect(typeof mod.useRealtimeTopics).toBe("function");
    expect(typeof mod.resourceToModel).toBe("function");
  });
});
