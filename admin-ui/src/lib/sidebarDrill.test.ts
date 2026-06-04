import { describe, expect, it } from "vitest";
import { findNavSection, partitionNavSections } from "./sidebarDrill";
import type { SidebarSectionWithIcons } from "./sidebarDrill";

const SECTIONS: SidebarSectionWithIcons[] = [
  { id: "mod:crm", label: "CRM", items: [{ label: "Leads", href: "/crm/lead" }] },
  { id: "ai", label: "AI", items: [{ label: "Agents", href: "/base/agent" }] },
];

describe("sidebarDrill", () => {
  it("finds section by id", () => {
    expect(findNavSection(SECTIONS, "mod:crm")?.label).toBe("CRM");
    expect(findNavSection(SECTIONS, "missing")).toBeNull();
  });

  it("partitions apps vs system sections", () => {
    const { apps, system } = partitionNavSections(SECTIONS);
    expect(apps).toHaveLength(1);
    expect(system).toHaveLength(1);
  });
});
