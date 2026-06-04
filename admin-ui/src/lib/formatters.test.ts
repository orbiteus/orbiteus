import { describe, expect, it } from "vitest";
import {
  displayMany2oneCell,
  formatListDate,
  formatMoney,
  humanizeRegistrySlugForUi,
} from "./formatters";

describe("humanizeRegistrySlugForUi", () => {
  it("strips registry- / record- prefixes before title-casing", () => {
    expect(humanizeRegistrySlugForUi("registry-model")).toBe("Model");
    expect(humanizeRegistrySlugForUi("REGISTRY-MODEL")).toBe("Model");
    expect(humanizeRegistrySlugForUi("model-access")).toBe("Model Access");
    expect(humanizeRegistrySlugForUi("record-rule")).toBe("Rule");
  });

  it("does not change non-registry slugs", () => {
    expect(humanizeRegistrySlugForUi("crm-lead")).toBe("Crm Lead");
    expect(humanizeRegistrySlugForUi("partner")).toBe("Partner");
  });
});

describe("formatListDate", () => {
  it("renders an em-dash for null / empty", () => {
    expect(formatListDate(null)).toBe("—");
    expect(formatListDate("")).toBe("—");
    expect(formatListDate(undefined)).toBe("—");
  });

  it("returns the raw input on an invalid date string", () => {
    expect(formatListDate("totally-not-a-date")).toBe("totally-not-a-date");
  });

  it("formats a valid ISO timestamp as YYYY-MM-DD HH:mm", () => {
    const out = formatListDate("2025-03-04T12:34:56Z");
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });
});

describe("formatMoney (legacy helper, kept for non-FieldMeta callers)", () => {
  it("returns em-dash on null / empty", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney("")).toBe("—");
  });

  it("falls back to the raw value when input is non-numeric", () => {
    expect(formatMoney("abc")).toBe("abc");
  });

  it("formats numbers with the supplied currency code", () => {
    // `Intl.NumberFormat` may render the currency as a symbol (€)
    // or as an ISO code, depending on the runtime locale. We assert
    // on the numeric portion only — the currency presence is covered
    // by the dedicated `MonetaryField` widget tests.
    const out = formatMoney(1234.5, "EUR");
    expect(out).toMatch(/1[ ,.\u00A0]?234/);
  });

  it("defaults to PLN when no currency is supplied", () => {
    expect(formatMoney(50)).toContain("PLN");
  });
});

describe("displayMany2oneCell — DoD §9.4 contract", () => {
  it("returns `<key>__name` when present", () => {
    const out = displayMany2oneCell(
      { person_id: "uuid-here", person_id__name: "Acme Corp" },
      "person_id",
    );
    expect(out).toBe("Acme Corp");
  });

  it("falls back to `<key>__display` when present", () => {
    const out = displayMany2oneCell(
      { person_id: "uuid-here", person_id__display: "Acme display" },
      "person_id",
    );
    expect(out).toBe("Acme display");
  });

  it("truncates the raw UUID when neither __name nor __display is present", () => {
    const id = "06548faf-5f0c-4b68-b4bb-84aa53a3d81d";
    const out = displayMany2oneCell({ person_id: id }, "person_id");
    expect(out).toBe(id.slice(0, 8) + "…");
  });

  it("returns em-dash on null / empty", () => {
    expect(displayMany2oneCell({}, "person_id")).toBe("—");
    expect(displayMany2oneCell({ person_id: null }, "person_id")).toBe("—");
    expect(displayMany2oneCell({ person_id: "" }, "person_id")).toBe("—");
  });

  it("prefers __name over __display when both exist", () => {
    const out = displayMany2oneCell(
      {
        person_id: "uuid",
        person_id__name: "Name wins",
        person_id__display: "Display loses",
      },
      "person_id",
    );
    expect(out).toBe("Name wins");
  });
});
