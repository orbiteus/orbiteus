import { describe, expect, it } from "vitest";
import { isAllowedAppPath, isKnownModel } from "./knownModels";
import type { UiConfig } from "@/lib/api";

const cfg: UiConfig = {
  modules: [
    {
      name: "base",
      label: "Base",
      category: "Core",
      models: [
        {
          name: "base.user",
          label: "User",
          fields: [],
          views: {},
        },
      ],
    },
  ],
};

describe("knownModels", () => {
  it("allows base user routes", () => {
    expect(isKnownModel(cfg, "base", "user")).toBe(true);
    expect(isAllowedAppPath("/base/user", cfg)).toBe(true);
    expect(isAllowedAppPath("/base/user/new", cfg)).toBe(true);
  });

  it("blocks removed crm routes", () => {
    expect(isKnownModel(cfg, "crm", "lead")).toBe(false);
    expect(isAllowedAppPath("/crm/lead", cfg)).toBe(false);
    expect(isAllowedAppPath("/crm/lead/new", cfg)).toBe(false);
  });

  it("allows ui_hidden models when present in ui-config", () => {
    const withTechnical: UiConfig = {
      modules: [
        {
          ...cfg.modules[0],
          models: [
            ...cfg.modules[0].models,
            {
              name: "base.registry-model",
              label: "Registry Model",
              ui_hidden: true,
              fields: [],
              views: {},
            },
            {
              name: "base.record-rule",
              label: "Record Rule",
              ui_hidden: true,
              fields: [],
              views: {},
            },
          ],
        },
      ],
    };
    expect(isKnownModel(withTechnical, "base", "registry-model")).toBe(true);
    expect(isAllowedAppPath("/base/registry-model", withTechnical)).toBe(true);
    expect(isAllowedAppPath("/base/record-rule", withTechnical)).toBe(true);
    expect(isKnownModel(cfg, "base", "registry-model")).toBe(false);
  });

  it("allows static technical paths", () => {
    expect(isAllowedAppPath("/technical/attachments", cfg)).toBe(true);
    expect(isAllowedAppPath("/technical/languages", cfg)).toBe(true);
  });
});
