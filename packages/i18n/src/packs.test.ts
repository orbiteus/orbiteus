import { describe, expect, it } from "vitest";
import { createTranslator } from "./core";
import { mergeAllCatalogs, mergeMessageCatalogs } from "./packs";
import { buildRuntimeCatalogs, registerLanguagePack } from "./registry";

describe("mergeMessageCatalogs", () => {
  it("later layers override keys", () => {
    expect(
      mergeMessageCatalogs({ "a": "1" }, { "a": "2", "b": "3" }),
    ).toEqual({ a: "2", b: "3" });
  });
});

describe("registerLanguagePack", () => {
  it("extends runtime catalogs for custom locales", () => {
    registerLanguagePack({
      code: "es",
      label: "Español",
      messages: { "common.save": "Guardar" },
    });
    const catalogs = buildRuntimeCatalogs({
      es: { "common.cancel": "Cancelar" },
    });
    const { t } = createTranslator("es", catalogs);
    expect(t("common.save")).toBe("Guardar");
    expect(t("common.cancel")).toBe("Cancelar");
  });
});

describe("mergeAllCatalogs", () => {
  it("merges per language", () => {
    const out = mergeAllCatalogs(
      { en: { x: "en" }, pl: { x: "pl" } },
      { pl: { y: "override" } },
    );
    expect(out.pl).toEqual({ x: "pl", y: "override" });
  });
});
