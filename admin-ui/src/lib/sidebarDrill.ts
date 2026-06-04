import type { SidebarNavSectionConfig } from "@/lib/sidebarNav";
import type { SidebarIcon } from "@/lib/sidebarIcons";

export type SidebarNavItemWithIcon = {
  label: string;
  href: string;
  icon?: SidebarIcon;
};

export type SidebarSectionWithIcons = Omit<SidebarNavSectionConfig, "items"> & {
  items: SidebarNavItemWithIcon[];
};

export function findNavSection(
  sections: SidebarSectionWithIcons[],
  id: string | null,
): SidebarSectionWithIcons | null {
  if (!id) return null;
  return sections.find((s) => s.id === id) ?? null;
}

export function partitionNavSections(sections: SidebarSectionWithIcons[]) {
  const apps = sections.filter((s) => s.id.startsWith("mod:"));
  const system = sections.filter((s) => !s.id.startsWith("mod:"));
  return { apps, system };
}
