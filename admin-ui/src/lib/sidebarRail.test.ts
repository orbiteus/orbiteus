import { afterEach, describe, expect, it } from "vitest";
import { isSidebarExpanded, readSidebarOpen, SIDEBAR_OPEN_KEY } from "./sidebarRail";

describe("sidebarRail", () => {
  afterEach(() => {
    window.localStorage.removeItem(SIDEBAR_OPEN_KEY);
  });

  it("is expanded by default when no preference is stored", () => {
    expect(readSidebarOpen()).toBe(true);
    expect(isSidebarExpanded(readSidebarOpen())).toBe(true);
  });

  it("respects stored collapsed preference", () => {
    window.localStorage.setItem(SIDEBAR_OPEN_KEY, "0");
    expect(readSidebarOpen()).toBe(false);
  });

  it("respects stored expanded preference", () => {
    window.localStorage.setItem(SIDEBAR_OPEN_KEY, "1");
    expect(readSidebarOpen()).toBe(true);
  });
});
