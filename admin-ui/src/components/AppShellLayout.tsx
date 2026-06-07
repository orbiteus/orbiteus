"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppShell, Group, Text, ScrollArea, Burger, Menu, ActionIcon, UnstyledButton, Tooltip } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { usePathname } from "next/navigation";
import {
  IconLogout, IconSearch, IconSparkles, IconUser,
  IconLayoutSidebarLeftExpand, IconLayoutSidebarLeftCollapse,
} from "@tabler/icons-react";
import { useBranding } from "@/lib/branding";
import { api } from "@/lib/api";
import { humanizeRegistrySlugForUi } from "@/lib/formatters";
import {
  invalidateModuleRuntimeCaches,
  MODULES_CHANGED_EVENT,
} from "@/lib/moduleRuntime";
import { useUiConfig } from "@/lib/queries/uiConfig";
import {
  resolveNavItemIcon,
  resolveSectionIcon,
} from "@/lib/sidebarIcons";
import {
  findActiveSectionIds,
  hasExpandedSectionStorage,
  initializeExpandedSectionsIfAbsent,
  isNavItemActive,
  mergeExpandedSectionIds,
  readExpandedSectionIds,
  writeExpandedSectionIds,
  type SidebarNavSectionConfig,
} from "@/lib/sidebarNav";
import CommandPalette from "@/components/CommandPalette";
import PageBreadcrumbs from "@/components/PageBreadcrumbs";
import ExpandedSidebarNav from "@/components/ExpandedSidebarNav";
import CollapsedSidebarNav from "@/components/CollapsedSidebarNav";
import classes from "@/components/AppShellLayout.module.css";
import type { SidebarSectionWithIcons } from "@/lib/sidebarDrill";
import {
  isSidebarExpanded,
  NAV_WIDTH_COLLAPSED,
  NAV_WIDTH_EXPANDED,
  readSidebarOpen,
  writeSidebarOpen,
} from "@/lib/sidebarRail";
import dynamic from "next/dynamic";
import { useI18n } from "@orbiteus/i18n";

const AIChatPanel = dynamic(
  () => import("@/orbiteus-ui/ai/AIChatPanel").then((m) => ({ default: m.AIChatPanel })),
  { ssr: false },
);

const AI_NAV_LINKS = [
  { href: "/technical/ai-integration", key: "nav.ai.integration" },
  { href: "/technical/agent-console", key: "nav.ai.agentConsole" },
  { href: "/base/agent", key: "nav.ai.agents" },
  { href: "/base/agent-run", key: "nav.ai.agentRuns" },
];

const SETTINGS_NAV_LINKS = [
  { href: "/base/user", key: "nav.settings.users" },
  { href: "/base/role", key: "nav.settings.roles" },
  { href: "/base/model-access", key: "nav.settings.access" },
  { href: "/connectivity/mail", key: "nav.settings.mail" },
  { href: "/connectivity/webhooks", key: "nav.settings.webhooks" },
  { href: "/modules", key: "nav.settings.modules" },
];

const TECHNICAL_NAV_LINKS = [
  { href: "/technical/system-status", key: "nav.technical.status" },
  { href: "/technical/attachments", key: "nav.technical.attachments" },
  { href: "/base/registry-model", key: "nav.technical.models" },
  { href: "/base/record-rule", key: "nav.technical.rules" },
  { href: "/base/config-param", key: "nav.technical.parameters" },
  { href: "/technical/audit-log", key: "nav.technical.audit" },
  { href: "/technical/languages", key: "nav.technical.languages" },
];

function useStaticNavSections(t: (key: string) => string): SidebarNavSectionConfig[] {
  return useMemo(
    () => [
      {
        id: "ai",
        label: t("nav.section.ai"),
        items: AI_NAV_LINKS.map((item) => ({ label: t(item.key), href: item.href })),
      },
      {
        id: "settings",
        label: t("nav.section.settings"),
        items: SETTINGS_NAV_LINKS.map((item) => ({ label: t(item.key), href: item.href })),
      },
      {
        id: "technical",
        label: t("nav.section.technical"),
        items: TECHNICAL_NAV_LINKS.map((item) => ({ label: t(item.key), href: item.href })),
      },
    ],
    [t],
  );
}

function modelHref(moduleName: string, modelName: string): string {
  const segment = modelName.startsWith(`${moduleName}.`)
    ? modelName.slice(moduleName.length + 1)
    : modelName;
  return `/${moduleName}/${segment}`;
}

function modelLabel(modelName: string): string {
  const last = modelName.split(".").pop() ?? modelName;
  return humanizeRegistrySlugForUi(last);
}

// Modules hidden from main nav (internal/system)
const HIDDEN_MODULES = new Set(["auth", "base"]);

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const [opened, { toggle }] = useDisclosure();
  const [aiPanelOpen, { open: openAiPanel, close: closeAiPanel }] = useDisclosure(false);
  const [navOpen, setNavOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(() => new Set());
  const [drillSectionId, setDrillSectionId] = useState<string | null>(null);
  const dismissedDrillForPath = useRef<string | null>(null);
  const path = usePathname();
  const isPublicRoute = path === "/login" || path === "/welcome";
  const { t } = useI18n();
  const STATIC_SECTIONS = useStaticNavSections(t);
  const branding = useBranding();
  const uiConfigQuery = useUiConfig(!isPublicRoute);
  const modules = uiConfigQuery.data?.modules ?? [];
  const navLoading = path !== "/login" && path !== "/welcome" && uiConfigQuery.isLoading && !uiConfigQuery.data;

  useEffect(() => {
    setNavOpen(readSidebarOpen());
  }, []);

  useEffect(() => {
    if (path === "/login" || path === "/welcome") return;
    const onModulesChanged = () => {
      invalidateModuleRuntimeCaches();
    };
    window.addEventListener(MODULES_CHANGED_EVENT, onModulesChanged);
    return () => window.removeEventListener(MODULES_CHANGED_EVENT, onModulesChanged);
  }, [path]);

  const appSections = useMemo(() => {
    return modules
      .filter((mod) => !HIDDEN_MODULES.has(mod.name))
      .map((mod) => ({ ...mod, models: mod.models.filter((m) => m.fields.length > 0) }))
      .filter((mod) => mod.models.length > 0)
      .map((mod) => ({
        id: `mod:${mod.name}`,
        label: mod.label,
        items: mod.models.map((model) => ({
          label: modelLabel(model.name),
          href: modelHref(mod.name, model.name),
        })),
      }));
  }, [modules]);

  const navSections = useMemo(
    () => [...appSections, ...STATIC_SECTIONS],
    [appSections, STATIC_SECTIONS],
  );

  const navSectionIdsKey = useMemo(
    () => navSections.map((section) => section.id).join("|"),
    [navSections],
  );

  const sectionsWithIcons = useMemo((): SidebarSectionWithIcons[] => {
    return navSections.map((section) => {
      const moduleName = section.id.startsWith("mod:") ? section.id.slice(4) : null;
      return {
        ...section,
        items: section.items.map((item) => ({
          ...item,
          icon: resolveNavItemIcon(item.href, moduleName),
        })),
      };
    });
  }, [navSections]);

  const appSectionsWithIcons = useMemo(
    () => sectionsWithIcons.filter((s) => s.id.startsWith("mod:")),
    [sectionsWithIcons],
  );

  const staticSectionsWithIcons = useMemo(
    () => sectionsWithIcons.filter((s) => !s.id.startsWith("mod:")),
    [sectionsWithIcons],
  );

  const navExpanded = isSidebarExpanded(navOpen);

  useEffect(() => {
    if (hasExpandedSectionStorage()) {
      setExpandedSections(readExpandedSectionIds());
    }
  }, []);

  useEffect(() => {
    const defaults = initializeExpandedSectionsIfAbsent(
      navSectionIdsKey ? navSectionIdsKey.split("|") : [],
    );
    if (defaults) setExpandedSections(defaults);
  }, [navSectionIdsKey]);

  useEffect(() => {
    const activeIds = findActiveSectionIds(path, navSections);
    setExpandedSections((prev) => {
      const next = mergeExpandedSectionIds(prev, activeIds);
      if (next !== prev) writeExpandedSectionIds(next);
      return next;
    });
  }, [path, navSections]);

  useEffect(() => {
    if (navExpanded) {
      setDrillSectionId(null);
      dismissedDrillForPath.current = null;
      return;
    }
    const activeIds = findActiveSectionIds(path, navSections);
    const activeId = activeIds[0];
    if (!activeId) {
      dismissedDrillForPath.current = null;
      return;
    }
    if (dismissedDrillForPath.current === path) return;
    setDrillSectionId(activeId);
  }, [path, navSections, navExpanded]);

  useEffect(() => {
    if (!navExpanded) dismissedDrillForPath.current = null;
  }, [path, navExpanded]);

  if (isPublicRoute) return <>{children}</>;

  async function logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      /* even if the server rejects, fall through and force redirect */
    }
    window.location.assign("/login");
  }

  function handleDrillSection(id: string | null) {
    if (id === null) {
      dismissedDrillForPath.current = path;
    }
    setDrillSectionId(id);
  }

  function toggleSection(id: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      writeExpandedSectionIds(next);
      return next;
    });
  }

  function toggleNavOpen() {
    setNavOpen((prev) => {
      const next = !prev;
      writeSidebarOpen(next);
      return next;
    });
  }

  return (
    <AppShell
      header={{ height: 52 }}
      navbar={{
        width: navExpanded ? NAV_WIDTH_EXPANDED : NAV_WIDTH_COLLAPSED,
        breakpoint: "sm",
        collapsed: { mobile: !opened },
      }}
      padding="md"
      styles={{
        navbar: {
          background: "var(--mantine-color-body)",
          borderRight: "1px solid var(--mantine-color-default-border)",
          transition: "width 200ms ease",
          overflow: "hidden",
        },
        main: { background: "var(--mantine-color-body)" },
      }}
    >
      <AppShell.Header
        style={{
          background: "var(--mantine-color-body)",
          borderBottom: "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            {branding.hydrated && branding.logo_url
              ? <img src={branding.logo_url} alt={branding.name} style={{ height: 30 }} />
              : <Text fw={700} size="lg">{branding.name}</Text>
            }
          </Group>
          <Group gap="sm">
            <UnstyledButton
              onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }))}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 12px",
                borderRadius: "var(--mantine-radius-sm)",
                background: "var(--mantine-color-default)",
                border: "1px solid var(--mantine-color-default-border)",
                cursor: "pointer",
              }}
            >
              <IconSearch size={15} stroke={1.5} color="var(--mantine-color-gray-6)" />
              <Text size="sm" c="dimmed">{t("nav.searchActions")}</Text>
              <Text size="sm" c="dimmed" style={{ fontFamily: "monospace", marginLeft: 4 }}>⌘K</Text>
            </UnstyledButton>

            <ActionIcon
              variant="subtle"
              color="gray"
              size="lg"
              onClick={openAiPanel}
              aria-label={t("common.assistant")}
            >
              <IconSparkles size={18} />
            </ActionIcon>

            <Menu position="bottom-end" withArrow>
              <Menu.Target>
                <ActionIcon variant="subtle" color="gray" size="lg">
                  <IconUser size={18} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconLogout size={14} />} color="red" onClick={logout}>
                  {t("auth.logout")}
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar
        p={navExpanded ? "sm" : "xs"}
        className={classes.rail}
        style={{ display: "flex", flexDirection: "column" }}
      >
        <ScrollArea
          style={{ flex: 1 }}
          className={classes.sidebarScroll}
          type="hover"
          scrollbarSize={6}
          offsetScrollbars
        >
          {navExpanded ? (
            <ExpandedSidebarNav
              path={path}
              appSections={appSectionsWithIcons}
              staticSections={staticSectionsWithIcons}
              loading={navLoading}
              expandedSections={expandedSections}
              onToggleSection={toggleSection}
              isActive={isNavItemActive}
              resolveSectionIcon={resolveSectionIcon}
            />
          ) : (
            <CollapsedSidebarNav
              path={path}
              sections={sectionsWithIcons}
              appSections={appSectionsWithIcons}
              staticSections={staticSectionsWithIcons}
              loading={navLoading}
              drillSectionId={drillSectionId}
              onDrillSection={handleDrillSection}
              isActive={isNavItemActive}
              resolveSectionIcon={resolveSectionIcon}
            />
          )}
        </ScrollArea>

        <div className={classes.pinBar}>
          <Group gap="xs" wrap="nowrap" justify={navExpanded ? "flex-start" : "center"}>
            <Tooltip
              label={navExpanded ? t("nav.collapseMenu") : t("nav.expand")}
              position="right"
              disabled={navExpanded}
            >
              <ActionIcon
                variant="subtle"
                color="gray"
                size="lg"
                aria-label={navExpanded ? t("nav.collapseMenu") : t("nav.expand")}
                aria-expanded={navExpanded}
                onClick={toggleNavOpen}
              >
                {navExpanded ? (
                  <IconLayoutSidebarLeftCollapse size={18} />
                ) : (
                  <IconLayoutSidebarLeftExpand size={18} />
                )}
              </ActionIcon>
            </Tooltip>
            {navExpanded && (
              <Text size="sm" c="dimmed">
                {t("nav.collapse")}
              </Text>
            )}
          </Group>
        </div>
      </AppShell.Navbar>

      <AppShell.Main>
        <PageBreadcrumbs />
        {children}
      </AppShell.Main>

      {path !== "/login" && path !== "/welcome" && <CommandPalette />}

      <AIChatPanel
        scope="global"
        opened={aiPanelOpen}
        onClose={closeAiPanel}
        title={t("common.assistant")}
        stream
      />
    </AppShell>
  );
}
