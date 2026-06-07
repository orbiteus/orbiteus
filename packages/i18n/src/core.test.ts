import { describe, expect, it } from "vitest";
import { createTranslator, normalizeUiLanguage } from "./core";
import { TEST_MESSAGE_CATALOGS } from "./fixtures";

describe("normalizeUiLanguage", () => {
  it("accepts supported codes", () => {
    expect(normalizeUiLanguage("pl")).toBe("pl");
    expect(normalizeUiLanguage("de")).toBe("de");
  });

  it("maps browser tags", () => {
    expect(normalizeUiLanguage("pl-PL")).toBe("pl");
    expect(normalizeUiLanguage("fr-FR")).toBe("fr");
  });

  it("falls back to en", () => {
    expect(normalizeUiLanguage("xx")).toBe("en");
  });
});

describe("createTranslator", () => {
  it("interpolates variables", () => {
    const { t } = createTranslator("en", TEST_MESSAGE_CATALOGS);
    expect(t("form.editTitle", { title: "User" })).toBe("Edit — User");
  });

  it("uses Polish catalog", () => {
    const { t } = createTranslator("pl", TEST_MESSAGE_CATALOGS);
    expect(t("common.save")).toBe("Zapisz");
  });

  it("falls back to English for missing keys", () => {
    const { t } = createTranslator("pl", TEST_MESSAGE_CATALOGS);
    expect(t("common.cancel")).toBe("Cancel");
  });

  it("falls back to shell gap-fill when API catalog is stale", () => {
    const { t } = createTranslator("en", { en: { "common.save": "Save" } });
    expect(t("mail.placeholderHostHint")).toContain("placeholder");
    expect(t("mail.placeholderHostHint")).not.toBe("mail.placeholderHostHint");
  });
});
