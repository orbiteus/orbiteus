import { describe, expect, it } from "vitest";
import { initiatorColor, initiatorTooltip } from "./auditInitiator";

describe("auditInitiator", () => {
  it("maps kind to badge colors", () => {
    expect(initiatorColor("user")).toBe("blue");
    expect(initiatorColor("ai")).toBe("violet");
    expect(initiatorColor("portal")).toBe("cyan");
    expect(initiatorColor("system")).toBe("gray");
  });

  it("builds tooltip from label, detail, and ids", () => {
    const tip = initiatorTooltip(
      {
        kind: "user",
        label: "Admin (admin@example.com)",
        detail: "IP 10.0.0.1",
      },
      { user_id: "uuid-1", request_id: "req-9" },
    );
    expect(tip).toContain("Admin (admin@example.com)");
    expect(tip).toContain("IP 10.0.0.1");
    expect(tip).toContain("user_id uuid-1");
    expect(tip).toContain("request_id req-9");
  });
});
