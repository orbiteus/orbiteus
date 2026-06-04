import { describe, expect, it } from "vitest";
import { buildPublicPageCatalogEn } from "./index";

describe("buildPublicPageCatalogEn", () => {
  it("includes login and nav shell keys", () => {
    const catalog = buildPublicPageCatalogEn();
    expect(catalog["auth.signIn"]).toBeTruthy();
    expect(catalog["login.welcomeTitle"]).toBeTruthy();
    expect(catalog["nav.dashboard"]).toBe("Dashboard");
  });
});
