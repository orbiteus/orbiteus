"use client";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { SegmentedControl, Group, Text } from "@mantine/core";
import {
  IconList, IconLayoutKanban, IconCalendar,
  IconChartBar, IconTable, IconActivity,
} from "@tabler/icons-react";
import { useTranslatedViewLabel } from "@/lib/translatedModel";

export type ViewType = "list" | "kanban" | "calendar" | "graph" | "pivot" | "activities";

const VIEW_ICONS: Record<ViewType, React.ReactNode> = {
  list: <IconList size={18} />,
  kanban: <IconLayoutKanban size={18} />,
  calendar: <IconCalendar size={18} />,
  graph: <IconChartBar size={18} />,
  pivot: <IconTable size={18} />,
  activities: <IconActivity size={18} />,
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
  const labelList = useTranslatedViewLabel("list");
  const labelKanban = useTranslatedViewLabel("kanban");
  const labelCalendar = useTranslatedViewLabel("calendar");
  const labelGraph = useTranslatedViewLabel("graph");
  const labels: Record<ViewType, string> = {
    list: labelList,
    kanban: labelKanban,
    calendar: labelCalendar,
    graph: labelGraph,
    pivot: "Pivot",
    activities: "Activities",
  };

  if (available.length <= 1) return null;

  return (
    <SegmentedControl
      value={current}
      onChange={(v) => router.push(`${pathname}?view=${v}`)}
      data={available.map((v) => ({
        value: v,
        label: (
          <Group gap={8} wrap="nowrap">
            <span style={{ display: "flex", alignItems: "center", lineHeight: 0 }}>
              {VIEW_ICONS[v]}
            </span>
            <Text size="sm" fw={500}>{labels[v]}</Text>
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
