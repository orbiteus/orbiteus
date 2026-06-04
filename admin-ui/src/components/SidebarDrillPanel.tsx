"use client";

import Link from "next/link";
import { Group, NavLink, Text, Tooltip, UnstyledButton } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useI18n } from "@orbiteus/i18n";
import type { SidebarSectionWithIcons } from "@/lib/sidebarDrill";
import type { SidebarIcon } from "@/lib/sidebarIcons";
import classes from "./SidebarNavSection.module.css";

export type SidebarDrillPanelProps = {
  section: SidebarSectionWithIcons;
  sectionIcon?: SidebarIcon;
  path: string;
  compact: boolean;
  onBack: () => void;
  isActive: (path: string, href: string) => boolean;
};

const navLinkStyles = {
  root: { borderRadius: "var(--mantine-radius-sm)", paddingTop: 6, paddingBottom: 6 },
};

const tooltipProps = {
  position: "right" as const,
  withArrow: true,
  openDelay: 200,
};

function CompactTooltip({
  label,
  children,
}: {
  label: string;
  children: React.ReactElement;
}) {
  return (
    <Tooltip label={label} {...tooltipProps}>
      {children}
    </Tooltip>
  );
}

export default function SidebarDrillPanel({
  section,
  sectionIcon: SectionIcon,
  path,
  compact,
  onBack,
  isActive,
}: SidebarDrillPanelProps) {
  const { t } = useI18n();
  const backControl = (
    <UnstyledButton
      className={classes.backRow}
      onClick={onBack}
      aria-label={`Back to main menu from ${section.label}`}
    >
      <IconArrowLeft size={16} stroke={1.5} />
      {!compact && (
        <Text size="sm" c="dimmed">
          {t("common.back")}
        </Text>
      )}
    </UnstyledButton>
  );

  const parentControl = compact ? (
    <div className={classes.parentHeader}>
      {SectionIcon ? <SectionIcon size={20} stroke={1.5} /> : null}
    </div>
  ) : (
    <Group gap="xs" className={classes.parentHeader} wrap="nowrap">
      {SectionIcon ? <SectionIcon size={20} stroke={1.5} /> : null}
      <Text size="sm" fw={600} lineClamp={1}>
        {section.label}
      </Text>
    </Group>
  );

  return (
    <div
      className={classes.drillPanel}
      data-compact={compact || undefined}
      data-testid="sidebar-drill-panel"
    >
      {compact ? (
        <CompactTooltip label={t("common.back")}>{backControl}</CompactTooltip>
      ) : (
        backControl
      )}

      {compact ? (
        <CompactTooltip label={section.label}>{parentControl}</CompactTooltip>
      ) : (
        parentControl
      )}

      <div className={classes.subLevelFrame}>
        {section.items.map((item) => {
          const ItemIcon = item.icon;
          const link = (
            <NavLink
              component={Link}
              href={item.href}
              label={compact ? "" : item.label}
              aria-label={item.label}
              leftSection={
                ItemIcon ? <ItemIcon size={18} stroke={1.5} /> : undefined
              }
              active={isActive(path, item.href)}
              variant="subtle"
              color="dark"
              className={compact ? classes.compactNav : undefined}
              styles={navLinkStyles}
            />
          );

          if (!compact) {
            return <div key={item.href}>{link}</div>;
          }

          return (
            <CompactTooltip key={item.href} label={item.label}>
              {link}
            </CompactTooltip>
          );
        })}
      </div>
    </div>
  );
}
