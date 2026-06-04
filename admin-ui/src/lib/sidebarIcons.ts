import {
  IconActivity,
  IconAddressBook,
  IconAdjustments,
  IconApps,
  IconBox,
  IconBriefcase,
  IconBuilding,
  IconClipboardList,
  IconCpu,
  IconFilter,
  IconHistory,
  IconLanguage,
  IconMail,
  IconPaperclip,
  IconRobot,
  IconSettings,
  IconShield,
  IconShieldLock,
  IconSparkles,
  IconStairs,
  IconTable,
  IconTarget,
  IconTools,
  IconUser,
  IconUsers,
  IconUsersGroup,
  IconWebhook,
} from "@tabler/icons-react";

export type SidebarIcon = React.ComponentType<{
  size?: number | string;
  stroke?: number | string;
}>;

/** Section header icons (module slug or static section id). */
export const SECTION_ICONS: Record<string, SidebarIcon> = {
  crm: IconUsers,
  hr: IconBriefcase,
  base: IconBuilding,
  ai: IconCpu,
  settings: IconSettings,
  technical: IconTools,
};

/** Per-model icons keyed by `module.segment` (e.g. `crm.lead`). */
export const MODEL_ICONS: Record<string, SidebarIcon> = {
  "crm.person": IconAddressBook,
  "crm.lead": IconTarget,
  "crm.stage": IconStairs,
  "crm.team": IconUsersGroup,
  "base.user": IconUser,
  "base.role": IconShield,
  "base.model-access": IconShieldLock,
  "base.agent": IconRobot,
  "base.agent-run": IconHistory,
  "base.registry-model": IconBox,
  "base.record-rule": IconFilter,
  "base.config-param": IconAdjustments,
};

/** Static routes outside the auto-CRUD model namespace. */
export const ROUTE_ICONS: Record<string, SidebarIcon> = {
  "/": IconTable,
  "/modules": IconApps,
  "/technical/system-status": IconActivity,
  "/technical/ai-integration": IconSparkles,
  "/connectivity/mail": IconMail,
  "/connectivity/webhooks": IconWebhook,
  "/technical/audit-log": IconClipboardList,
  "/technical/attachments": IconPaperclip,
  "/technical/languages": IconLanguage,
};

export const DEFAULT_MODEL_ICON: SidebarIcon = IconTable;

export function modelKey(moduleName: string, modelName: string): string {
  if (modelName.includes(".")) return modelName;
  return `${moduleName}.${modelName}`;
}

export function resolveSectionIcon(sectionId: string): SidebarIcon {
  const key = sectionId.startsWith("mod:") ? sectionId.slice(4) : sectionId;
  return SECTION_ICONS[key] ?? DEFAULT_MODEL_ICON;
}

export function resolveNavItemIcon(
  href: string,
  moduleName?: string | null,
  modelName?: string | null,
): SidebarIcon {
  const routeIcon = ROUTE_ICONS[href];
  if (routeIcon) return routeIcon;

  if (moduleName && modelName) {
    return MODEL_ICONS[modelKey(moduleName, modelName)] ?? DEFAULT_MODEL_ICON;
  }

  const segment = href.split("/").filter(Boolean);
  if (segment.length >= 2) {
    const [mod, model] = segment;
    return MODEL_ICONS[`${mod}.${model}`] ?? DEFAULT_MODEL_ICON;
  }

  return DEFAULT_MODEL_ICON;
}

export function resolveNavItemIconFromHref(href: string): SidebarIcon {
  return resolveNavItemIcon(href);
}

/** Legacy alias used by static nav item arrays. */
export function iconForHref(href: string): SidebarIcon {
  return resolveNavItemIcon(href);
}
