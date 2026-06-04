export type SidebarNavItem = {
  label: string;
  href: string;
};

export type SidebarNavSectionConfig = {
  id: string;
  label: string;
  items: SidebarNavItem[];
};

export const SIDEBAR_EXPANDED_STORAGE_KEY = "orbiteus.sidebar.expanded.v3";

/** Sections collapsed on first visit (engine / developer surface). */
export const SIDEBAR_COLLAPSED_BY_DEFAULT = new Set(["technical"]);

export function buildDefaultExpandedSections(sectionIds: string[]): Set<string> {
  return new Set(sectionIds.filter((id) => !SIDEBAR_COLLAPSED_BY_DEFAULT.has(id)));
}

export function isNavItemActive(path: string, href: string): boolean {
  if (href === "/") return path === "/";
  return path === href || path.startsWith(`${href}/`);
}

export function findActiveSectionIds(
  path: string,
  sections: SidebarNavSectionConfig[],
): string[] {
  return sections
    .filter((section) => section.items.some((item) => isNavItemActive(path, item.href)))
    .map((section) => section.id);
}

export function hasExpandedSectionStorage(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(SIDEBAR_EXPANDED_STORAGE_KEY) !== null;
}

export function readExpandedSectionIds(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(SIDEBAR_EXPANDED_STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((id): id is string => typeof id === "string"));
  } catch {
    return new Set();
  }
}

export function writeExpandedSectionIds(ids: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      SIDEBAR_EXPANDED_STORAGE_KEY,
      JSON.stringify([...ids]),
    );
  } catch {
    /* ignore quota / private mode */
  }
}

export function mergeExpandedSectionIds(
  current: Set<string>,
  required: Iterable<string>,
): Set<string> {
  const next = new Set(current);
  let changed = false;
  for (const id of required) {
    if (!next.has(id)) {
      next.add(id);
      changed = true;
    }
  }
  return changed ? next : current;
}
