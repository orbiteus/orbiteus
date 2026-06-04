import { describe, expect, it } from "vitest";
import { isSidebarExpanded } from "./sidebarRail";

describe("sidebarRail", () => {
  it("collapsed by default", () => {
    expect(isSidebarExpanded(false)).toBe(false);
  });

  it("expanded only when toggled open", () => {
    expect(isSidebarExpanded(true)).toBe(true);
  });
});
