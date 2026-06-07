import { describe, expect, it } from "vitest";
import { afterEach, describe, expect, it } from "vitest";
import {
  buildDefaultExpandedSections,
  findActiveSectionIds,
  initializeExpandedSectionsIfAbsent,
  isNavItemActive,
  mergeExpandedSectionIds,
  SIDEBAR_COLLAPSED_BY_DEFAULT,
  SIDEBAR_EXPANDED_STORAGE_KEY,
  type SidebarNavSectionConfig,
} from "./sidebarNav";

const SECTIONS: SidebarNavSectionConfig[] = [
  {
    id: "mod:crm",
    label: "CRM",
    items: [
      { label: "Leads", href: "/crm/lead" },
      { label: "People", href: "/crm/person" },
    ],
  },
  {
    id: "ai",
    label: "AI",
    items: [
      { label: "Agents", href: "/base/agent" },
      { label: "Agent runs", href: "/base/agent-run" },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    items: [{ label: "Users", href: "/base/user" }],
  },
  {
    id: "technical",
    label: "Technical",
    items: [{ label: "Models", href: "/base/registry-model" }],
  },
];

describe("isNavItemActive", () => {
  it("matches exact paths and nested routes", () => {
    expect(isNavItemActive("/crm/lead", "/crm/lead")).toBe(true);
    expect(isNavItemActive("/crm/lead/abc", "/crm/lead")).toBe(true);
    expect(isNavItemActive("/crm/person", "/crm/lead")).toBe(false);
  });

  it("treats dashboard as exact match only", () => {
    expect(isNavItemActive("/", "/")).toBe(true);
    expect(isNavItemActive("/crm/lead", "/")).toBe(false);
  });
});

describe("findActiveSectionIds", () => {
  it("returns sections containing the active route", () => {
    expect(findActiveSectionIds("/crm/lead/new", SECTIONS)).toEqual(["mod:crm"]);
    expect(findActiveSectionIds("/base/agent-run/1", SECTIONS)).toEqual(["ai"]);
    expect(findActiveSectionIds("/base/registry-model", SECTIONS)).toEqual(["technical"]);
  });

  it("returns empty list when nothing matches", () => {
    expect(findActiveSectionIds("/modules", SECTIONS)).toEqual([]);
  });
});

describe("mergeExpandedSectionIds", () => {
  it("adds missing ids without replacing the set instance when unchanged", () => {
    const current = new Set(["ai"]);
    expect(mergeExpandedSectionIds(current, ["ai"])).toBe(current);
  });

  it("returns a new set when required ids are missing", () => {
    const current = new Set(["ai"]);
    const next = mergeExpandedSectionIds(current, ["mod:crm"]);
    expect(next).toEqual(new Set(["ai", "mod:crm"]));
    expect(next).not.toBe(current);
  });
});

describe("buildDefaultExpandedSections", () => {
  it("expands all sections except technical by default", () => {
    const ids = ["mod:crm", "ai", "settings", "technical"];
    expect(buildDefaultExpandedSections(ids)).toEqual(
      new Set(["mod:crm", "ai", "settings"]),
    );
    expect(SIDEBAR_COLLAPSED_BY_DEFAULT.has("technical")).toBe(true);
  });
});

describe("initializeExpandedSectionsIfAbsent", () => {
  afterEach(() => {
    window.localStorage.removeItem(SIDEBAR_EXPANDED_STORAGE_KEY);
  });

  it("persists defaults once and returns null on subsequent calls", () => {
    const ids = ["mod:crm", "ai", "settings", "technical"];
    const first = initializeExpandedSectionsIfAbsent(ids);
    expect(first).toEqual(new Set(["mod:crm", "ai", "settings"]));
    expect(window.localStorage.getItem(SIDEBAR_EXPANDED_STORAGE_KEY)).toBeTruthy();

    const second = initializeExpandedSectionsIfAbsent(ids);
    expect(second).toBeNull();
  });

  it("returns null when section list is empty", () => {
    expect(initializeExpandedSectionsIfAbsent([])).toBeNull();
  });
});
