"use client";
/**
 * Modules — catalog of registered engine modules with enable toggles.
 *
 * Backend:
 *   GET   /api/base/modules
 *   PATCH /api/base/modules/{name}  { enabled: boolean }
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  ThemeIcon,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  IconApps,
  IconBuilding,
  IconLock,
  IconPlug,
  IconUsers,
} from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useT } from "@orbiteus/i18n";
import { api } from "@/lib/api";
import { applyModuleToggleSideEffects } from "@/lib/moduleRuntime";

interface ModuleRow {
  name: string;
  label: string;
  version: string;
  category: string;
  depends_on: string[];
  auto_install: boolean;
  models: string[];
  model_count: number;
  load_order: number;
  core: boolean;
  toggleable: boolean;
  enabled: boolean;
}

const MODULE_ICONS: Record<string, typeof IconApps> = {
  base: IconBuilding,
  auth: IconLock,
  crm: IconUsers,
};

function ModuleIcon({ name }: { name: string }) {
  const Icon = MODULE_ICONS[name] ?? IconPlug;
  return (
    <ThemeIcon size={44} radius="md" variant="light" color={name === "crm" ? "cyan" : "gray"}>
      <Icon size={24} stroke={1.5} />
    </ThemeIcon>
  );
}

export default function ModulesPage() {
  const t = useT();
  const [modules, setModules] = useState<ModuleRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toggling, setToggling] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<{ modules: ModuleRow[] }>("/base/modules");
      setModules(data.modules ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("modules.errorLoad"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleToggle(mod: ModuleRow, next: boolean) {
    if (!mod.toggleable) return;
    setToggling(mod.name);
    try {
      const { data } = await api.patch<ModuleRow>(`/base/modules/${mod.name}`, {
        enabled: next,
      });
      setModules((prev) => prev.map((m) => (m.name === mod.name ? data : m)));
      applyModuleToggleSideEffects(mod.name, next);
      notifications.show({
        title: next ? t("modules.enabledTitle") : t("modules.disabledTitle"),
        message: next
          ? t("modules.enabledMessage", { module: mod.label })
          : t("modules.disabledMessage", { module: mod.label }),
        color: next ? "green" : "gray",
      });
    } catch (e) {
      notifications.show({
        title: t("modules.updateFailedTitle"),
        message: e instanceof Error ? e.message : t("modules.updateFailedMessage"),
        color: "red",
      });
    } finally {
      setToggling(null);
    }
  }

  if (loading) {
    return (
      <Stack align="center" py="xl">
        <Loader color="gray" />
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Group gap="sm">
          <ThemeIcon size="lg" radius="md" variant="light">
            <IconApps size={20} />
          </ThemeIcon>
          <Title order={2}>{t("modules.title")}</Title>
        </Group>
        <Text c="dimmed" size="sm" maw={640}>
          {t("modules.description")}
        </Text>
      </Stack>

      {error ? (
        <Alert color="red" title={t("common.error")} icon={<IconApps size={16} />}>
          {error}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
        {modules.map((mod) => (
          <Paper
            key={mod.name}
            withBorder
            p="md"
            radius="md"
            style={{
              opacity: mod.enabled ? 1 : 0.72,
              borderColor: mod.enabled
                ? "var(--mantine-color-green-3)"
                : "var(--mantine-color-default-border)",
              transition: "border-color 160ms ease, opacity 160ms ease",
            }}
          >
            <Stack gap="sm">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Group gap="sm" wrap="nowrap">
                  <ModuleIcon name={mod.name} />
                  <Box>
                    <Text fw={600} size="md" lh={1.2}>
                      {mod.label}
                    </Text>
                    <Text size="xs" c="dimmed" ff="monospace">
                      {mod.name} · v{mod.version}
                    </Text>
                  </Box>
                </Group>
                <Tooltip
                  label={
                    mod.core
                      ? t("modules.tooltip.core")
                      : mod.enabled
                        ? t("modules.tooltip.enabled")
                        : t("modules.tooltip.disabled")
                  }
                >
                  <Switch
                    checked={mod.enabled}
                    disabled={!mod.toggleable || toggling === mod.name}
                    onChange={(e) => void handleToggle(mod, e.currentTarget.checked)}
                    color="green"
                    size="md"
                    thumbIcon={
                      mod.enabled ? (
                        <Box
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            background: "var(--mantine-color-green-6)",
                          }}
                        />
                      ) : undefined
                    }
                    aria-label={t("modules.toggleAria", { module: mod.label })}
                  />
                </Tooltip>
              </Group>

              <Group gap={6}>
                {mod.category ? (
                  <Badge variant="light" size="sm">
                    {mod.category}
                  </Badge>
                ) : null}
                {mod.core ? (
                  <Badge color="gray" variant="outline" size="sm">
                    {t("modules.core")}
                  </Badge>
                ) : null}
                {mod.auto_install ? (
                  <Badge color="cyan" variant="outline" size="sm">
                    {t("modules.autoInstall")}
                  </Badge>
                ) : null}
                <Badge variant="dot" color={mod.enabled ? "green" : "gray"} size="sm">
                  {mod.enabled ? t("modules.enabled") : t("modules.disabled")}
                </Badge>
              </Group>

              <Text size="sm" c="dimmed">
                {t("modules.modelCount", { count: mod.model_count })}
                {mod.depends_on.length > 0
                  ? ` · ${t("modules.dependsOn")} ${mod.depends_on.join(", ")}`
                  : ""}
              </Text>

              {mod.models.length > 0 ? (
                <Text size="xs" c="dimmed" lineClamp={2} ff="monospace">
                  {mod.models.join(", ")}
                </Text>
              ) : null}
            </Stack>
          </Paper>
        ))}
      </SimpleGrid>
    </Stack>
  );
}
