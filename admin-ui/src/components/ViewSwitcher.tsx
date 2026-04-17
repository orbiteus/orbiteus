"use client";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { SegmentedControl, Group, Text } from "@mantine/core";
import {
  IconList, IconLayoutKanban, IconCalendar,
  IconChartBar, IconTable, IconActivity,
} from "@tabler/icons-react";

export type ViewType = "list" | "kanban" | "calendar" | "graph" | "pivot" | "activities";

const VIEW_META: Record<ViewType, { icon: React.ReactNode; label: string }> = {
  list:       { icon: <IconList size={16} />,           label: "List" },
  kanban:     { icon: <IconLayoutKanban size={16} />,   label: "Kanban" },
  calendar:   { icon: <IconCalendar size={16} />,       label: "Calendar" },
  graph:      { icon: <IconChartBar size={16} />,       label: "Chart" },
  pivot:      { icon: <IconTable size={16} />,          label: "Pivot" },
  activities: { icon: <IconActivity size={16} />,       label: "Activities" },
};

interface Props {
  available: ViewType[];
  current: ViewType;
}

export function useCurrentView(defaultView: ViewType = "list"): ViewType {
  const params = useSearchParams();
  return (params.get("view") as ViewType) ?? defaultView;
}

export default function ViewSwitcher({ available, current }: Props) {
  const router = useRouter();
  const pathname = usePathname();

  if (available.length <= 1) return null;

  return (
    <SegmentedControl
      size="xs"
      value={current}
      onChange={(v) => router.push(`${pathname}?view=${v}`)}
      data={available.map((v) => ({
        value: v,
        label: (
          <Group gap={6} wrap="nowrap">
            <span style={{ display: "flex", alignItems: "center", lineHeight: 0 }}>
              {VIEW_META[v].icon}
            </span>
            <Text size="xs" fw={500}>{VIEW_META[v].label}</Text>
          </Group>
        ),
      }))}
      styles={{
        root: {
          background: "var(--mantine-color-default-hover)",
          border: "1px solid var(--mantine-color-default-border)",
        },
        indicator: { background: "var(--mantine-color-body)" },
      }}
    />
  );
}
