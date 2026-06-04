"use client";
import { Suspense, use } from "react";
import { Group, Stack, Title, Loader, Center, Paper, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { modelToColumns } from "@/lib/modelConfig";
import type { ModelConfig } from "@/lib/api";
import { parseCalendarView, parseGraphView } from "@/lib/viewParser";
import { resolveKanbanGroupField } from "@/lib/viewJson";
import ResourceList from "@/components/ResourceList";
import ResourceKanban from "@/components/ResourceKanban";
import ResourceCalendar from "@/components/ResourceCalendar";
import ResourceGraph from "@/components/ResourceGraph";
import ViewSwitcher, { useCurrentView, type ViewType } from "@/components/ViewSwitcher";
import { api } from "@/lib/api";
import UnknownModelNotice from "@/components/UnknownModelNotice";
import { isKnownModel } from "@/lib/knownModels";
import { useUiConfig, useUiConfigModel } from "@/lib/queries/uiConfig";
import { useTranslatedColumns, useTranslatedModelTitle } from "@/lib/translatedModel";
import { useT } from "@orbiteus/i18n";

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
    <Group justify="space-between" align="flex-end" wrap="wrap" pb="xs"
      style={{ borderBottom: "1px solid var(--mantine-color-default-border)" }}>
      <Stack gap={2}>
        <Title order={2} size="h3" fw={600}>{title}</Title>
        {subtitle && <Text size="xs" c="dimmed">{subtitle}</Text>}
      </Stack>
      {switcher}
    </Group>
  );
}

function PageContent({ mod, model, cfg }: { mod: string; model: string; cfg: ModelConfig }) {
  const resource = `${mod}/${model}`;
  const t = useT();
  const title = useTranslatedModelTitle(cfg, model);

  const available: ViewType[] = ["list"];
  if (cfg.views.kanban) available.push("kanban");
  if (cfg.views.calendar && parseCalendarView(cfg.views.calendar)) available.push("calendar");
  if (cfg.views.graph && parseGraphView(cfg.views.graph)) available.push("graph");

  const view = useCurrentView("list");
  const columns = useTranslatedColumns(cfg);

  const cal = cfg.views.calendar ? parseCalendarView(cfg.views.calendar) : null;
  const gr = cfg.views.graph ? parseGraphView(cfg.views.graph) : null;

  if (view === "kanban" && cfg.views.kanban) {
    const groupField = resolveKanbanGroupField(cfg.views.kanban) || "stage_id";
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
              await api.put(`/${resource}/${id}`, { [groupField]: groupId }, { skipGlobalErrorToast: true });
              notifications.show({ title: t("form.saved"), message: t("form.saved"), color: "green" });
            } catch {
              notifications.show({ title: t("common.error"), message: t("form.saveFailed"), color: "red" });
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
    <Stack gap="sm">
      {available.length > 1 && (
        <ViewHeader
          title={title}
          subtitle={t("list.clickRow")}
          switcher={<ViewSwitcher available={available} current="list" />}
        />
      )}
      <ResourceList
        title={title}
        showTitle={available.length <= 1}
        resource={resource}
        columns={columns}
        fieldMeta={cfg.fields}
        createHref={`/${mod}/${model}/new`}
        editHref={(id) => `/${mod}/${model}/${id}`}
        prefetchExpandFields={cfg.fields
          .filter((f) => f.type === "many2one")
          .map((f) => f.name)}
      />
    </Stack>
  );
}

// Next 16 made route params async — they arrive as a Promise that must be
// unwrapped via `React.use()` in client components (App Router). Until v15
// `params` was a synchronous object; reading it directly now logs a noisy
// runtime warning and breaks subsequent re-renders.
export default function DynamicListPage({ params }: { params: Promise<Params> }) {
  const { module: mod, model } = use(params);
  const uiConfig = useUiConfig();
  const { model: cfg, isLoading, isFetched } = useUiConfigModel(mod, model);

  if (isFetched && !isKnownModel(uiConfig.data, mod, model)) {
    return <UnknownModelNotice module={mod} model={model} />;
  }

  if (!isFetched && isLoading) {
    return <Center h={200}><Loader color="gray" size="sm" /></Center>;
  }

  if (!cfg) {
    // Fall back to a generic list view that auto-discovers columns from the
    // backend response — keeps every model reachable even when ui-config is
    // empty for it.
    return (
      <Suspense fallback={<Center h={200}><Loader color="gray" size="sm" /></Center>}>
        <FallbackList mod={mod} model={model} />
      </Suspense>
    );
  }

  return (
    <Suspense fallback={<Center h={200}><Loader color="gray" size="sm" /></Center>}>
      <PageContent mod={mod} model={model} cfg={cfg} />
    </Suspense>
  );
}

function FallbackList({ mod, model }: { mod: string; model: string }) {
  const t = useT();
  const resource = `${mod}/${model}`;
  const title = useTranslatedModelTitle(null, model);
  return (
    <Stack gap="sm">
      <ViewHeader title={title} subtitle={t("list.fallbackSubtitle")} />
      <ResourceList
        title={title}
        showTitle={false}
        resource={resource}
        columns={[
          { key: "id", label: t("field.id") },
          { key: "model_name", label: "Model" },
          { key: "key", label: "Key" },
          { key: "name", label: t("field.name") },
          { key: "label", label: "Label" },
        ]}
        fieldMeta={[]}
        createHref={`/${mod}/${model}/new`}
        editHref={(id) => `/${mod}/${model}/${id}`}
      />
    </Stack>
  );
}
