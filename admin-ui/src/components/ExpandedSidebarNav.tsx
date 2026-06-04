"use client";

import { Loader } from "@mantine/core";
import { IconDashboard } from "@tabler/icons-react";
import { useI18n } from "@orbiteus/i18n";
import type { SidebarSectionWithIcons } from "@/lib/sidebarDrill";
import type { SidebarIcon } from "@/lib/sidebarIcons";
import SidebarNavSection, { SidebarLeafLink } from "@/components/SidebarNavSection";
import classes from "./SidebarNavSection.module.css";

function SidebarGroupLabel({ children }: { children: React.ReactNode }) {
  return <div className={classes.groupLabel}>{children}</div>;
}

interface Props {
  path: string;
  appSections: SidebarSectionWithIcons[];
  staticSections: SidebarSectionWithIcons[];
  loading: boolean;
  expandedSections: Set<string>;
  onToggleSection: (id: string) => void;
  isActive: (path: string, href: string) => boolean;
  resolveSectionIcon: (key: string) => SidebarIcon | undefined;
}

export default function ExpandedSidebarNav({
  path,
  appSections,
  staticSections,
  loading,
  expandedSections,
  onToggleSection,
  isActive,
  resolveSectionIcon,
}: Props) {
  const { t } = useI18n();
  if (loading) {
    return <Loader size="xs" color="gray" mt="sm" ml="sm" />;
  }

  return (
    <div className={classes.rootPanel} data-testid="sidebar-root-panel">
      <SidebarLeafLink
        href="/"
        label={t("nav.dashboard")}
        icon={<IconDashboard size={18} stroke={1.5} />}
        active={path === "/"}
        compact={false}
      />

      {appSections.length > 0 && (
        <>
          <SidebarGroupLabel>{t("nav.group.apps")}</SidebarGroupLabel>
          {appSections.map((section) => {
            const moduleName = section.id.startsWith("mod:") ? section.id.slice(4) : null;
            return (
              <SidebarNavSection
                key={section.id}
                label={section.label}
                icon={resolveSectionIcon(moduleName ?? section.id)}
                items={section.items}
                path={path}
                opened={expandedSections.has(section.id)}
                onToggle={() => onToggleSection(section.id)}
                isActive={isActive}
              />
            );
          })}
        </>
      )}

      {staticSections.length > 0 && (
        <>
          <SidebarGroupLabel>{t("nav.group.system")}</SidebarGroupLabel>
          {staticSections.map((section) => (
            <SidebarNavSection
              key={section.id}
              label={section.label}
              icon={resolveSectionIcon(section.id)}
              items={section.items}
              path={path}
              opened={expandedSections.has(section.id)}
              onToggle={() => onToggleSection(section.id)}
              isActive={isActive}
            />
          ))}
        </>
      )}
    </div>
  );
}
