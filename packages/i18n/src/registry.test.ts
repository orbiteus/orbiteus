import { describe, expect, it } from "vitest";
import { createTranslator } from "./core";
import { buildRuntimeCatalogs } from "./registry";

describe("buildRuntimeCatalogs (API-driven)", () => {
  it("uses runtime overrides as the translated catalog", () => {
    const catalogs = buildRuntimeCatalogs({
      pl: { "common.save": "Zapisz", "nav.dashboard": "Pulpit" },
    });
    const { t } = createTranslator("pl", catalogs);
    expect(t("common.save")).toBe("Zapisz");
    expect(t("nav.dashboard")).toBe("Pulpit");
  });

  it("falls back to English keys from overrides when locale partial", () => {
    const catalogs = buildRuntimeCatalogs({
      en: { "common.save": "Save", "common.cancel": "Cancel" },
      pl: { "common.save": "Zapisz" },
    });
    const { t } = createTranslator("pl", catalogs);
    expect(t("common.save")).toBe("Zapisz");
    expect(t("common.cancel")).toBe("Cancel");
  });

  it("returns key when no catalog loaded", () => {
    const { t } = createTranslator("pl", buildRuntimeCatalogs());
    expect(t("unknown.key")).toBe("unknown.key");
  });

  it("fills missing nav keys from shell fallbacks when API catalog is stale", () => {
    const catalogs = buildRuntimeCatalogs({
      en: { "nav.dashboard": "Dashboard" },
    });
    const { t } = createTranslator("en", catalogs);
    expect(t("nav.technical.languages")).toBe("Languages");
  });
});
