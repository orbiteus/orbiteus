import { describe, expect, it } from "vitest";
import { shouldBlockAuthenticatedShell } from "./i18nShellGate";

describe("shouldBlockAuthenticatedShell", () => {
  it("never blocks public routes", () => {
    expect(
      shouldBlockAuthenticatedShell({
        isPublicRoute: true,
        hydrated: false,
        hasCatalog: false,
      }),
    ).toBe(false);
  });

  it("blocks protected routes until auth hydrates", () => {
    expect(
      shouldBlockAuthenticatedShell({
        isPublicRoute: false,
        hydrated: false,
        hasCatalog: false,
      }),
    ).toBe(true);
  });

  it("blocks protected routes until the API catalog is loaded", () => {
    expect(
      shouldBlockAuthenticatedShell({
        isPublicRoute: false,
        hydrated: true,
        hasCatalog: false,
      }),
    ).toBe(true);
    expect(
      shouldBlockAuthenticatedShell({
        isPublicRoute: false,
        hydrated: true,
        hasCatalog: true,
      }),
    ).toBe(false);
  });
});
