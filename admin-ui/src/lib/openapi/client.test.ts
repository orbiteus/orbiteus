import { describe, expect, it } from "vitest";
import type { AgentRead } from "./client";

/** Compile-time guard: OpenAPI types are wired for base agent resources. */
describe("openapi types", () => {
  it("AgentRead exposes id", () => {
    const agent = { id: "x" } as AgentRead;
    expect(agent.id).toBe("x");
  });
});
