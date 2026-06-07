"use client";
/**
 * Technical → System status
 *
 * Tile grid of Orbiteus framework components (PostgreSQL, Redis, Celery,
 * outbox, realtime, AI layer, …). Data from `GET /api/base/system-status`.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconActivity,
  IconAlertCircle,
  IconApi,
  IconBrandDocker,
  IconBrandNextjs,
  IconBrandPython,
  IconBrandReact,
  IconBroadcast,
  IconChartBar,
  IconClockPlay,
  IconCpu,
  IconDatabase,
  IconInbox,
  IconKey,
  IconLayersIntersect,
  IconListDetails,
  IconLock,
  IconPlugConnected,
  IconRefresh,
  IconRobot,
  IconSearch,
  IconServer,
  IconShield,
  IconSparkles,
  IconStack2,
  IconTools,
  IconVector,
  IconWorld,
} from "@tabler/icons-react";
import { useT } from "@orbiteus/i18n";
import { api, apiErrorMessage } from "@/lib/api";
import { FRONTEND_STACK_VERSIONS } from "@/lib/frontendStackVersions";
import {
  componentTileColor,
  groupComponents,
  GROUP_LABELS,
  GROUP_ORDER,
  semverLabel,
  statusColor,
  statusLabel,
  type SystemComponent,
  type SystemStatusPayload,
} from "@/lib/systemStatus";

const COMPONENT_ICONS: Record<string, React.ComponentType<{ size?: number; stroke?: number }>> = {
  orbiteus: IconActivity,
  python: IconBrandPython,
  fastapi: IconApi,
  http_server: IconServer,
  sqlalchemy: IconDatabase,
  asyncpg: IconDatabase,
  alembic: IconListDetails,
  postgresql: IconDatabase,
  pgvector: IconVector,
  pgbouncer: IconLayersIntersect,
  pydantic: IconShield,
  redis: IconStack2,
  cache: IconStack2,
  module_registry: IconLayersIntersect,
  rbac: IconLock,
  audit: IconListDetails,
  event_bus: IconBroadcast,
  realtime: IconBroadcast,
  auth_jwt: IconKey,
  ai_module_config: IconSparkles,
  ai_action_palette: IconSearch,
  ai_agents: IconRobot,
  ai_credentials: IconKey,
  ai_secret_key: IconLock,
  ai_embeddings: IconVector,
  ai_agent_runs: IconListDetails,
  ai_providers: IconPlugConnected,
  ai_tooling: IconTools,
  prometheus: IconChartBar,
  celery_lib: IconCpu,
  celery_worker: IconCpu,
  celery_beat: IconClockPlay,
  outbox: IconInbox,
  nginx: IconWorld,
  docker: IconBrandDocker,
  nextjs: IconBrandNextjs,
  react: IconBrandReact,
  mantine: IconShield,
  admin_ui: IconBrandNextjs,
  portal_ui: IconBrandNextjs,
};

function ComponentIcon({ id }: { id: string }) {
  const Icon = COMPONENT_ICONS[id] ?? IconActivity;
  return <Icon size={22} stroke={1.5} />;
}

function StatusTile({ component }: { component: SystemComponent }) {
  const tileColor = componentTileColor(component.id);
  return (
    <Paper p="md" radius="md" withBorder>
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Stack gap={6} style={{ flex: 1, minWidth: 0 }}>
          <Group gap="xs" wrap="nowrap">
            <Text size="sm" fw={600} truncate>
              {component.name}
            </Text>
            <Badge size="xs" variant="light" color={statusColor(component.status)}>
              {statusLabel(component.status)}
            </Badge>
          </Group>
          <Text size="sm" c="dimmed" lineClamp={2}>
            {component.message}
          </Text>
          {component.latency_ms != null && (
            <Text size="xs" c="dimmed" ff="monospace">
              {component.latency_ms} ms
            </Text>
          )}
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={tileColor}>
          <ComponentIcon id={component.id} />
        </ThemeIcon>
      </Group>
    </Paper>
  );
}

export default function SystemStatusPage() {
  const t = useT();
  const [payload, setPayload] = useState<SystemStatusPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const frontendTiles = useMemo<SystemComponent[]>(() => {
    const v = FRONTEND_STACK_VERSIONS;
    return [
      {
        id: "nextjs",
        name: "Next.js",
        group: "frontend",
        status: "ok",
        message: `v${semverLabel(v.next)} · App Router`,
        latency_ms: null,
        detail: { version: semverLabel(v.next) },
      },
      {
        id: "react",
        name: "React",
        group: "frontend",
        status: "ok",
        message: `v${semverLabel(v.react)}`,
        latency_ms: null,
        detail: { version: semverLabel(v.react) },
      },
      {
        id: "mantine",
        name: "Mantine",
        group: "frontend",
        status: "ok",
        message: `v${semverLabel(v.mantine)} · design system`,
        latency_ms: null,
        detail: { version: semverLabel(v.mantine) },
      },
      {
        id: "i18n_pack",
        name: "@orbiteus/i18n",
        group: "frontend",
        status: "ok",
        message: `v${semverLabel(v.i18n)} · module catalogs`,
        latency_ms: null,
        detail: { version: semverLabel(v.i18n) },
      },
      {
        id: "admin_ui",
        name: "Admin UI",
        group: "frontend",
        status: "ok",
        message: `v${semverLabel(v.adminUi)} · TanStack Query v${semverLabel(v.reactQuery)}`,
        latency_ms: null,
        detail: { version: semverLabel(v.adminUi), reactQuery: semverLabel(v.reactQuery) },
      },
      {
        id: "portal_ui",
        name: "Portal UI",
        group: "frontend",
        status: process.env.NEXT_PUBLIC_PORTAL_URL ? "unknown" : "skipped",
        message: process.env.NEXT_PUBLIC_PORTAL_URL
          ? `v${semverLabel(v.portalUi)} · verify at :3001`
          : `v${semverLabel(v.portalUi)} · optional second Next.js app`,
        latency_ms: null,
        detail: { version: semverLabel(v.portalUi) },
      },
    ];
  }, []);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError("");
    try {
      const { data } = await api.get<SystemStatusPayload>("/base/system-status", {
        skipGlobalErrorToast: true,
        timeout: 20_000,
      });
      setPayload(data);
    } catch (err) {
      setError(apiErrorMessage(err, t("systemStatus.loadFailed")));
      if (!silent) setPayload(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => {
    const all = [...(payload?.components ?? []), ...frontendTiles];
    return groupComponents(all);
  }, [payload, frontendTiles]);

  const groupOrder = GROUP_ORDER;

  if (loading && !payload) {
    return (
      <Stack align="center" py="xl" gap="sm">
        <Loader color="gray" />
        <Text c="dimmed" size="sm">{t("systemStatus.probing")}</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <div>
          <Title order={3}>{t("nav.technical.status")}</Title>
          <Text c="dimmed" size="sm" mt={4}>
            {t("systemStatus.healthPrefix")}{" "}
            <Text span ff="monospace" size="xs">GET /api/base/system-status</Text>
          </Text>
        </div>
        <Group gap="xs">
          {payload?.version && (
            <Badge size="lg" variant="outline" color="dark">
              {t("systemStatus.version", { version: payload.version })}
            </Badge>
          )}
          {payload && (
            <Badge
              size="lg"
              variant="light"
              color={statusColor(payload.status)}
            >
              {t("systemStatus.overall", { status: statusLabel(payload.status) })}
            </Badge>
          )}
          <Button
            variant="default"
            size="xs"
            leftSection={<IconRefresh size={14} />}
            loading={refreshing}
            onClick={() => void load(true)}
          >
            {t("common.refresh")}
          </Button>
        </Group>
      </Group>

      {error && (
        <Alert color="red" icon={<IconAlertCircle size={16} />} title={t("common.error")}>
          {error}
        </Alert>
      )}

      {payload?.checked_at && (
        <Text size="xs" c="dimmed">
          {t("systemStatus.lastChecked", { time: new Date(payload.checked_at).toLocaleString() })}
          {" · "}{t("systemStatus.refreshHint")}
        </Text>
      )}

      {groupOrder.map((groupId) => {
        const items = grouped.get(groupId);
        if (!items?.length) return null;
        return (
          <Stack key={groupId} gap="sm">
            <Text size="xs" tt="uppercase" fw={700} c="dimmed" style={{ letterSpacing: "0.05em" }}>
              {GROUP_LABELS[groupId] ?? groupId}
            </Text>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
              {items.map((comp) => (
                <StatusTile key={comp.id} component={comp} />
              ))}
            </SimpleGrid>
          </Stack>
        );
      })}
    </Stack>
  );
}
