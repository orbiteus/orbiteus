import { describe, expect, it } from "vitest";
import { CORE_LOCALE_CODES } from "./coreLocales";

describe("CORE_LOCALE_CODES", () => {
  it("only English is core", () => {
    expect(CORE_LOCALE_CODES).toEqual(new Set(["en"]));
    expect(CORE_LOCALE_CODES.has("pl")).toBe(false);
  });
});
