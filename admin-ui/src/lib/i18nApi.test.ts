import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, fetchUiLocales, fetchUiMessages } from "./api";

describe("i18n API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchUiLocales parses locales array", async () => {
    vi.spyOn(api, "get").mockResolvedValue({
      data: {
        locales: [
          { code: "en", label: "English", dayjs: "en", source: "core", module: "base" },
          { code: "pl", label: "Polski", dayjs: "pl", source: "module", module: "locales" },
        ],
      },
    });

    const locales = await fetchUiLocales();
    expect(locales).toHaveLength(2);
    expect(locales[0].code).toBe("en");
    expect(locales[1].label).toBe("Polski");
  });

  it("fetchUiMessages returns message map", async () => {
    vi.spyOn(api, "get").mockResolvedValue({
      data: {
        lang: "pl",
        messages: { "common.save": "Zapisz", "nav.dashboard": "Pulpit" },
      },
    });

    const messages = await fetchUiMessages("pl");
    expect(messages["common.save"]).toBe("Zapisz");
    expect(api.get).toHaveBeenCalledWith("/base/i18n/messages/pl");
  });
});
