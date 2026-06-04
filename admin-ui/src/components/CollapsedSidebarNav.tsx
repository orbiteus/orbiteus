"use client";

import { Loader, NavLink, Tooltip } from "@mantine/core";
import { IconChevronRight, IconDashboard } from "@tabler/icons-react";
import { useI18n } from "@orbiteus/i18n";
import type { SidebarSectionWithIcons } from "@/lib/sidebarDrill";
import { findNavSection } from "@/lib/sidebarDrill";
import type { SidebarIcon } from "@/lib/sidebarIcons";
import SidebarDrillPanel from "@/components/SidebarDrillPanel";
import { SidebarLeafLink } from "@/components/SidebarNavSection";
import layoutClasses from "@/components/AppShellLayout.module.css";
import classes from "./SidebarNavSection.module.css";

function RailDivider() {
  return <div className={layoutClasses.railDivider} aria-hidden />;
}

function SectionIconButton({
  label,
  icon: Icon,
  active,
  onDrill,
}: {
  label: string;
  icon?: SidebarIcon;
  active: boolean;
  onDrill: () => void;
}) {
  return (
    <Tooltip label={label} position="right" withArrow openDelay={200}>
      <NavLink
        label=""
        aria-label={label}
        leftSection={
          Icon ? <Icon size={18} stroke={1.5} /> : <IconChevronRight size={18} stroke={1.5} />
        }
        variant={active ? "light" : "subtle"}
        color={active ? "dark" : "gray"}
        className={classes.compactNav}
        mt="xs"
        onClick={(e) => {
          e.preventDefault();
          onDrill();
        }}
        styles={{
          root: {
            borderRadius: "var(--mantine-radius-md)",
            paddingTop: 7,
            paddingBottom: 7,
          },
        }}
      />
    </Tooltip>
  );
}

interface Props {
  path: string;
  sections: SidebarSectionWithIcons[];
  appSections: SidebarSectionWithIcons[];
  staticSections: SidebarSectionWithIcons[];
  loading: boolean;
  drillSectionId: string | null;
  onDrillSection: (id: string | null) => void;
  isActive: (path: string, href: string) => boolean;
  resolveSectionIcon: (key: string) => SidebarIcon | undefined;
}

export default function CollapsedSidebarNav({
  path,
  sections,
  appSections,
  staticSections,
  loading,
  drillSectionId,
  onDrillSection,
  isActive,
  resolveSectionIcon,
}: Props) {
  const { t } = useI18n();
  const drilled = findNavSection(sections, drillSectionId);

  if (loading) {
    return <Loader size="xs" color="gray" mt="sm" mx="auto" />;
  }

  if (drilled) {
    const moduleName = drilled.id.startsWith("mod:") ? drilled.id.slice(4) : null;
    return (
      <SidebarDrillPanel
        section={drilled}
        sectionIcon={resolveSectionIcon(moduleName ?? drilled.id)}
        path={path}
        compact
        onBack={() => onDrillSection(null)}
        isActive={isActive}
      />
    );
  }

  return (
    <div className={classes.rootPanel}>
      <SidebarLeafLink
        href="/"
        label={t("nav.dashboard")}
        icon={<IconDashboard size={18} stroke={1.5} />}
        active={path === "/"}
        compact
      />

      {appSections.length > 0 && (
        <>
          <RailDivider />
          {appSections.map((section) => (
            <SectionIconButton
              key={section.id}
              label={section.label}
              icon={resolveSectionIcon(
                section.id.startsWith("mod:") ? section.id.slice(4) : section.id,
              )}
              active={section.items.some((item) => isActive(path, item.href))}
              onDrill={() => onDrillSection(section.id)}
            />
          ))}
        </>
      )}

      {staticSections.length > 0 && (
        <>
          <RailDivider />
          {staticSections.map((section) => (
            <SectionIconButton
              key={section.id}
              label={section.label}
              icon={resolveSectionIcon(section.id)}
              active={section.items.some((item) => isActive(path, item.href))}
              onDrill={() => onDrillSection(section.id)}
            />
          ))}
        </>
      )}
    </div>
  );
}
