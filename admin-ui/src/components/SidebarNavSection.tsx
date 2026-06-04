"use client";

import Link from "next/link";
import { NavLink, Tooltip } from "@mantine/core";
import classes from "./SidebarNavSection.module.css";

export type SidebarNavSectionItem = {
  label: string;
  href: string;
  icon?: React.ComponentType<{ size?: number | string; stroke?: number | string }>;
};

type SidebarNavSectionProps = {
  label: string;
  icon?: React.ComponentType<{ size?: number | string; stroke?: number | string }>;
  items: SidebarNavSectionItem[];
  path: string;
  opened: boolean;
  onToggle: () => void;
  isActive: (path: string, href: string) => boolean;
};

const navLinkStyles = {
  root: { borderRadius: "var(--mantine-radius-md)", paddingTop: 7, paddingBottom: 7 },
};

function SectionIcon({
  Icon,
}: {
  Icon: React.ComponentType<{ size?: number | string; stroke?: number | string }>;
}) {
  return <Icon size={18} stroke={1.5} />;
}

export default function SidebarNavSection({
  label,
  icon: Icon,
  items,
  path,
  opened,
  onToggle,
  isActive,
}: SidebarNavSectionProps) {
  const sectionActive = items.some((item) => isActive(path, item.href));

  return (
    <NavLink
      label={label}
      leftSection={Icon ? <SectionIcon Icon={Icon} /> : undefined}
      opened={opened}
      onChange={onToggle}
      childrenOffset={28}
      variant={sectionActive ? "light" : "subtle"}
      color={sectionActive ? "dark" : "gray"}
      styles={navLinkStyles}
      mt="xs"
    >
      {items.map((item) => {
        const ItemIcon = item.icon;
        return (
          <NavLink
            key={item.href}
            component={Link}
            href={item.href}
            label={item.label}
            leftSection={
              ItemIcon ? <ItemIcon size={18} stroke={1.5} /> : undefined
            }
            active={isActive(path, item.href)}
            variant="filled"
            styles={navLinkStyles}
          />
        );
      })}
    </NavLink>
  );
}

export function SidebarLeafLink({
  href,
  label,
  icon,
  active,
  compact,
}: {
  href: string;
  label: string;
  icon?: React.ReactNode;
  active: boolean;
  compact: boolean;
}) {
  const link = (
    <NavLink
      component={Link}
      href={href}
      label={compact ? "" : label}
      aria-label={label}
      leftSection={icon}
      active={active}
      variant="filled"
      styles={{ root: { borderRadius: "var(--mantine-radius-sm)" } }}
      className={compact ? classes.compactNav : undefined}
    />
  );

  if (!compact) return link;

  return (
    <Tooltip label={label} position="right" withArrow openDelay={200}>
      {link}
    </Tooltip>
  );
}
