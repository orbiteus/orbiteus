"use client";
import { Suspense, useEffect, useState } from "react";
import { Group, Stack, Title, Loader, Center, Paper, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { getCachedUiConfig, findModel, modelToColumns } from "@/lib/modelConfig";
import type { ModelConfig } from "@/lib/api";
import type { ColumnDef } from "@/lib/viewParser";
import { parseCalendarView, parseGraphView } from "@/lib/viewParser";
import ResourceList from "@/components/ResourceList";
import ResourceKanban from "@/components/ResourceKanban";
import ResourceCalendar from "@/components/ResourceCalendar";
import ResourceGraph from "@/components/ResourceGraph";
import ViewSwitcher, { useCurrentView, type ViewType } from "@/components/ViewSwitcher";
import { api } from "@/lib/api";

interface Params { module: string; model: string; }

function ViewHeader({
  title,
  subtitle,
  switcher,
}: {
  title: string;
  subtitle?: string;
  switcher?: React.ReactNode;
}) {
  return (
    <Paper>
      <Group justify="space-between" align="center">
        <Stack gap={2}>
          <Title order={3}>{title}</Title>
          {subtitle && <Text size="sm" c="dimmed">{subtitle}</Text>}
        </Stack>
        {switcher}
      </Group>
    </Paper>
  );
}

function parseKanbanGroupField(arch: string): string {
  if (typeof window !== "undefined") {
    try {
      const doc = new DOMParser().parseFromString(arch, "text/xml");
      const k = doc.querySelector("kanban");
      return (
        k?.getAttribute("default_group_by")
        ?? k?.getAttribute("group_by")
        ?? ""
      );
    } catch { /* fall through */ }
  }
  return (
    arch.match(/default_group_by="([^"]+)"/)?.[1]
    ?? arch.match(/group_by="([^"]+)"/)?.[1]
    ?? ""
  );
}

function PageContent({ mod, model, cfg }: { mod: string; model: string; cfg: ModelConfig }) {
  const resource = `${mod}/${model}`;
  const title = model.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  const available: ViewType[] = ["list"];
  if (cfg.views.kanban) available.push("kanban");
  if (cfg.views.calendar && parseCalendarView(cfg.views.calendar)) available.push("calendar");
  if (cfg.views.graph && parseGraphView(cfg.views.graph)) available.push("graph");

  const view = useCurrentView("list");
  const columns: ColumnDef[] = modelToColumns(cfg);

  const cal = cfg.views.calendar ? parseCalendarView(cfg.views.calendar) : null;
  const gr = cfg.views.graph ? parseGraphView(cfg.views.graph) : null;

  if (view === "kanban" && cfg.views.kanban) {
    const groupField = parseKanbanGroupField(cfg.views.kanban) || "stage_id";
    const groupModel = groupField.replace(/_id$/, "");
    const groupsResource = `${mod}/${groupModel}`;

    return (
      <Stack gap="md">
        <ViewHeader
          title={title}
          subtitle="Drag and drop cards between stages."
          switcher={<ViewSwitcher available={available} current="kanban" />}
        />
        <ResourceKanban
          title=""
          groupsResource={groupsResource}
          itemsResource={resource}
          groupField={groupField}
          titleField="name"
          onMove={async (id, groupId) => {
            try {
              if (resource === "crm/opportunity" && groupField === "stage_id") {
                await api.post(`/${resource}/${id}/move`, {}, {
                  params: { stage_id: groupId },
                  skipGlobalErrorToast: true,
                });
              } else {
                await api.put(`/${resource}/${id}`, { [groupField]: groupId }, { skipGlobalErrorToast: true });
              }
              notifications.show({ title: "Updated", message: "Card moved.", color: "green" });
            } catch {
              notifications.show({ title: "Move failed", message: "Could not update record.", color: "red" });
              throw new Error("move failed");
            }
          }}
          createHref={`/${mod}/${model}/new`}
        />
      </Stack>
    );
  }

  if (view === "calendar" && cal) {
    return (
      <Stack gap="md">
        <ViewHeader
          title={title}
          subtitle="Plan and review records in time."
          switcher={<ViewSwitcher available={available} current="calendar" />}
        />
        <ResourceCalendar resource={resource} dateField={cal.dateStart} titleField="name" />
      </Stack>
    );
  }

  if (view === "graph" && gr) {
    return (
      <Stack gap="md">
        <ViewHeader
          title={title}
          subtitle="Track trends and compare values."
          switcher={<ViewSwitcher available={available} current="graph" />}
        />
        <ResourceGraph
          resource={resource}
          rowField={gr.rowField}
          measureField={gr.measureField}
          fieldMeta={cfg.fields}
        />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      {available.length > 1 && (
        <ViewHeader
          title={title}
          subtitle="Browse, filter and manage records."
          switcher={<ViewSwitcher available={available} current="list" />}
        />
      )}
      <ResourceList
        title={title}
        resource={resource}
        columns={columns}
        fieldMeta={cfg.fields}
        createHref={`/${mod}/${model}/new`}
        editHref={(id) => `/${mod}/${model}/${id}`}
      />
    </Stack>
  );
}

export default function DynamicListPage({ params }: { params: Params }) {
  const { module: mod, model } = params;
  const [cfg, setCfg] = useState<ModelConfig | null>(null);

  useEffect(() => {
    getCachedUiConfig()
      .then((config) => setCfg(findModel(config, mod, model)))
      .catch(() => setCfg(null));
  }, [mod, model]);

  if (cfg === null) return <Center h={200}><Loader color="gray" size="sm" /></Center>;

  return (
    <Suspense fallback={<Center h={200}><Loader color="gray" size="sm" /></Center>}>
      <PageContent mod={mod} model={model} cfg={cfg} />
    </Suspense>
  );
}
