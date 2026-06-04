import { describe, expect, it } from "vitest";
import type { CrmLead, CrmPerson } from "./client";

/** Compile-time guard: OpenAPI CRM types are wired for showcase resources. */
describe("openapi CRM types", () => {
  it("LeadRead and PersonRead expose id", () => {
    const lead = { id: "x" } as CrmLead;
    const person = { id: "y" } as CrmPerson;
    expect(lead.id).toBe("x");
    expect(person.id).toBe("y");
  });
});
