import { describe, expect, it } from "vitest";
import {
  MODEL_ICONS,
  ROUTE_ICONS,
  SECTION_ICONS,
  resolveNavItemIcon,
  resolveSectionIcon,
} from "./sidebarIcons";

describe("resolveSectionIcon", () => {
  it("maps module and static section ids", () => {
    expect(resolveSectionIcon("mod:crm")).toBe(SECTION_ICONS.crm);
    expect(resolveSectionIcon("ai")).toBe(SECTION_ICONS.ai);
  });
});

describe("resolveNavItemIcon", () => {
  it("assigns distinct CRM model icons", () => {
    expect(resolveNavItemIcon("/crm/person")).toBe(MODEL_ICONS["crm.person"]);
    expect(resolveNavItemIcon("/crm/lead")).toBe(MODEL_ICONS["crm.lead"]);
    expect(resolveNavItemIcon("/crm/person")).not.toBe(resolveNavItemIcon("/crm/lead"));
  });

  it("assigns distinct AI section icons", () => {
    expect(resolveNavItemIcon("/technical/ai-integration")).toBe(ROUTE_ICONS["/technical/ai-integration"]);
    expect(resolveNavItemIcon("/base/agent")).toBe(MODEL_ICONS["base.agent"]);
    expect(resolveNavItemIcon("/technical/ai-integration")).not.toBe(resolveNavItemIcon("/base/agent"));
  });

  it("uses a different icon for audit log than agent runs", () => {
    expect(resolveNavItemIcon("/technical/audit-log")).toBe(ROUTE_ICONS["/technical/audit-log"]);
    expect(resolveNavItemIcon("/base/agent-run")).toBe(MODEL_ICONS["base.agent-run"]);
    expect(resolveNavItemIcon("/technical/audit-log")).not.toBe(resolveNavItemIcon("/base/agent-run"));
  });
});
