import { describe, expect, it } from "vitest";

import { ORBITEUS_DARK, orbiteusTheme } from "./theme";

describe("orbiteusTheme", () => {
  it("uses charcoal primary instead of default blue", () => {
    expect(orbiteusTheme.primaryColor).toBe("dark");
    expect(ORBITEUS_DARK[8]).toBe("#27272a");
    expect(ORBITEUS_DARK[9]).toBe("#09090b");
  });

  it("uses balanced readable density (16px body)", () => {
    expect(orbiteusTheme.fontSizes?.md).toBe("16px");
    expect(orbiteusTheme.spacing?.md).toBe("16px");
  });
});
