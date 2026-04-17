"use client";
import { useEffect, useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  type DragStartEvent, type DragEndEvent, closestCorners,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy, useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Group, Title, Text, Button, Stack, Paper, Badge, Loader, Alert, ScrollArea,
  ThemeIcon,
} from "@mantine/core";
import { IconPlus, IconAlertCircle } from "@tabler/icons-react";
import Link from "next/link";
import { api } from "@/lib/api";

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
  groupsResource: string;               // GET /api/{groupsResource} → groups
  itemsResource: string;                // GET /api/{itemsResource}?{groupField}={groupId}
  groupField: string;                   // field on item linking to group (e.g. "stage_id")
  titleField: string;                   // field to show as card title
  subtitleFields?: { key: string; label: string; render?: (v: unknown) => string }[];
  onMove: (itemId: string, newGroupId: string) => Promise<void>;
  createHref?: string;
  groupByFilter?: Record<string, string>; // extra filter when fetching items
}

// ── Draggable Card ──────────────────────────────────────────────────────────
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

// ── Column ──────────────────────────────────────────────────────────────────
function KanbanColumn({ group, items, titleField, subtitleFields, activeId }: {
  group: KanbanGroup;
  items: KanbanItem[];
  titleField: string;
  subtitleFields?: Props["subtitleFields"];
  activeId: string | null;
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
              <Text size="xs" c="dimmed" ta="center" py="md">No records</Text>
            )}
          </Stack>
        </SortableContext>
      </Paper>
    </Stack>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────
export default function ResourceKanban({
  title, groupsResource, itemsResource, groupField,
  titleField, subtitleFields, onMove, createHref, groupByFilter,
}: Props) {
  const [groups, setGroups] = useState<KanbanGroup[]>([]);
  const [columns, setColumns] = useState<Record<string, KanbanItem[]>>({});
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeItem, setActiveItem] = useState<KanbanItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  useEffect(() => {
    load();
  }, [groupsResource, itemsResource]);

  async function load() {
    setLoading(true);
    try {
      const itemsRes = await api.get(`/${itemsResource}`, { params: { limit: 200, ...groupByFilter } });
      const allItems: KanbanItem[] = itemsRes.data.items ?? itemsRes.data ?? [];

      // For opportunity boards, keep one coherent pipeline on the board
      // to avoid fragmented columns when seed/demo data spans many pipelines.
      const pipelineCounts = new Map<string, number>();
      allItems.forEach((item) => {
        const pipelineId = item.pipeline_id;
        if (pipelineId == null || pipelineId === "") return;
        const key = String(pipelineId);
        pipelineCounts.set(key, (pipelineCounts.get(key) ?? 0) + 1);
      });
      const dominantPipelineId = [...pipelineCounts.entries()]
        .sort((a, b) => b[1] - a[1])[0]?.[0];

      const itemsForBoard = dominantPipelineId
        ? allItems.filter((item) => String(item.pipeline_id ?? "") === dominantPipelineId)
        : allItems;

      const grpRes = await api.get(`/${groupsResource}`, {
        params: dominantPipelineId
          ? { pipeline_id: dominantPipelineId }
          : undefined,
      });
      const grps: KanbanGroup[] = (grpRes.data.items ?? grpRes.data ?? [])
        .sort((a: KanbanGroup, b: KanbanGroup) => (a.sequence ?? 0) - (b.sequence ?? 0));

      setGroups(grps);
      const cols: Record<string, KanbanItem[]> = {};
      grps.forEach((g) => { cols[g.id] = []; });
      itemsForBoard.forEach((item) => {
        const gid = String(item[groupField]);
        if (cols[gid]) cols[gid].push(item);
      });
      setColumns(cols);
    } catch (e: unknown) {
      setError((e as { message: string }).message);
    } finally {
      setLoading(false);
    }
  }

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
    // overId might be a group id or another item id — find target group
    const targetGroup = columns[overId] !== undefined
      ? overId
      : findGroupForItem(overId);

    if (!sourceGroup || !targetGroup || sourceGroup === targetGroup) return;

    // Optimistic update
    const item = columns[sourceGroup].find((i) => i.id === itemId)!;
    setColumns((prev) => ({
      ...prev,
      [sourceGroup]: prev[sourceGroup].filter((i) => i.id !== itemId),
      [targetGroup]: [...prev[targetGroup], { ...item, [groupField]: targetGroup }],
    }));

    try {
      await onMove(itemId, targetGroup);
    } catch {
      // Revert on error
      load();
    }
  }

  if (loading) return <Loader color="gray" size="sm" />;
  if (error) return <Alert icon={<IconAlertCircle size={16} />} color="red">{error}</Alert>;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>{title}</Title>
        {createHref && (
          <Button component={Link} href={createHref} leftSection={<IconPlus size={16} />} size="sm">
            New
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
