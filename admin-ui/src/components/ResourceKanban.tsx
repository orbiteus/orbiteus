"use client";
import { useMemo, useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  type DragStartEvent, type DragEndEvent, closestCorners,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy, useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Group, Title, Text, Button, Stack, Paper, Badge, Skeleton, Alert, ScrollArea,
  ThemeIcon,
} from "@mantine/core";
import { IconPlus, IconAlertCircle } from "@tabler/icons-react";
import Link from "next/link";
import { useT } from "@orbiteus/i18n";
import EmptyState from "@/components/EmptyState";
import { useResourceList } from "@/lib/queries/resources";
import { extractApiError } from "@/lib/api";

interface KanbanGroup {
  id: string;
  name: string;
  color?: string;
  sequence?: number;
}

interface KanbanItem {
  id: string;
  [key: string]: unknown;
}

interface Props {
  title: string;
  groupsResource: string;
  itemsResource: string;
  groupField: string;
  titleField: string;
  subtitleFields?: { key: string; label: string; render?: (v: unknown) => string }[];
  onMove: (itemId: string, newGroupId: string) => Promise<void>;
  createHref?: string;
  groupByFilter?: Record<string, string>;
}

function KanbanCard({ item, titleField, subtitleFields, isDragging }: {
  item: KanbanItem;
  titleField: string;
  subtitleFields?: Props["subtitleFields"];
  isDragging?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: item.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    cursor: "grab",
  };

  return (
    <Paper
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      p="sm"
      radius="sm"
      withBorder
      styles={{
        root: {
          background: "var(--mantine-color-default)",
          borderColor: "var(--mantine-color-default-border)",
        },
      }}
    >
      <Text size="sm" fw={600} lineClamp={2}>
        {String(item[titleField] ?? "—")}
      </Text>
      {subtitleFields?.map((s) => (
        <Text key={s.key} size="xs" c="dimmed" mt={2}>
          {s.label}: {s.render ? s.render(item[s.key]) : String(item[s.key] ?? "—")}
        </Text>
      ))}
    </Paper>
  );
}

function KanbanColumn({ group, items, titleField, subtitleFields, activeId, emptyColumnLabel }: {
  group: KanbanGroup;
  items: KanbanItem[];
  titleField: string;
  subtitleFields?: Props["subtitleFields"];
  activeId: string | null;
  emptyColumnLabel: string;
}) {
  return (
    <Stack gap="xs" style={{ minWidth: 260, maxWidth: 300, flex: "0 0 280px" }}>
      <Paper p="xs">
        <Group justify="space-between">
          <Group gap={8}>
            <ThemeIcon variant="light" color={group.color ?? "gray"} size={20}>
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: 999,
                  background: "currentColor",
                }}
              />
            </ThemeIcon>
            <Text size="sm" fw={700}>{group.name}</Text>
          </Group>
          <Badge size="sm" variant="light" color="gray">{items.length}</Badge>
        </Group>
      </Paper>
      <Paper
        p="xs"
        style={{ minHeight: 120, background: "var(--mantine-color-default-hover)" }}
      >
        <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
          <Stack gap="xs">
            {items.map((item) => (
              <KanbanCard
                key={item.id}
                item={item}
                titleField={titleField}
                subtitleFields={subtitleFields}
                isDragging={item.id === activeId}
              />
            ))}
            {items.length === 0 && (
              <Text size="xs" c="dimmed" ta="center" py="md">
                {emptyColumnLabel}
              </Text>
            )}
          </Stack>
        </SortableContext>
      </Paper>
    </Stack>
  );
}

export default function ResourceKanban({
  title, groupsResource, itemsResource, groupField,
  titleField, subtitleFields, onMove, createHref, groupByFilter,
}: Props) {
  const t = useT();
  const itemsQuery = useResourceList<KanbanItem>(itemsResource, {
    limit: 200,
    ...groupByFilter,
  });

  const allItems = itemsQuery.data?.items ?? [];

  const dominantPipelineId = useMemo(() => {
    const pipelineCounts = new Map<string, number>();
    allItems.forEach((item) => {
      const pipelineId = item.pipeline_id;
      if (pipelineId == null || pipelineId === "") return;
      const key = String(pipelineId);
      pipelineCounts.set(key, (pipelineCounts.get(key) ?? 0) + 1);
    });
    return [...pipelineCounts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  }, [allItems]);

  const itemsForBoard = useMemo(
    () =>
      dominantPipelineId
        ? allItems.filter((item) => String(item.pipeline_id ?? "") === dominantPipelineId)
        : allItems,
    [allItems, dominantPipelineId],
  );

  const groupsParams = useMemo(
    () =>
      dominantPipelineId
        ? { pipeline_id: dominantPipelineId, limit: 200 }
        : { limit: 200 },
    [dominantPipelineId],
  );

  const groupsQuery = useResourceList<KanbanGroup>(groupsResource, groupsParams);

  const groups = useMemo(
    () =>
      [...(groupsQuery.data?.items ?? [])].sort(
        (a, b) => (a.sequence ?? 0) - (b.sequence ?? 0),
      ),
    [groupsQuery.data],
  );

  const baseColumns = useMemo(() => {
    const cols: Record<string, KanbanItem[]> = {};
    groups.forEach((g) => { cols[g.id] = []; });
    itemsForBoard.forEach((item) => {
      const gid = String(item[groupField]);
      if (cols[gid]) cols[gid].push(item);
    });
    return cols;
  }, [groups, itemsForBoard, groupField]);

  const [optimisticColumns, setOptimisticColumns] = useState<Record<string, KanbanItem[]> | null>(null);
  const columns = optimisticColumns ?? baseColumns;

  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeItem, setActiveItem] = useState<KanbanItem | null>(null);

  const loading =
    (itemsQuery.isLoading && !itemsQuery.data)
    || (groupsQuery.isLoading && !groupsQuery.data);
  const error = itemsQuery.error ?? groupsQuery.error;
  const errorMsg = error ? extractApiError(error, t("kanban.errorLoad")) : "";

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  function findGroupForItem(itemId: string): string | null {
    for (const [gid, items] of Object.entries(columns)) {
      if (items.find((i) => i.id === itemId)) return gid;
    }
    return null;
  }

  function onDragStart(event: DragStartEvent) {
    const id = String(event.active.id);
    setActiveId(id);
    const gid = findGroupForItem(id);
    if (gid) setActiveItem(columns[gid].find((i) => i.id === id) ?? null);
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    setActiveItem(null);
    if (!over) return;

    const itemId = String(active.id);
    const overId = String(over.id);

    const sourceGroup = findGroupForItem(itemId);
    const targetGroup = columns[overId] !== undefined
      ? overId
      : findGroupForItem(overId);

    if (!sourceGroup || !targetGroup || sourceGroup === targetGroup) return;

    const item = columns[sourceGroup].find((i) => i.id === itemId)!;
    setOptimisticColumns({
      ...columns,
      [sourceGroup]: columns[sourceGroup].filter((i) => i.id !== itemId),
      [targetGroup]: [...columns[targetGroup], { ...item, [groupField]: targetGroup }],
    });

    try {
      await onMove(itemId, targetGroup);
      setOptimisticColumns(null);
    } catch {
      setOptimisticColumns(null);
      void itemsQuery.refetch();
      void groupsQuery.refetch();
    }
  }

  if (loading) {
    return (
      <Group align="flex-start" gap="md">
        {Array.from({ length: 4 }).map((_, i) => (
          <Stack key={i} gap="xs" style={{ minWidth: 240 }}>
            <Skeleton height={32} radius="sm" />
            <Skeleton height={80} radius="sm" />
            <Skeleton height={80} radius="sm" />
          </Stack>
        ))}
      </Group>
    );
  }
  if (errorMsg) return <Alert icon={<IconAlertCircle size={16} />} color="red">{errorMsg}</Alert>;

  const totalItems = Object.values(columns).reduce((acc, arr) => acc + arr.length, 0);
  if (groups.length === 0 || totalItems === 0) {
    return (
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>{title}</Title>
          {createHref && (
            <Button component={Link} href={createHref} leftSection={<IconPlus size={16} />} size="sm">
              {t("kanban.new")}
            </Button>
          )}
        </Group>
        <EmptyState
          title={t("list.noRecords")}
          description={t("kanban.emptyDescription")}
          ctaLabel={createHref ? t("kanban.new") : undefined}
          ctaHref={createHref}
        />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>{title}</Title>
        {createHref && (
          <Button component={Link} href={createHref} leftSection={<IconPlus size={16} />} size="sm">
            {t("kanban.new")}
          </Button>
        )}
      </Group>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      >
        <ScrollArea
          type="auto"
          scrollbarSize={8}
          styles={{ viewport: { paddingBottom: 8 } }}
        >
          <Group gap="md" align="flex-start" wrap="nowrap" pb="md">
            {groups.map((group) => (
              <KanbanColumn
                key={group.id}
                group={group}
                items={columns[group.id] ?? []}
                titleField={titleField}
                subtitleFields={subtitleFields}
                activeId={activeId}
                emptyColumnLabel={t("kanban.dropHere")}
              />
            ))}
          </Group>
        </ScrollArea>

        <DragOverlay>
          {activeItem && (
            <KanbanCard item={activeItem} titleField={titleField} subtitleFields={subtitleFields} />
          )}
        </DragOverlay>
      </DndContext>
    </Stack>
  );
}
